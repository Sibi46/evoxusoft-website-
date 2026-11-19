# EVOXU website

Responsive company website with a Flask job admin and SQLite careers database. Static assets are in `dist/`; server code is in `backend/`.

Enquiries submit to FormSubmit for delivery to evoxusoft@gmail.com. Confirm the first activation email in that inbox; FormSubmit handles the security check and redirects to `/thank-you.html`. Email delivery remains dependent on FormSubmit and recipient activation.

The footer Admin link opens `/admin`. The admin can create, edit, publish, close, and reopen jobs. Only open jobs appear through `/api/jobs` in the Careers section. Applications use the enquiry form and include the selected job title. A new admin must replace the temporary password on first sign-in. Login uses hashed passwords, secure session cookies, CSRF protection, and rate limiting.

Production runs the dedicated `evoxuind-jobs` systemd service as an unprivileged user on loopback port 8067. The service is pinned to its deployed backend release; restart it against the intended release when deploying backend changes. Nginx serves only `current/dist` and proxies `/admin`, `/admin/`, and `/api/` to the service. Job data stays in `/var/lib/evoxuind/jobs.sqlite3`; session configuration stays in `/etc/evoxuind/jobs.env`. Credentials and databases must never be committed.

Release packages must include `dist/`, `backend/`, and `deploy/`. After changing the `current` symlink, restart `evoxuind-jobs`. Keep the previous release for rollback. Back up the persistent database before schema changes. Backend tests use a temporary database: run `python -m unittest -v test_app.py` from `backend/` with requirements installed.

Photography uses externally hosted Unsplash images; fonts use Google Fonts.
