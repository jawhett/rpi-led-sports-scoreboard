import unittest
from data.nba_wnba_data import determine_league_id

class TestNBAWNBAData(unittest.TestCase):

    def test_determine_league_id_nba(self):
        """Test determine_league_id with 'NBA'."""
        self.assertEqual(determine_league_id('NBA'), '00')

    def test_determine_league_id_wnba(self):
        """Test determine_league_id with 'WNBA'."""
        self.assertEqual(determine_league_id('WNBA'), '10')

    def test_determine_league_id_invalid(self):
        """Test determine_league_id with invalid inputs."""
        self.assertIsNone(determine_league_id('NFL'))
        self.assertIsNone(determine_league_id(''))
        self.assertIsNone(determine_league_id(None))
        self.assertIsNone(determine_league_id(123))

if __name__ == '__main__':
    unittest.main()
