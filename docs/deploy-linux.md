# Linux Deployment Guide

This guide deploys the HR application on an internal Ubuntu 24.04 LTS server using:

- Nginx
- Gunicorn
- systemd
- MariaDB
- internal-only access

## Assumptions

- App server hostname: `hr-app-01`
- App path: `/opt/ytech-hr`
- App user: `hrapp`
- Internal FQDN: `hr.ytech.local`
- Internal app server IP: `10.20.30.10`
- MariaDB server IP: `10.20.40.20`

## 1. Install OS Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev build-essential pkg-config default-libmysqlclient-dev mariadb-client nginx git
```

## 2. Create the Service Account and Directories

```bash
sudo adduser --system --group --home /opt/ytech-hr hrapp
sudo mkdir -p /opt/ytech-hr
sudo mkdir -p /etc/ytech-hr
sudo chown -R hrapp:hrapp /opt/ytech-hr
sudo chown root:hrapp /etc/ytech-hr
sudo chmod 750 /etc/ytech-hr
```

## 3. Copy the Project to the Server

```bash
sudo -u hrapp git clone <your-repo-url> /opt/ytech-hr
cd /opt/ytech-hr
```

If the repository already exists locally, copy it with `scp` or your preferred deployment method.

## 4. Create the Python Virtual Environment

```bash
sudo -u hrapp python3 -m venv /opt/ytech-hr/.venv
sudo -u hrapp /opt/ytech-hr/.venv/bin/pip install --upgrade pip
sudo -u hrapp /opt/ytech-hr/.venv/bin/pip install -r /opt/ytech-hr/backend/requirements.txt
```

## 5. Prepare MariaDB

On the MariaDB server, run [mariadb-bootstrap.sql](../database/mariadb-bootstrap.sql) as a MariaDB administrator:

```bash
sudo mariadb < /path/to/mariadb-bootstrap.sql
```

Then allow only the app server to connect in MariaDB and the firewall.

Example firewall logic:

- allow `10.20.30.10 -> 10.20.40.20:3306`
- deny all other sources to MariaDB

## 6. Create the Environment File

Copy [hr.env.example](../config/env/hr.env.example) to `/etc/ytech-hr/hr.env` and update every placeholder:

```bash
sudo cp /opt/ytech-hr/config/env/hr.env.example /etc/ytech-hr/hr.env
sudo chown root:hrapp /etc/ytech-hr/hr.env
sudo chmod 640 /etc/ytech-hr/hr.env
sudoedit /etc/ytech-hr/hr.env
```

Minimum required values:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=hr.ytech.local,10.20.30.10
DJANGO_CSRF_TRUSTED_ORIGINS=https://hr.ytech.local
DJANGO_BEHIND_PROXY=True
DATABASE_URL=mariadb://hr_app_user:<strong-password>@10.20.40.20:3306/ytech_hr
```

## 7. Run Migrations and Collect Static Files

```bash
cd /opt/ytech-hr
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py migrate'
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py collectstatic --noinput'
```

Optional demo data for a lab server:

```bash
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py seed_demo'
```

Do not run `seed_demo` on a real production HR server.

## 8. Install systemd Service

Copy the service file:

```bash
sudo cp /opt/ytech-hr/config/systemd/ytech-hr.service /etc/systemd/system/ytech-hr.service
sudo systemctl daemon-reload
sudo systemctl enable --now ytech-hr.service
sudo systemctl status ytech-hr.service
```

The service uses:

- [ytech-hr.service](../config/systemd/ytech-hr.service)
- [gunicorn.conf.py](../config/gunicorn/gunicorn.conf.py)

## 9. Install Nginx

Copy the Nginx config:

```bash
sudo cp /opt/ytech-hr/config/nginx/hr_internal.conf /etc/nginx/sites-available/hr_internal
sudo ln -s /etc/nginx/sites-available/hr_internal /etc/nginx/sites-enabled/hr_internal
sudo nginx -t
sudo systemctl reload nginx
```

Before reloading Nginx, place your internal TLS certificate and key at:

- `/etc/ssl/certs/hr.ytech.local.crt`
- `/etc/ssl/private/hr.ytech.local.key`

The Nginx config already:

- redirects HTTP to HTTPS
- restricts access to allowed internal subnets
- serves static files directly
- proxies app traffic to Gunicorn over a Unix socket

## 10. Apply Firewall Rules

On the app server:

- allow `10.20.10.0/24 -> 10.20.30.10:443`
- allow `10.20.50.0/24 -> 10.20.30.10:443`
- deny Internet access to `10.20.30.10:443`
- allow outbound `10.20.30.10 -> 10.20.40.20:3306`

Example with `ufw`:

```bash
sudo ufw allow from 10.20.10.0/24 to 10.20.30.10 port 443 proto tcp
sudo ufw allow from 10.20.50.0/24 to 10.20.30.10 port 443 proto tcp
sudo ufw deny 8000/tcp
```

Do not expose Gunicorn directly. Nginx should be the only listener for client traffic.

## 11. Verify Deployment

Check the service:

```bash
sudo systemctl status ytech-hr
sudo journalctl -u ytech-hr -n 100 --no-pager
```

Check Nginx:

```bash
sudo nginx -t
sudo systemctl status nginx
```

Check the application from an internal workstation:

```bash
curl -Ik https://hr.ytech.local
```

Expected results:

- HTTP 200 or redirect to `/login/`
- no external Internet reachability
- successful login from approved internal subnet

## 12. Ongoing Operations

- rotate `DJANGO_SECRET_KEY` and database credentials
- patch the server regularly
- back up MariaDB daily
- monitor `journalctl`, Nginx logs, and authentication failures
- run `migrate` during controlled releases

## Notes

- The architecture guide schema in [schema.sql](../database/schema.sql) is a design reference.
- For the Django application itself, use `manage.py migrate` as the source of truth for production schema changes.
