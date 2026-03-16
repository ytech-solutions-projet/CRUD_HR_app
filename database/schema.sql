CREATE DATABASE IF NOT EXISTS ytech_hr
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ytech_hr;

CREATE TABLE IF NOT EXISTS departments (
    department_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (department_id),
    UNIQUE KEY uq_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employees (
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

CREATE TABLE IF NOT EXISTS audit_log (
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

CREATE USER IF NOT EXISTS 'hr_app_user'@'10.20.30.10' IDENTIFIED BY 'replace_me';
CREATE USER IF NOT EXISTS 'hr_reporting_ro'@'10.20.30.10' IDENTIFIED BY 'replace_me_reporting';

GRANT SELECT ON ytech_hr.departments TO 'hr_app_user'@'10.20.30.10';
GRANT SELECT, INSERT, UPDATE ON ytech_hr.employees TO 'hr_app_user'@'10.20.30.10';
GRANT SELECT, INSERT ON ytech_hr.audit_log TO 'hr_app_user'@'10.20.30.10';

GRANT SELECT ON ytech_hr.departments TO 'hr_reporting_ro'@'10.20.30.10';
GRANT SELECT ON ytech_hr.employees TO 'hr_reporting_ro'@'10.20.30.10';
GRANT SELECT ON ytech_hr.audit_log TO 'hr_reporting_ro'@'10.20.30.10';

FLUSH PRIVILEGES;
