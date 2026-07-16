import unittest
from unittest.mock import patch, MagicMock
from data.pwhl_data import get_season_id

class TestPWHLData(unittest.TestCase):

    @patch('data.pwhl_data.session')
    def test_get_season_id_regular_season(self, mock_session):
        """Test getting season ID during regular season."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'SiteKit': {
                'Seasons': [
                    {'season_id': '2', 'season_name': 'Regular Season 2024'}
                ],
                'Parameters': {
                    'season_id': '2'
                }
            }
        }
        mock_session.get.return_value = mock_response

        # When in regular season, both with and without playoffs should return the current ID
        self.assertEqual(get_season_id(include_playoffs=True), 2)
        self.assertEqual(get_season_id(include_playoffs=False), 2)

    @patch('data.pwhl_data.session')
    def test_get_season_id_preseason(self, mock_session):
        """Test getting season ID during preseason."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'SiteKit': {
                'Seasons': [
                    {'season_id': '3', 'season_name': 'Preseason 2024'}
                ],
                'Parameters': {
                    'season_id': '3'
                }
            }
        }
        mock_session.get.return_value = mock_response

        # When in preseason, it should return the next season's ID (+1)
        self.assertEqual(get_season_id(include_playoffs=True), 4)
        self.assertEqual(get_season_id(include_playoffs=False), 4)

    @patch('data.pwhl_data.session')
    def test_get_season_id_playoffs(self, mock_session):
        """Test getting season ID during playoffs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'SiteKit': {
                'Seasons': [
                    {'season_id': '4', 'season_name': 'Playoffs 2024'}
                ],
                'Parameters': {
                    'season_id': '4'
                }
            }
        }
        mock_session.get.return_value = mock_response

        # When in playoffs and include_playoffs=True, it should return the current ID
        self.assertEqual(get_season_id(include_playoffs=True), 4)

        # When in playoffs and include_playoffs=False, it should return the previous season's ID (-1)
        self.assertEqual(get_season_id(include_playoffs=False), 3)

    @patch('data.pwhl_data.session')
    def test_get_season_id_api_error(self, mock_session):
        """Test handling of API errors."""
        mock_session.get.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            get_season_id(include_playoffs=True)

if __name__ == '__main__':
    unittest.main()
