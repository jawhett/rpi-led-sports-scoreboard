import unittest
from data.nba_wnba_data import determine_team_abbreviation

class TestDetermineTeamAbbreviation(unittest.TestCase):
    def test_valid_nba_team(self):
        # Test a known valid NBA team ID
        self.assertEqual(determine_team_abbreviation(1610612737, 'NBA'), 'ATL')
        self.assertEqual(determine_team_abbreviation(1610612738, 'NBA'), 'BOS')

    def test_valid_wnba_team(self):
        # Test a known valid WNBA team ID
        self.assertEqual(determine_team_abbreviation(1611661313, 'WNBA'), 'NYL')
        self.assertEqual(determine_team_abbreviation(1611661317, 'WNBA'), 'PHX')

    def test_invalid_nba_team(self):
        # Test an invalid NBA team ID
        self.assertIsNone(determine_team_abbreviation(9999999999, 'NBA'))

    def test_invalid_wnba_team(self):
        # Test an invalid WNBA team ID
        self.assertIsNone(determine_team_abbreviation(9999999999, 'WNBA'))

    def test_cross_league_ids(self):
        # Test using WNBA ID with NBA league
        self.assertIsNone(determine_team_abbreviation(1611661313, 'NBA'))
        # Test using NBA ID with WNBA league
        self.assertIsNone(determine_team_abbreviation(1610612737, 'WNBA'))

    def test_invalid_league(self):
        # The current implementation defaults to WNBA mapping if league_abrv is not 'NBA'
        # So providing an invalid league with a WNBA ID should return the WNBA team
        self.assertEqual(determine_team_abbreviation(1611661313, 'INVALID_LEAGUE'), 'NYL')
        # Providing an invalid league with an NBA ID should return None
        self.assertIsNone(determine_team_abbreviation(1610612737, 'INVALID_LEAGUE'))

if __name__ == '__main__':
    unittest.main()
