import time
import sys
import os

# Monkeypatch sleep to make test run instantly
time.sleep = lambda x: None

# Mock matrix before any imports
import setup.matrix_setup
class MockMatrix:
    def __init__(self):
        self.brightness = 100
    def SetImage(self, image, x=0, y=0):
        pass
    def Clear(self):
        pass
    def SwapOnVSync(self, canvas):
        pass

mock_matrix = MockMatrix()
setup.matrix_setup.matrix = mock_matrix

from utils import data_utils

# Monkeypatch display_scene in GamesScene to print what it's doing
from scenes.game_scenes.games_scene import GamesScene
original_display_game_images = GamesScene.display_game_images

def verbose_display_game_images(self, games, date=None):
    print(f"[{self.LEAGUE}] display_game_images called with {len(games) if games else 0} games")
    if games:
        for g in games:
            print(f"  - Game: {g['away_abrv']} @ {g['home_abrv']} (Status: {g['status']}, Score: {g['away_score']}-{g['home_score']})")
    return original_display_game_images(self, games, date)

GamesScene.display_game_images = verbose_display_game_images

# Also patch transition_image to print
def verbose_transition_image(self, direction, image_already_combined=False):
    print(f"  [Transition] {direction}")
    
GamesScene.transition_image = verbose_transition_image

print("Starting debug run of scoreboard (1 loop)...")
scene_order = data_utils.read_yaml('config.yaml')['scene_order']
print("Scene order:", scene_order)

from scenes.game_scenes.games_scene_nba_wnba import NBAWNBAGamesScene
from scenes.game_scenes.games_scene_mlb import MLBGamesScene
from scenes.game_scenes.games_scene_nfl import NFLGamesScene

scene_mapping = {
    'nba_games':                NBAWNBAGamesScene('NBA'),
    'wnba_games':               NBAWNBAGamesScene('WNBA'),
    'mlb_games':                MLBGamesScene(),
    'nfl_games':                NFLGamesScene()
}

for scene in scene_order:
    if scene in scene_mapping:
        print(f"\n--- Running scene: {scene} ---")
        try:
            scene_mapping[scene].display_scene()
        except Exception as e:
            print(f"Error in scene {scene}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

print("\nDebug run complete.")
