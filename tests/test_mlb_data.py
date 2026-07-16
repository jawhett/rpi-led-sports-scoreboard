import unittest
import sys
import os

# Add parent directory to path so we can import from data module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.mlb_data import determine_team_abbreviation

class TestMLBData(unittest.TestCase):
    def test_determine_team_abbreviation_valid(self):
        """Test valid MLB team abbreviations return correct integers"""
        self.assertEqual(determine_team_abbreviation('TOR'), 141)
        self.assertEqual(determine_team_abbreviation('NYY'), 147)
        self.assertEqual(determine_team_abbreviation('LAD'), 119)
        self.assertEqual(determine_team_abbreviation('ATH'), 133)
        self.assertEqual(determine_team_abbreviation('CWS'), 145)

    def test_determine_team_abbreviation_invalid(self):
        """Test invalid abbreviations return None"""
        self.assertIsNone(determine_team_abbreviation('INVALID'))
        self.assertIsNone(determine_team_abbreviation(''))
        self.assertIsNone(determine_team_abbreviation(None))
        self.assertIsNone(determine_team_abbreviation(123))

if __name__ == '__main__':
    unittest.main()
