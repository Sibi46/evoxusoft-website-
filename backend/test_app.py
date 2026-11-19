import re
import tempfile
import unittest
from pathlib import Path

from app import app, db, init_db
from werkzeug.security import generate_password_hash


class JobAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, SECRET_KEY='test-only-session-key', ADMIN_USERNAME='admin', DATABASE=str(Path(self.temp.name) / 'test.sqlite3'))
        init_db()
        with db() as conn:
            conn.execute('INSERT INTO admin (id,password_hash,must_change) VALUES (1,?,0)', (generate_password_hash('test-admin-password'),))
        self.client = app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def csrf(self, path='/admin/login'):
        page = self.client.get(path, base_url='https://localhost')
        return re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)

    def login(self):
        token = self.csrf()
        return self.client.post('/admin/login', data={'csrf': token, 'username': 'admin', 'password': 'test-admin-password'}, base_url='https://localhost')

    def job(self, **overrides):
        data = dict(title='Software Intern', department='EVOXU SOFT', location='Remote', employment_type='Internship', description='Learn and build with a team.', status='open')
        data.update(overrides)
        data['csrf'] = self.csrf('/admin/jobs/new')
        return self.client.post('/admin/jobs/new', data=data, base_url='https://localhost')

    def test_admin_requires_login_and_csrf(self):
        self.assertEqual(self.client.get('/admin', base_url='https://localhost').status_code, 302)
        self.assertEqual(self.client.post('/admin/jobs/new', data={'status': 'open'}, base_url='https://localhost').status_code, 400)
        self.assertEqual(self.client.get('/api/jobs').json, {'jobs': []})

    def test_configured_username(self):
        app.config['ADMIN_USERNAME'] = 'evoxu'
        self.assertEqual(self.login().status_code, 401)
        token = self.csrf()
        response = self.client.post('/admin/login', data={'csrf': token, 'username': 'evoxu', 'password': 'test-admin-password'}, base_url='https://localhost')
        self.assertEqual(response.status_code, 302)

    def test_publish_edit_close_and_reopen(self):
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.job().status_code, 302)
        job = self.client.get('/api/jobs').json['jobs'][0]
        self.assertEqual(job['title'], 'Software Intern')
        edit_path = f"/admin/jobs/{job['id']}/edit"
        token = self.csrf(edit_path)
        edited = dict(csrf=token, title='Project Lead', department='Technology', location='Chennai', employment_type='Full-time', description='Lead real projects.', status='open')
        self.assertEqual(self.client.post(edit_path, data=edited, base_url='https://localhost').status_code, 302)
        self.assertEqual(self.client.get('/api/jobs').json['jobs'][0]['title'], 'Project Lead')
        for status, count in [('closed', 0), ('open', 1)]:
            token = self.csrf('/admin')
            self.client.post(f"/admin/jobs/{job['id']}/status", data={'csrf': token, 'status': status}, base_url='https://localhost')
            self.assertEqual(len(self.client.get('/api/jobs').json['jobs']), count)

    def test_drafts_private_and_invalid_fields_rejected(self):
        self.login()
        self.job(status='draft')
        self.job(status='closed')
        self.assertEqual(self.client.get('/api/jobs').json['jobs'], [])
        self.job(title='')
        self.job(status='unexpected')
        with db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 2)

    def test_admin_escapes_job_content(self):
        self.login()
        self.job(title='<script>alert(1)</script>')
        page = self.client.get('/admin', base_url='https://localhost').text
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_first_login_requires_password_change(self):
        with db() as conn:
            conn.execute('UPDATE admin SET must_change=1')
        self.login()
        self.assertTrue(self.client.get('/admin', base_url='https://localhost').location.endswith('/admin/password'))
        token = self.csrf('/admin/password')
        response = self.client.post('/admin/password', data={'csrf': token, 'current_password': 'test-admin-password', 'new_password': 'a-new-strong-password', 'confirm_password': 'a-new-strong-password'}, base_url='https://localhost')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/admin', base_url='https://localhost').status_code, 200)
        with db() as conn:
            self.assertEqual(conn.execute('SELECT must_change FROM admin').fetchone()[0], 0)

    def test_rate_limit_and_logout(self):
        token = self.csrf()
        for _ in range(8):
            self.client.post('/admin/login', data={'csrf': token, 'username': 'admin', 'password': 'wrong'}, base_url='https://localhost')
        self.assertEqual(self.client.post('/admin/login', data={'csrf': token, 'username': 'admin', 'password': 'wrong'}, base_url='https://localhost').status_code, 429)
        with db() as conn:
            conn.execute('DELETE FROM login_attempts')
        self.login()
        token = self.csrf('/admin')
        self.client.post('/admin/logout', data={'csrf': token}, base_url='https://localhost')
        self.assertEqual(self.client.get('/admin', base_url='https://localhost').status_code, 302)


if __name__ == '__main__':
    unittest.main()
