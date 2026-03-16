import os
from unittest.mock import patch

from django.test import SimpleTestCase

from hr_core.settings import get_database_config


class DatabaseConfigTests(SimpleTestCase):
    def test_mariadb_url_maps_to_django_mysql_backend(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "mariadb://hr_app_user:s%40cret@10.20.40.20:3306/ytech_hr",
                "DATABASE_CONN_MAX_AGE": "120",
            },
            clear=False,
        ):
            config = get_database_config()

        self.assertEqual(config["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(config["NAME"], "ytech_hr")
        self.assertEqual(config["USER"], "hr_app_user")
        self.assertEqual(config["PASSWORD"], "s@cret")
        self.assertEqual(config["HOST"], "10.20.40.20")
        self.assertEqual(config["PORT"], 3306)
        self.assertEqual(config["CONN_MAX_AGE"], 120)
        self.assertEqual(config["OPTIONS"]["charset"], "utf8mb4")

    def test_unsupported_scheme_raises_clear_error(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://legacy-db/hr"}, clear=False):
            with self.assertRaisesMessage(
                ValueError,
                "Unsupported DATABASE_URL scheme. Use mariadb://, mysql://, or sqlite:///",
            ):
                get_database_config()
