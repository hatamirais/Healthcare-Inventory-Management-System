# App Demo Deployment Draft

Docker-based deployment draft for the App Demo environment on an existing workplace VM/VPS.

Last updated: 2026-04-09
Scope: Demo deployment of the current Django monolith for internal stakeholder evaluation.

## 1. Deployment Goal

Provide a stable, repeatable deployment of the current Healthcare IMS application on a VM that already runs Docker. The deployment should match the current production-like runtime as closely as practical without introducing infrastructure that the application does not yet use.

Current design principle:

- deploy only services that are active in the codebase today
- keep the topology simple enough to reset and maintain during demos
- preserve a path to expand later into a fuller production stack

## 2. Recommended Topology

### Mandatory containers

- `app`: Django application served by Gunicorn
- `postgres`: PostgreSQL database

### Optional container

- `nginx`: reverse proxy for HTTP/HTTPS termination and static/media serving if the VM does not already sit behind an organizational reverse proxy

### Deferred for later

- `redis`: not required for App Demo because the current codebase does not actively use Redis-backed caching or Celery workers
- `worker`: no Celery worker should be deployed until real background jobs exist

## 3. Baseline Deployment Modes

Choose one of these two modes.

### Mode A: Existing reverse proxy available

Use this when the department already has a gateway, ingress, or reverse proxy on the VM or network edge.

- Run `app` and `postgres` only
- Expose Gunicorn on an internal VM port such as `8000`
- Let the existing proxy handle TLS, domain routing, and external access

This is the preferred App Demo mode because it removes one container and avoids duplicate TLS management.

### Mode B: Standalone VM deployment

Use this when the VM itself must terminate HTTP or HTTPS.

- Run `nginx`, `app`, and `postgres`
- Nginx proxies to Gunicorn over the Docker network
- Static and media files are served through Nginx-mounted volumes

## 4. Proposed File Set

These files should be added in the implementation phase.

- `backend/Dockerfile`
- `backend/entrypoint.sh`
- `docker-compose.demo.yml`
- `.env.demo.example`
- `scripts/deploy-demo.ps1` or `scripts/deploy-demo.sh`

If Mode B is selected, add:

- `deploy/nginx/default.conf`

## 5. Container Responsibilities

### app

Responsibilities:

- install Python dependencies
- run database migrations on startup or through a one-shot release step
- collect static files
- serve Django via Gunicorn

Expected command shape:

```sh
python manage.py migrate && \
python manage.py collectstatic --noinput && \
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

Notes:

- working directory should be `backend/`
- application container should use `DEBUG=False`
- `ALLOWED_HOSTS` must include the demo hostname and VM IP if needed

### postgres

Responsibilities:

- persist application data through a named Docker volume
- expose only the internal Docker network port by default

Notes:

- avoid publishing PostgreSQL to the public network unless there is a clear operational need
- enforce strong `DB_PASSWORD`

### nginx

Responsibilities:

- reverse proxy requests to Gunicorn
- serve static and media files directly
- optionally terminate TLS

Notes:

- include only if the VM does not already have an external reverse proxy

## 6. Environment Contract

The demo deployment should use a dedicated env file instead of the current local-development defaults.

Required values:

- `DJANGO_SECRET_KEY`
- `DEBUG=False`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST=postgres`
- `DB_PORT=5432`
- `ALLOWED_HOSTS=<demo-hostname>,<vm-ip>`
- `SECURE_SSL_REDIRECT=True` only when HTTPS is correctly terminated upstream

Recommended additions for deployment clarity:

- `CSRF_TRUSTED_ORIGINS=https://demo-hostname`
- `GUNICORN_WORKERS=3`
- `GUNICORN_TIMEOUT=120`

Note:

- `REDIS_URL` should not be required for App Demo until Redis becomes active in the runtime

## 7. Storage Strategy

Use Docker named volumes for the demo environment.

- `postgres_data`: database persistence
- `static_data`: collected static files
- `media_data`: uploaded files and branding assets

Why:

- container recreation should not erase the demo database
- uploaded logo and generated assets should survive redeployments

## 8. Network Strategy

Use a private Docker network for inter-container communication.

- `app` talks to `postgres` on the internal network
- `nginx` talks to `app` on the internal network when used
- only the web entrypoint should publish host ports

Recommended port exposure:

- Mode A: publish `8000:8000` only if the upstream proxy needs a host port
- Mode B: publish `80:80` and optionally `443:443` from Nginx

## 9. Security Posture for Demo

The demo is still an internal deployment, but it should not run with local-development shortcuts.

Required:

- `DEBUG=False`
- non-default Django secret key
- non-default PostgreSQL password
- restricted host firewall rules
- database port not exposed publicly

Recommended:

- restrict access to office network or VPN
- use HTTPS if external browser access is required
- create dedicated demo user accounts instead of sharing admin credentials

## 10. Operations Flow

### Initial deploy

1. Copy repo to the VM.
2. Prepare `.env.demo` from `.env.demo.example`.
3. Build images with `docker compose -f docker-compose.demo.yml build`.
4. Start services with `docker compose -f docker-compose.demo.yml up -d`.
5. Run migrations and collect static assets if not handled by entrypoint.
6. Create superuser and seed demo data.
7. Verify login, dashboard, stock list, receiving, and distribution flows.

### Update deploy

1. Pull the latest code.
2. Rebuild the app image.
3. Restart only the app service unless schema changes require migration.
4. Run migrations.
5. Smoke-test the main demo scenario.

### Reset flow for demos

1. Restore the database from a known backup or reseed from a reset script.
2. Keep media volume if branding should remain.
3. Re-run the smoke-test checklist.

## 11. Demo Smoke Test Checklist

Minimum checks after each deployment:

1. Login page loads.
2. Admin user can sign in.
3. Dashboard renders without errors.
4. Item master list loads.
5. Stock list loads.
6. Receiving list and detail pages work.
7. Distribution list and detail pages work.
8. Static assets render correctly.
9. Uploaded branding assets still appear.

## 12. Known Constraints

- The repo currently has no backend container image definition.
- The repo currently has no deployment compose file for Django.
- The repo currently documents Redis in local infrastructure, but the application does not actively depend on it today.
- `CSRF_TRUSTED_ORIGINS` is not yet configured in settings and should be added when the deployment implementation starts.

## 13. Recommended Next Implementation Order

1. Add `backend/Dockerfile`.
2. Add `docker-compose.demo.yml` with `app` and `postgres` only.
3. Add production-oriented env example for the demo VM.
4. Add `CSRF_TRUSTED_ORIGINS` support to Django settings.
5. Add a simple deployment script and smoke-test steps.
6. Decide whether Nginx is needed based on the VM's existing reverse-proxy setup.

## 14. Decision Summary

For App Demo, the default deployment should be:

- Docker on the department VM
- Django app container with Gunicorn
- PostgreSQL container
- no Redis
- no Celery worker
- Nginx only if the VM does not already have reverse-proxy capability
