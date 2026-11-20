"""Enable EVOXU-only public careers/sitemap routes, retaining rollback copies."""
from pathlib import Path
import os
import re
import subprocess
import time
import urllib.request

release = Path(__file__).resolve().parents[1]
site = Path('/etc/nginx/sites-available/evoxuind')
service = Path('/etc/systemd/system/evoxuind-jobs.service')
current = Path('/var/www/evoxuind/current')
old_release = current.resolve()
old_site = site.read_text()
old_service = service.read_text()
assert 'location /careers/' not in old_site
backup = Path('/etc/nginx/evoxuind.before-seo.conf')
if backup.exists():
    raise SystemExit('SEO backup already exists; review state before retrying.')
backup.write_text(old_site)
Path('/etc/systemd/system/evoxuind-jobs.before-seo').write_text(old_service)
routes = '''    location = /careers {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
    location /careers/ {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
    location = /sitemap.xml {
        include /etc/nginx/snippets/evoxuind-jobs-proxy.conf;
    }
'''
new_site = old_site.replace('    location / {', routes + '    location / {', 1)
# A return-only server-level conditional preserves the existing TLS settings.
new_site = new_site.replace('    root /var/www/evoxuind/current/dist;', '    if ($host = evoxuind.com) { return 301 https://www.evoxuind.com$request_uri; }\n\n    root /var/www/evoxuind/current/dist;', 1)
new_service = re.sub(r'^WorkingDirectory=.*$', f'WorkingDirectory={release}/backend', old_service, flags=re.M)

try:
    service.write_text(new_service)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'restart', 'evoxuind-jobs'], check=True)
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8067/careers/', timeout=3) as response:
                assert response.status == 200
            break
        except Exception:
            time.sleep(.3)
    else:
        raise RuntimeError('New Careers service failed to start.')
    with urllib.request.urlopen('http://127.0.0.1:8067/sitemap.xml', timeout=5) as response:
        assert response.status == 200
    site.write_text(new_site)
    subprocess.run(['nginx', '-t'], check=True)
    next_link = Path('/var/www/evoxuind/current-next')
    next_link.symlink_to(release)
    os.replace(next_link, current)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
except Exception:
    site.write_text(old_site)
    service.write_text(old_service)
    if current.resolve() != old_release:
        rollback = Path('/var/www/evoxuind/rollback-next')
        rollback.symlink_to(old_release)
        os.replace(rollback, current)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'restart', 'evoxuind-jobs'], check=True)
    raise
print('SEO routes, canonical redirect and public job pages deployed. Persistent data and credentials preserved.')
