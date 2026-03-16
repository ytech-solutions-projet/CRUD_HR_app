# Secure HR CRUD Architecture Guide

## 1. System Architecture

Ytech Solutions should host the HR application as an internal-only service on a separate application server and a separate MariaDB database server. The HR stack must not share the same database, host, or network exposure as the public commercial website.

### High-Level Design

- Public website: exposed to the Internet in a DMZ or public application segment
- HR application: hosted in an internal application VLAN
- HR database: hosted in a protected internal data VLAN
- Internal DNS: resolves `hr.ytech.local` only for internal users
- Firewall: blocks any direct Internet path to the HR application and HR database
- Monitoring and logs: sent to central monitoring/SIEM
- Jira and Git repository: reachable from authorized staff networks, not from the public website tier

### Isolation Goals

- Separate servers or VMs for public app and HR app
- Separate databases for public app and HR app
- Separate service accounts and secrets
- Separate firewall rules for HR traffic
- No inbound Internet exposure for the HR application

### Text-Based Architecture Diagram

```text
                         Internet
                             |
                       [ Edge Firewall ]
                             |
                   ------------------------
                   |                      |
                [ DMZ ]             [ Internal Network ]
                   |                      |
         Public Web App Server      -------------------------
                   |                |           |           |
         Public Website Database  HR VLAN   IT Admin   Dev/Tools VLAN
                                    |          |           |
                                    |      Bastion/VPN   Jira/Git
                                    |
                            [ Internal Firewall ]
                                    |
                          HR App Server (Nginx + Gunicorn + Django)
                                    |
                            MariaDB HR Database Server
                                    |
                         Logs / Monitoring / Backup Server
```

### Relationship With Enterprise Infrastructure

The HR application fits into the wider cybersecurity project as follows:

| Component | Role in the architecture |
|---|---|
| Firewall | Enforces network segmentation and internal-only access |
| Zero Trust access | Requires identity verification before admin access |
| Jira | Tracks stories, controls changes, and supports auditability |
| GitHub/GitLab | Stores source code with branch protection and PR review |
| Monitoring tools | Detect downtime, authentication abuse, and system anomalies |
| SIEM/logging | Centralizes security and audit events |

## 2. Technology Stack

### Recommended Stack

| Layer | Recommendation | Why it fits this project |
|---|---|---|
| Frontend | Django templates + Bootstrap | Simple, fast to build, fewer client-side attack surfaces than a SPA |
| Backend | Django 6 + Django REST Framework | Mature auth, ORM, CSRF protection, validation, admin-friendly ecosystem |
| Database | MariaDB | Strong relational support, transactions, indexing, utf8mb4 support, and straightforward grants |
| App Server | Gunicorn | Stable production WSGI server for Django |
| Reverse Proxy | Nginx | TLS termination, request filtering, rate limiting, static file serving |
| Authentication | Django session auth with Argon2id | Safer for internal browser apps than storing JWTs in the browser |
| Authorization | Role-based access control using Django Groups | Simple and realistic for HR, admin, and IT read-only roles |

### Why Not JWT For This Use Case

For an internal web application accessed through a browser, server-side sessions are usually simpler and safer than JWT in local storage:

- easier logout and session invalidation
- built-in CSRF protections with forms and cookies
- reduced token handling complexity for students

JWT can still be used later for service-to-service access if needed.

## 3. Database Design

### Core Schema Design

The database should normalize departments and keep employees in a dedicated table. Audit logs should be recorded separately so HR actions can be reviewed.

### Main Tables

| Table | Purpose |
|---|---|
| `departments` | Controlled list of departments |
| `employees` | Employee master record |
| `audit_log` | Tracks create, update, suspend, and login-related events |

### Security Design Principles

- Use a dedicated application account with only required privileges
- Use a separate migration/admin account for schema changes
- Do not let the web app connect as a database superuser
- Enforce constraints in the database, not only in the UI
- Use unique constraints for identifiers and email addresses

### Example MariaDB Schema

```sql
CREATE TABLE departments (
    department_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (department_id),
    UNIQUE KEY uq_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE employees (
    employee_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    employee_code VARCHAR(20) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    department_id BIGINT UNSIGNED NOT NULL,
    position_title VARCHAR(120) NOT NULL,
    salary DECIMAL(12,2) NOT NULL,
    hire_date DATE NOT NULL,
    employment_status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (employee_id),
    UNIQUE KEY uq_employees_employee_code (employee_code),
    UNIQUE KEY uq_employees_email (email),
    KEY idx_employees_last_name (last_name),
    KEY idx_employees_department_status (department_id, employment_status),
    CONSTRAINT fk_employees_department
        FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE RESTRICT,
    CONSTRAINT chk_employees_salary CHECK (salary >= 0),
    CONSTRAINT chk_employees_status CHECK (
        employment_status IN ('ACTIVE', 'ON_LEAVE', 'SUSPENDED', 'TERMINATED')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_log (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor_username VARCHAR(150) NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    target_table VARCHAR(100) NOT NULL,
    target_id BIGINT UNSIGNED NULL,
    source_ip VARCHAR(45) NULL,
    details JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (audit_id),
    KEY idx_audit_log_created_at (created_at),
    KEY idx_audit_log_actor_username (actor_username),
    CONSTRAINT chk_audit_action_type CHECK (
        action_type IN ('CREATE', 'UPDATE', 'SUSPEND', 'DELETE', 'LOGIN', 'LOGOUT')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Example Least-Privilege Accounts

```sql
CREATE USER 'hr_app_user'@'10.20.30.10' IDENTIFIED BY 'replace_me';
CREATE USER 'hr_reporting_ro'@'10.20.30.10' IDENTIFIED BY 'replace_me_reporting';

GRANT SELECT ON ytech_hr.departments TO 'hr_app_user'@'10.20.30.10';
GRANT SELECT, INSERT, UPDATE ON ytech_hr.employees TO 'hr_app_user'@'10.20.30.10';
GRANT SELECT, INSERT ON ytech_hr.audit_log TO 'hr_app_user'@'10.20.30.10';

GRANT SELECT ON ytech_hr.departments TO 'hr_reporting_ro'@'10.20.30.10';
GRANT SELECT ON ytech_hr.employees TO 'hr_reporting_ro'@'10.20.30.10';
GRANT SELECT ON ytech_hr.audit_log TO 'hr_reporting_ro'@'10.20.30.10';
```

### Validation and Integrity

- `employee_code` must be unique
- `email` must be unique under a case-insensitive collation
- `salary` cannot be negative
- `department_id` must exist before an employee can be inserted
- hard deletes should be disabled; use suspension or status changes instead

## 4. CRUD API Design

Use versioned endpoints under `/api/v1/`.

### Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/employees` | Create employee |
| `GET` | `/api/v1/employees` | List or search employees |
| `GET` | `/api/v1/employees/{employee_id}` | Get one employee |
| `PUT` | `/api/v1/employees/{employee_id}` | Full update |
| `PATCH` | `/api/v1/employees/{employee_id}` | Partial update |
| `POST` | `/api/v1/employees/{employee_id}/suspend` | Suspend employee without deleting the record |
| `GET` | `/api/v1/departments` | List departments |

### Example Create Request

```http
POST /api/v1/employees
Content-Type: application/json
```

```json
{
  "employee_code": "YTHR-0024",
  "first_name": "Sara",
  "last_name": "Bennani",
  "email": "sara.bennani@ytech.local",
  "department_id": 2,
  "position_title": "HR Specialist",
  "salary": 14000.00,
  "hire_date": "2026-02-03",
  "employment_status": "ACTIVE"
}
```

### Example Create Response

```json
{
  "employee_id": 24,
  "employee_code": "YTHR-0024",
  "first_name": "Sara",
  "last_name": "Bennani",
  "email": "sara.bennani@ytech.local",
  "department_id": 2,
  "position_title": "HR Specialist",
  "salary": 14000.00,
  "hire_date": "2026-02-03",
  "employment_status": "ACTIVE",
  "created_at": "2026-03-14T10:00:00Z",
  "updated_at": "2026-03-14T10:00:00Z"
}
```

### Example Search Endpoint

```http
GET /api/v1/employees?q=sara&department_id=2&status=ACTIVE&page=1&page_size=20
```

### Input Validation Rules

- reject unknown fields
- validate email format
- validate date format
- enforce salary numeric range
- enforce allowed status values including `SUSPENDED`
- trim whitespace and normalize casing where appropriate
- use serializer or schema validation before any database operation

In Django REST Framework, use serializers with explicit field definitions and object-level validation.

## 5. Authentication and Authorization

### Authentication Design

Recommended approach:

- users authenticate at `/login`
- passwords stored using Argon2id
- successful login creates a server-side session
- session ID stored in a secure cookie
- session rotated after login
- idle timeout and absolute timeout enforced

### Password Security

- use Argon2id as primary password hasher
- minimum password length of 12
- block common passwords
- disable password reuse if possible
- prefer MFA for privileged accounts through VPN or SSO

### Session Management

| Control | Recommendation |
|---|---|
| Cookie flags | `Secure`, `HttpOnly`, `SameSite=Lax` or `Strict` |
| Idle timeout | 15 to 30 minutes |
| Absolute timeout | 8 hours |
| Session rotation | rotate on login and privilege change |
| Logout | explicit logout button and server-side invalidation |

### Role-Based Access Control

| Role | Permissions |
|---|---|
| HR User | Create, read, update, and suspend employees; cannot manage users or system config |
| HR Admin | Full HR management, department maintenance, user-role assignment within HR scope, and suspend actions |
| IT Admin | Read-only access for support, auditing, and troubleshooting |

### How Access Is Restricted

Access is restricted at multiple layers:

1. Internal network access only
2. Firewall permit rules only from approved subnets
3. Login required for every application action
4. Role checks on each sensitive endpoint
5. Database access only from the application server

## 6. Security Architecture

### Protection Against Common Attacks

| Threat | Mitigation |
|---|---|
| SQL Injection | ORM queries, parameterized statements, least-privilege DB account |
| XSS | Django auto-escaping, output encoding, CSP, no unsafe HTML rendering |
| CSRF | Django CSRF tokens for forms and authenticated state-changing requests |
| Brute force login | Rate limiting, account lockout, monitoring, MFA for admins |
| Session hijacking | Secure cookies, HTTPS only, session rotation, timeout enforcement |
| Broken access control | RBAC checks, server-side permission enforcement, route guards |

### Secure Coding Practices

- validate on both client side and server side
- never trust hidden form fields
- centralize validation logic
- log security-relevant events
- store secrets in environment variables or a secrets manager
- use dependency scanning and static analysis in CI

### Recommended HTTP Security Headers

```text
Content-Security-Policy: default-src 'self';
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## 7. Network Security and Isolation

### Network Placement

| Asset | Recommended location |
|---|---|
| HR user workstations | HR user VLAN |
| HR app server | Internal application VLAN |
| HR database server | Protected data VLAN |
| Public website | DMZ or public application zone |
| Admin access | Bastion host or VPN with MFA |

### Firewall Rules

| Source | Destination | Port | Action | Reason |
|---|---|---|---|---|
| HR VLAN | HR app server | 443 | Allow | HR users access the app |
| IT admin subnet | Bastion host | 22 or VPN | Allow | Controlled administration |
| Bastion host | HR app server | 22 | Allow | Admin management path |
| HR app server | HR database server | 3306 | Allow | Application-to-database traffic |
| Monitoring server | HR app server | agent port | Allow | Health and security monitoring |
| Internet | HR app server | any | Deny | Internal-only application |
| HR VLAN | HR database server | 3306 | Deny | Users must not access DB directly |

### Why This Improves CIA

| Principle | Improvement |
|---|---|
| Confidentiality | Only internal HR staff can reach the application |
| Integrity | Role checks and DB constraints reduce unauthorized or invalid changes |
| Availability | Segmentation reduces blast radius and supports focused monitoring and backup |

## 8. Integration With Jira

### Suggested Epics

| Epic | Goal |
|---|---|
| HR Application Development | Build the internal HR web application |
| Authentication System | Implement secure login, roles, and session management |
| Employee CRUD Features | Create employee management workflows |
| Security Hardening | Add defensive controls and security tests |
| Deployment and Operations | Deploy, monitor, back up, and document the system |

### Example User Stories

| ID | User story |
|---|---|
| HR-01 | As an HR user, I can add a new employee so that records stay up to date |
| HR-02 | As an HR user, I can search employees by name, department, or status |
| HR-03 | As an HR admin, I can update employee information without breaking data integrity |
| HR-04 | As an HR admin, I can suspend an employee record without deleting history |
| SEC-01 | As a security reviewer, I need audit logs for create, update, and suspend actions |
| OPS-01 | As an IT admin, I need the application deployed only on the internal network |

### Example Tasks

- create database schema and migrations
- build login page and session management
- implement employee list with pagination and search
- implement create and update employee forms with validation
- implement role checks for HR user, HR admin, and IT admin
- configure Nginx and internal DNS
- enable backups and monitoring
- perform security testing before release

## 9. DevOps and Repository Structure

### Recommended Folder Structure

```text
backend/
  hr_core/
  employees/
  accounts/
  requirements.txt
  manage.py
frontend/
  templates/
  static/
database/
  schema.sql
  migrations/
config/
  nginx/
  systemd/
docs/
  architecture/
  runbooks/
  jira/
tests/
  api/
  integration/
  security/
```

### Git Workflow

Recommended:

- protect `main`
- use short-lived feature branches such as `feature/hr-create-employee`
- require pull requests
- require at least one reviewer
- run tests, linting, SAST, and secret scanning before merge

### Branching Example

| Branch | Use |
|---|---|
| `main` | production-ready code |
| `develop` | optional integration branch for student teams |
| `feature/*` | individual features |
| `hotfix/*` | urgent production fixes |

## 10. Deployment Guide

### Linux Deployment Flow

1. Provision an internal Linux VM for the HR app server.
2. Provision a separate internal Linux VM for MariaDB.
3. Create internal DNS entry such as `hr.ytech.local`.
4. Install Python, MariaDB client/build libraries, Nginx, and Gunicorn.
5. Deploy the Django application under a dedicated service account.
6. Store secrets in environment variables or a vault.
7. Configure Nginx to listen only on the private interface.
8. Apply firewall rules so only internal HR users can connect.

### Example App Server Steps

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential pkg-config default-libmysqlclient-dev mariadb-client nginx
sudo adduser --system --group hrapp
sudo mkdir -p /opt/ytech-hr
sudo chown -R hrapp:hrapp /opt/ytech-hr
```

### Example Environment Variables

```env
DEBUG=False
SECRET_KEY=replace-with-long-random-value
ALLOWED_HOSTS=hr.ytech.local,10.20.30.10
DATABASE_URL=mariadb://hr_app_user:strong_password@10.20.40.20:3306/ytech_hr
CSRF_TRUSTED_ORIGINS=https://hr.ytech.local
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Internal-Only Enforcement

Use all of the following:

- private RFC1918 IP address only
- internal DNS only
- Nginx bound to private interface
- firewall deny from Internet
- no NAT or reverse publishing to the HR server

## 11. Hardening and Security Best Practices

### Application Hardening

- disable `DEBUG` in production
- rotate secrets on a schedule
- enable structured application logs
- log authentication failures and CRUD changes
- apply security patches regularly

### Audit and Logging

Log at least:

- successful and failed logins
- employee create, update, suspend actions
- role changes
- admin access events

Each log should include:

- timestamp
- username
- source IP
- action performed
- target record ID

### Backup Strategy

- daily MariaDB backups
- encrypted backup storage
- restore test at least monthly
- keep retention based on policy, for example 30 to 90 days

### Secrets Management

- never commit secrets to Git
- use `.env` only for local development
- use a vault or secret store in production
- rotate database passwords and application keys

### Monitoring

- uptime monitoring for app server and database
- disk and memory alerts
- authentication failure alerts
- backup success/failure alerts

## 12. Optional Improvements

Useful upgrades after the MVP:

- Docker or Podman deployment
- audit trail UI for HR actions
- richer suspension workflows with employee history tracking
- CI/CD pipeline with SAST and dependency scanning
- LDAP, Active Directory, or SSO integration
- encrypted salary field or column-level protection for highly sensitive data
- MFA for all HR users

## Recommended MVP Scope

For a student project, the most realistic secure MVP is:

- Django server-rendered application
- MariaDB database on a separate host
- role-based login with session cookies
- internal-only network access
- employee CRUD plus search
- audit logging
- Nginx reverse proxy with TLS on the internal network

This gives a realistic enterprise design while staying small enough to implement and explain.
