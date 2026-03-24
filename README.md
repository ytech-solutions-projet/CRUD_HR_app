# Ytech Solutions HR CRUD

This repository now contains a runnable local Django implementation of the secure HR CRUD blueprint for Ytech Solutions.

The design assumes:

- The HR application is reachable only from the internal network.
- The HR database is separate from the public commercial website database.
- Security controls follow ISO 27001-aligned good practices such as least privilege, segmentation, logging, and controlled change management.

## Recommended Stack

- Frontend: Django templates with Bootstrap for a simple internal UI
- Backend: Django + Django REST Framework
- Database: MariaDB
- Reverse proxy: Nginx
- App server: Gunicorn
- Auth: Session-based authentication with Argon2id password hashing and role-based access control

## Repository Layout

```text
backend/
  openapi.yaml
  requirements.txt
database/
  schema.sql
config/
  nginx/
    hr_internal.conf
  systemd/
    ytech-hr.service
docs/
  secure-hr-architecture.md
```

## Run Locally

From the repository root:

```powershell
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Demo accounts:

- `hradmin` / `ChangeMe123!`
- `hruser` / `ChangeMe123!`
- `itadmin` / `ChangeMe123!`

## What To Read First

- [docs/deploy-ubuntu24-single-host.md](docs/deploy-ubuntu24-single-host.md): quickest path for deploying this project on one Ubuntu 24 04 server
- [docs/secure-hr-architecture.md](docs/secure-hr-architecture.md): full technical architecture guide
- [docs/deploy-linux.md](docs/deploy-linux.md): Ubuntu/Linux deployment guide for Nginx, Gunicorn, systemd, and MariaDB
- [database/schema.sql](database/schema.sql): MariaDB schema with constraints and least-privilege grants
- [backend/openapi.yaml](backend/openapi.yaml): CRUD API contract
- [config/nginx/hr_internal.conf](config/nginx/hr_internal.conf): internal-only Nginx example

## Current Local App Scope

- Session-based login
- Employee create, read, update, suspend
- Search by employee fields
- Department and status filtering
- Audit logging for logins and CRUD actions
- SQLite for local development

## Production Note

The local app uses SQLite so it can run easily in this workspace. The production architecture in the docs now recommends MariaDB, Nginx, Gunicorn, internal-only deployment, and network segmentation.

If you only have one Ubuntu 24.04 server available, start with [docs/deploy-ubuntu24-single-host.md](docs/deploy-ubuntu24-single-host.md). If you want the stricter internal-network layout with a separate database server, use [docs/deploy-linux.md](docs/deploy-linux.md).

## IDE Preview Note

If you open the local app inside an embedded IDE preview, POST actions can send `Origin: null`. The project now allows that only in local debug mode so forms like suspend and logout still work during development. Keep `DJANGO_ALLOW_NULL_ORIGIN_IN_DEBUG=False` in Linux production.
