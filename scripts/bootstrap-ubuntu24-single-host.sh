#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script with sudo or as root."
    exit 1
fi

APP_USER="${APP_USER:-hrapp}"
APP_DIR="${APP_DIR:-/opt/ytech-hr}"
ENV_DIR="${ENV_DIR:-/etc/ytech-hr}"
ENV_FILE="${ENV_DIR}/hr.env"
SERVICE_FILE="/etc/systemd/system/ytech-hr.service"
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/hr_single_host"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/hr_single_host"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${REPO_ROOT}" != "${APP_DIR}" ]]; then
    echo "This script expects the repository at ${APP_DIR}."
    echo "Current repository path: ${REPO_ROOT}"
    echo "Copy or clone the project to ${APP_DIR}, then rerun the script."
    exit 1
fi

echo "Installing Ubuntu packages..."
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    mariadb-server \
    nginx \
    git

if ! id "${APP_USER}" >/dev/null 2>&1; then
    echo "Creating service account ${APP_USER}..."
    adduser --system --group --home "${APP_DIR}" "${APP_USER}"
fi

echo "Preparing directories..."
mkdir -p "${APP_DIR}"
mkdir -p "${ENV_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chown root:"${APP_USER}" "${ENV_DIR}"
chmod 750 "${ENV_DIR}"

echo "Creating virtual environment..."
runuser -u "${APP_USER}" -- python3 -m venv "${APP_DIR}/.venv"
runuser -u "${APP_USER}" -- "${APP_DIR}/.venv/bin/pip" install --upgrade pip
runuser -u "${APP_USER}" -- "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Creating ${ENV_FILE} from the single-host example..."
    install -m 0640 -o root -g "${APP_USER}" \
        "${APP_DIR}/config/env/hr.single-host.env.example" \
        "${ENV_FILE}"
else
    echo "Keeping existing environment file at ${ENV_FILE}."
fi

echo "Staging systemd and Nginx configuration..."
install -m 0644 "${APP_DIR}/config/systemd/ytech-hr.service" "${SERVICE_FILE}"
install -m 0644 "${APP_DIR}/config/nginx/hr_single_host.conf" "${NGINX_SITE_AVAILABLE}"
ln -sfn "${NGINX_SITE_AVAILABLE}" "${NGINX_SITE_ENABLED}"
systemctl daemon-reload

cat <<EOF

Bootstrap complete.

Next steps:
1. Edit ${ENV_FILE} and set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, and DATABASE_URL.
2. Create the MariaDB database and user on this server.
3. Create TLS files at:
   - /etc/ssl/certs/hr-app-selfsigned.crt
   - /etc/ssl/private/hr-app-selfsigned.key
4. Run:
   sudo -u ${APP_USER} bash -lc 'set -a && source ${ENV_FILE} && set +a && ${APP_DIR}/.venv/bin/python ${APP_DIR}/backend/manage.py migrate'
   sudo -u ${APP_USER} bash -lc 'set -a && source ${ENV_FILE} && set +a && ${APP_DIR}/.venv/bin/python ${APP_DIR}/backend/manage.py collectstatic --noinput'
5. Start the services:
   sudo systemctl enable --now ytech-hr.service
   sudo nginx -t
   sudo systemctl enable --now nginx

Full guide:
${APP_DIR}/docs/deploy-ubuntu24-single-host.md
EOF
