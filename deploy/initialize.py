"""Initialize persistent server configuration and an admin only once."""
import os
import secrets
import subprocess
from pathlib import Path

config = Path('/etc/evoxuind/jobs.env')
if not config.exists():
    fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('EVOXU_SECRET_KEY=' + secrets.token_hex(32) + '\n')
        f.write('EVOXU_DATABASE=/var/lib/evoxuind/jobs.sqlite3\n')

env = os.environ.copy()
for line in config.read_text().splitlines():
    if '=' in line:
        key, value = line.split('=', 1)
        env[key] = value

backend = Path(__file__).resolve().parents[1] / 'backend'
database = Path(env['EVOXU_DATABASE'])
if not database.exists():
    subprocess.run([
        '/opt/evoxuind/venv/bin/python', str(backend / 'app.py'),
        '--init-admin', '--credentials-file', '/etc/evoxuind/initial-admin-access.txt',
    ], env=env, check=True)
else:
    raise SystemExit('Persistent database already exists. Initialization skipped; review existing state before deploying.')
