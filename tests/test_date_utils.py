import unittest
from unittest.mock import patch
from datetime import datetime, date
from utils.date_utils import determine_dates_to_display_games

class TestDateUtils(unittest.TestCase):
    @patch('utils.date_utils.datetime')
    def test_determine_dates_to_display_games(self, mock_datetime):
        # We need mock_datetime.strptime to behave like the real one
        mock_datetime.strptime = datetime.strptime

        # Test 1: Current time is strictly before the rollover start time.
        # e.g., current time is 08:00, rollover is 09:00 to 11:00
        mock_datetime.today.return_value = datetime(2023, 10, 15, 8, 0, 0)
        result = determine_dates_to_display_games('09:00', '11:00')
        self.assertEqual(result, [date(2023, 10, 14)])

        # Test 2: Current time is exactly at the rollover start time.
        # e.g., current time is 09:00, rollover is 09:00 to 11:00
        mock_datetime.today.return_value = datetime(2023, 10, 15, 9, 0, 0)
        result = determine_dates_to_display_games('09:00', '11:00')
        self.assertEqual(result, [date(2023, 10, 14), date(2023, 10, 15)])

        # Test 3: Current time is strictly between rollover start and end times.
        # e.g., current time is 10:00, rollover is 09:00 to 11:00
        mock_datetime.today.return_value = datetime(2023, 10, 15, 10, 0, 0)
        result = determine_dates_to_display_games('09:00', '11:00')
        self.assertEqual(result, [date(2023, 10, 14), date(2023, 10, 15)])

        # Test 4: Current time is exactly at the rollover end time.
        # e.g., current time is 11:00, rollover is 09:00 to 11:00
        mock_datetime.today.return_value = datetime(2023, 10, 15, 11, 0, 0)
        result = determine_dates_to_display_games('09:00', '11:00')
        self.assertEqual(result, [date(2023, 10, 15)])

        # Test 5: Current time is strictly after the rollover end time.
        # e.g., current time is 12:00, rollover is 09:00 to 11:00
        mock_datetime.today.return_value = datetime(2023, 10, 15, 12, 0, 0)
        result = determine_dates_to_display_games('09:00', '11:00')
        self.assertEqual(result, [date(2023, 10, 15)])

if __name__ == '__main__':
    unittest.main()
