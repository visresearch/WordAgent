import unittest

from pydantic import ValidationError

from app.api.routes.settings import UserSettings


class UserSettingsTemperatureTests(unittest.TestCase):
    def test_temperature_defaults_to_half(self):
        self.assertEqual(UserSettings().temperature, 0.5)

    def test_temperature_accepts_range_boundaries(self):
        self.assertEqual(UserSettings(temperature=0).temperature, 0)
        self.assertEqual(UserSettings(temperature=1).temperature, 1)

    def test_temperature_rejects_values_outside_range(self):
        for value in (-0.01, 1.01):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    UserSettings(temperature=value)


if __name__ == "__main__":
    unittest.main()
