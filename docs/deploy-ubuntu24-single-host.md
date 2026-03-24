# Ubuntu 24.04 Single-Host Deployment

This guide is the fastest way to deploy the HR application on one Ubuntu 24.04 LTS server using:

- Nginx
- Gunicorn
- systemd
- MariaDB on the same server
- HTTPS with a self-signed or internal CA certificate

Use this when you want a practical deployment on one server. If you want the stricter internal-only layout with a separate MariaDB server, use [deploy-linux.md](deploy-linux.md).

## Assumptions

- Ubuntu version: `24.04 LTS`
- App path: `/opt/ytech-hr`
- App user: `hrapp`
- Service name: `ytech-hr`
- MariaDB runs locally on `127.0.0.1:3306`
- You already copied or cloned this repository to `/opt/ytech-hr`

## 1. Copy the Project to the Server

If the repository is not already on the server:

```bash
sudo mkdir -p /opt/ytech-hr
sudo git clone <your-repo-url> /opt/ytech-hr
cd /opt/ytech-hr
```

If the project is already there, just `cd /opt/ytech-hr`.

## 2. Run the Bootstrap Script

From the repository root:

```bash
cd /opt/ytech-hr
sudo bash scripts/bootstrap-ubuntu24-single-host.sh
```

The script will:

- install Ubuntu packages
- create the `hrapp` service account if needed
- create `/etc/ytech-hr/hr.env` if it does not exist
- build the Python virtual environment
- install Python dependencies
- stage the systemd unit and Nginx site config

It does not start the app yet because you still need to set secrets, database credentials, and TLS files.

## 3. Create the MariaDB Database and User

Open the MariaDB shell:

```bash
sudo mysql
```

Run:

```sql
CREATE DATABASE IF NOT EXISTS ytech_hr
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'hr_app_user'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON ytech_hr.* TO 'hr_app_user'@'127.0.0.1';
FLUSH PRIVILEGES;
```

Replace `change_me` with a strong password.

## 4. Fill in the Environment File

Edit the generated file:

```bash
sudoedit /etc/ytech-hr/hr.env
```

Use [config/env/hr.single-host.env.example](../config/env/hr.single-host.env.example) as the reference.

Minimum values:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,your-server-name-or-ip
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-server-name-or-ip
DJANGO_BEHIND_PROXY=True
DATABASE_URL=mariadb://hr_app_user:<strong-password>@127.0.0.1:3306/ytech_hr
```

Notes:

- `DJANGO_ALLOWED_HOSTS` must include the hostname or IP you will use in the browser.
- `DJANGO_CSRF_TRUSTED_ORIGINS` must include the full HTTPS origin, for example `https://192.168.1.50` or `https://hr.internal.local`.
- keep `DJANGO_DEBUG=False` on the server.

## 5. Create a TLS Certificate

For a lab or internal-only server, a self-signed certificate is enough to get started:

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout /etc/ssl/private/hr-app-selfsigned.key \
  -out /etc/ssl/certs/hr-app-selfsigned.crt \
  -subj "/CN=your-server-name-or-ip"
```

If you already have an internal CA or a public certificate, place your certificate and key at the same paths or edit [config/nginx/hr_single_host.conf](../config/nginx/hr_single_host.conf).

## 6. Run Migrations and Collect Static Files

```bash
cd /opt/ytech-hr
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py migrate'
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py collectstatic --noinput'
```

Optional first admin user:

```bash
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py createsuperuser'
```

Optional lab-only demo data:

```bash
sudo -u hrapp bash -lc 'set -a && source /etc/ytech-hr/hr.env && set +a && /opt/ytech-hr/.venv/bin/python backend/manage.py seed_demo'
```

Do not run `seed_demo` on a real HR server.

## 7. Enable systemd and Nginx

Disable the Ubuntu default Nginx site if it is still enabled:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Then enable the app:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ytech-hr.service
sudo ln -sfn /etc/nginx/sites-available/hr_single_host /etc/nginx/sites-enabled/hr_single_host
sudo nginx -t
sudo systemctl enable --now nginx
```

The staged files are:

- [config/systemd/ytech-hr.service](../config/systemd/ytech-hr.service)
- [config/gunicorn/gunicorn.conf.py](../config/gunicorn/gunicorn.conf.py)
- [config/nginx/hr_single_host.conf](../config/nginx/hr_single_host.conf)

## 8. Open the Firewall

Allow HTTPS and optionally SSH:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 443/tcp
sudo ufw enable
```

If the server should stay internal-only, allow only your LAN or VPN subnet instead of opening `443/tcp` globally.

## 9. Verify the Deployment

Check the service:

```bash
sudo systemctl status ytech-hr --no-pager
sudo journalctl -u ytech-hr -n 100 --no-pager
```

Check Nginx:

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
```

Check the app locally:

```bash
curl -Ik https://127.0.0.1 --insecure
```

Then open the server URL in the browser and log in.

## 10. Next Hardening Steps

- replace the self-signed certificate with an internal CA or trusted certificate
- restrict the Nginx site with `allow` and `deny` rules if the app should stay private
- back up the MariaDB database regularly
- patch Ubuntu packages regularly
- rotate `DJANGO_SECRET_KEY` and database passwords under change control
