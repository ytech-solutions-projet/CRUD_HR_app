import os
from unittest.mock import patch

from django.test import SimpleTestCase

from hr_core.settings import get_database_config


class DatabaseConfigTests(SimpleTestCase):
    def test_postgresql_url_maps_to_django_postgresql_backend(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://hr_app_user:s%40cret@10.20.40.20:5432/ytech_hr",
                "DATABASE_CONN_MAX_AGE": "120",
            },
            clear=False,
        ):
            config = get_database_config()

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "ytech_hr")
        self.assertEqual(config["USER"], "hr_app_user")
        self.assertEqual(config["PASSWORD"], "s@cret")
        self.assertEqual(config["HOST"], "10.20.40.20")
        self.assertEqual(config["PORT"], 5432)
        self.assertEqual(config["CONN_MAX_AGE"], 120)

    def test_unsupported_scheme_raises_clear_error(self):
        with patch.dict(os.environ, {"DATABASE_URL": "mariadb://legacy-db/hr"}, clear=False):
            with self.assertRaisesMessage(
                ValueError,
                "Unsupported DATABASE_URL scheme. Use postgresql://, postgres://, or sqlite:///",
            ):
                get_database_config()
