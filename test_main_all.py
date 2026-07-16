from scenes.game_scenes.games_scene_mlb import MLBGamesScene
from scenes.game_scenes.games_scene_nhl import NHLGamesScene
from scenes.game_scenes.games_scene_nba_wnba import NBAWNBAGamesScene
from scenes.game_scenes.games_scene_nfl import NFLGamesScene
from scenes.game_scenes.games_scene_pwhl import PWHLGamesScene
import unittest

def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("success")
        return 0
    else:
        print("tests failed")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
