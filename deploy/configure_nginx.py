"""Preserve this site's TLS config while adding its admin/API proxy routes."""
from pathlib import Path
import subprocess

site = Path('/etc/nginx/sites-available/evoxuind')
backup = Path('/etc/nginx/evoxuind.before-jobs.conf')
original = site.read_text()
if backup.exists():
    raise SystemExit('Backup exists; review deployment state before retrying.')
backup.write_text(original)
assert 'root /var/www/evoxuind/current;' in original
assert 'location /admin' not in original
release = Path(__file__).resolve().parents[1]
text = original.replace('root /var/www/evoxuind/current;', f'root {release}/dist;', 1)
routes = '''    location = /admin {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
    location /admin/ {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
    location /api/ {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
'''
text = text.replace('    location / {', routes + '    location / {', 1)
site.write_text(text)
try:
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
except Exception:
    site.write_text(original)
    subprocess.run(['nginx', '-t'], check=True)
    raise
print('EVOXU-only proxy configuration installed. TLS configuration preserved.')
