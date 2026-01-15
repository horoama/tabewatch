import unittest
import datetime
from worker import is_weekend_change

class TestLogic(unittest.TestCase):
    def test_is_weekend_change(self):
        # 2023-10-27 is Friday
        self.assertFalse(is_weekend_change("📅 2023-10-27: ❌ ➡ ⭕"))

        # 2023-10-28 is Saturday
        self.assertTrue(is_weekend_change("📅 2023-10-28: ❌ ➡ ⭕"))

        # 2023-10-29 is Sunday
        self.assertTrue(is_weekend_change("📅 2023-10-29: ❌ ➡ ⭕"))

        # 2023-10-30 is Monday
        self.assertFalse(is_weekend_change("📅 2023-10-30: ❌ ➡ ⭕"))

        # Test with "New" format
        # 2023-10-28 is Saturday
        self.assertTrue(is_weekend_change("🆕 2023-10-28: ⭕"))

        # Invalid string
        self.assertFalse(is_weekend_change("No date here"))

if __name__ == '__main__':
    unittest.main()
