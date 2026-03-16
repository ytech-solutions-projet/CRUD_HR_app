CREATE DATABASE IF NOT EXISTS ytech_hr
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'hr_app_user'@'10.20.30.10' IDENTIFIED BY 'change_me';
CREATE USER IF NOT EXISTS 'hr_reporting_ro'@'10.20.30.10' IDENTIFIED BY 'change_me_reporting';

GRANT ALL PRIVILEGES ON ytech_hr.* TO 'hr_app_user'@'10.20.30.10';
GRANT SELECT ON ytech_hr.* TO 'hr_reporting_ro'@'10.20.30.10';

FLUSH PRIVILEGES;
