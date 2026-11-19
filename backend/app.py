import functools
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('EVOXU_SECRET_KEY'),
    DATABASE=os.environ.get('EVOXU_DATABASE', '/var/lib/evoxuind/jobs.sqlite3'),
    SESSION_COOKIE_NAME='evoxu_admin', SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=4), MAX_CONTENT_LENGTH=64 * 1024,
)
# The service listens only on loopback, behind the site's Nginx proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


def db():
    conn = sqlite3.connect(app.config['DATABASE'], timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY CHECK (id = 1), password_hash TEXT NOT NULL,
                must_change INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                department TEXT NOT NULL, location TEXT NOT NULL, employment_type TEXT NOT NULL,
                description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT NOT NULL, attempted_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS login_attempt_ip ON login_attempts(ip, attempted_at);
        ''')


def admin_record():
    with db() as conn:
        return conn.execute('SELECT * FROM admin WHERE id=1').fetchone()


def csrf_token():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


app.jinja_env.globals['csrf_token'] = csrf_token


@app.before_request
def protect_admin():
    if request.path.startswith('/admin') and request.method == 'POST':
        expected = session.get('csrf', '')
        supplied = request.form.get('csrf', '')
        if not expected or not secrets.compare_digest(expected, supplied):
            abort(400, 'Your session expired. Reload the page and try again.')


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.path.startswith('/admin'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


def require_admin(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        admin = admin_record()
        if not admin or session.get('admin_version') != admin['version']:
            return redirect(url_for('login'))
        if admin['must_change'] and request.endpoint not in ('password', 'logout'):
            return redirect(url_for('password'))
        return view(*args, **kwargs)
    return wrapped


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        now = int(time.time())
        ip = request.remote_addr or 'unknown'
        with db() as conn:
            conn.execute('DELETE FROM login_attempts WHERE attempted_at < ?', (now - 900,))
            attempts = conn.execute('SELECT COUNT(*) FROM login_attempts WHERE ip=?', (ip,)).fetchone()[0]
        if attempts >= 8:
            return render_template('login.html', error='Too many attempts. Please wait 15 minutes.'), 429
        admin = admin_record()
        if request.form.get('username') == 'admin' and admin and check_password_hash(admin['password_hash'], request.form.get('password', '')):
            session.clear()
            session.permanent = True
            session['admin_version'] = admin['version']
            with db() as conn:
                conn.execute('DELETE FROM login_attempts WHERE ip=?', (ip,))
            return redirect(url_for('password' if admin['must_change'] else 'dashboard'))
        with db() as conn:
            conn.execute('INSERT INTO login_attempts VALUES (?, ?)', (ip, now))
        return render_template('login.html', error='Username or password is incorrect.'), 401
    return render_template('login.html')


@app.route('/admin/password', methods=['GET', 'POST'])
@require_admin
def password():
    admin = admin_record()
    error = None
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        if not check_password_hash(admin['password_hash'], current):
            error = 'Current password is incorrect.'
        elif len(new) < 12 or len(new) > 128:
            error = 'Use a password between 12 and 128 characters.'
        elif new != request.form.get('confirm_password'):
            error = 'The new passwords do not match.'
        elif secrets.compare_digest(new, current):
            error = 'Choose a different password from your temporary password.'
        else:
            with db() as conn:
                conn.execute('UPDATE admin SET password_hash=?, must_change=0, version=version+1 WHERE id=1', (generate_password_hash(new),))
            session.clear()
            session.permanent = True
            session['admin_version'] = admin['version'] + 1
            flash('Password updated.')
            return redirect(url_for('dashboard'))
    return render_template('password.html', error=error, initial=bool(admin['must_change']))


@app.post('/admin/logout')
@require_admin
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.get('/admin')
@app.get('/admin/')
@require_admin
def dashboard():
    with db() as conn:
        jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC, id DESC').fetchall()
    return render_template('dashboard.html', jobs=jobs)


TYPES = ('Full-time', 'Part-time', 'Internship', 'Traineeship', 'Contract')
STATUSES = ('draft', 'open', 'closed')


@app.route('/admin/jobs/new', methods=['GET', 'POST'])
@app.route('/admin/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@require_admin
def edit_job(job_id=None):
    job = {}
    if job_id is not None:
        with db() as conn:
            row = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            abort(404)
        job = dict(row)
    error = None
    if request.method == 'POST':
        job = {k: request.form.get(k, '').strip() for k in ('title', 'department', 'location', 'employment_type', 'description', 'status')}
        if not all(job.values()):
            error = 'Complete all fields.'
        elif any(len(job[k]) > limit for k, limit in [('title', 140), ('department', 100), ('location', 140), ('description', 12000)]):
            error = 'One or more fields exceed the maximum length.'
        elif job['employment_type'] not in TYPES or job['status'] not in STATUSES:
            error = 'Choose a valid employment type and status.'
        else:
            now = datetime.now(timezone.utc).isoformat()
            values = tuple(job[k] for k in ('title', 'department', 'location', 'employment_type', 'description', 'status'))
            with db() as conn:
                if job_id is None:
                    conn.execute('INSERT INTO jobs (title,department,location,employment_type,description,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', values + (now, now))
                else:
                    conn.execute('UPDATE jobs SET title=?,department=?,location=?,employment_type=?,description=?,status=?,updated_at=? WHERE id=?', values + (now, job_id))
            flash('Job published on Careers.' if job['status'] == 'open' else 'Job saved. Only open jobs appear on Careers.')
            return redirect(url_for('dashboard'))
    return render_template('job.html', job=job, job_id=job_id, types=TYPES, statuses=STATUSES, error=error)


@app.post('/admin/jobs/<int:job_id>/status')
@require_admin
def job_status(job_id):
    status = request.form.get('status')
    if status not in STATUSES:
        abort(400)
    with db() as conn:
        result = conn.execute('UPDATE jobs SET status=?,updated_at=? WHERE id=?', (status, datetime.now(timezone.utc).isoformat(), job_id))
        if result.rowcount == 0:
            abort(404)
    flash('Job status updated.')
    return redirect(url_for('dashboard'))


@app.get('/api/jobs')
def public_jobs():
    with db() as conn:
        rows = conn.execute("SELECT id,title,department,location,employment_type,description,created_at FROM jobs WHERE status='open' ORDER BY created_at DESC,id DESC").fetchall()
    response = jsonify(jobs=[dict(row) for row in rows])
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/health')
def health():
    with db() as conn:
        conn.execute('SELECT 1').fetchone()
    return jsonify(status='ok')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-admin', action='store_true')
    parser.add_argument('--credentials-file')
    args = parser.parse_args()
    init_db()
    if args.init_admin:
        if admin_record():
            raise SystemExit('Admin already exists; no changes made.')
        if not args.credentials_file:
            raise SystemExit('--credentials-file is required.')
        temporary = secrets.token_urlsafe(20)
        fd = os.open(args.credentials_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write('EVOXU JOB ADMIN\nURL: https://www.evoxuind.com/admin\nUsername: admin\nTemporary password: ' + temporary + '\n\nChange this password at first sign-in. Keep this file private.\n')
        with db() as conn:
            conn.execute('INSERT INTO admin (id,password_hash) VALUES (1,?)', (generate_password_hash(temporary),))
        print('Admin initialized. Temporary login saved to the private credentials file.')
