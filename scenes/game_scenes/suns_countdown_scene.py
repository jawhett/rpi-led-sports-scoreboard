from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.nba_wnba_data
from utils import data_utils, date_utils, image_utils
from PIL import Image, ImageDraw
from utils.font_utils import FONT_3X5, draw_text_3x5, get_text_3x5_width
from datetime import datetime as dt
from time import sleep
import os

class SunsCountdownScene(GamesScene):
    """ Dedicated Phoenix Suns Hub & Offseason / Break Countdown Scene.
    Displays a prominent Suns display with team colors, next game countdown, or offseason status.
    """

    def __init__(self):
        super().__init__()
        self.LEAGUE = 'NBA'
        self.TEAM = 'PHX'
        self.SUNS_ORANGE = (255, 110, 0)
        self.SUNS_PURPLE = (92, 38, 142)

    def display_scene(self):
        try:
            self.settings = data_utils.read_yaml('config.yaml')['scene_settings']['nba']['fav_team_next_game']
        except Exception:
            self.settings = {'display_duration': 15.0, 'transition': 'modern'}

        next_game = data.nba_wnba_data.get_next_game(self.TEAM, self.LEAGUE)
        
        self.build_suns_countdown_image(next_game)
        self.transition_image(direction='in', image_already_combined=True)
        sleep(self.settings.get('display_duration', 15.0))
        self.transition_image(direction='out', image_already_combined=True)

    def build_suns_countdown_image(self, next_game):
        image_utils.clear_image(self.images['full'], self.draw['full'])

        # 1. Draw large Phoenix Suns Logo (28x28) on the left
        suns_logo_path = 'assets/images/NBA/teams/PHX.png'
        if os.path.exists(suns_logo_path):
            try:
                suns_logo = Image.open(suns_logo_path)
                suns_logo = image_utils.crop_image(suns_logo)
                suns_logo.thumbnail((26, 26))
                y_pos = (32 - suns_logo.height) // 2
                self.images['full'].paste(suns_logo, (1, max(0, y_pos)))
            except Exception as e:
                print(f"Error loading Suns logo: {e}")

        # 2. Draw Opponent Logo on the right
        if next_game and next_game.get('opponent_abrv'):
            opp_abrv = next_game['opponent_abrv']
            opp_logo_path = f'assets/images/NBA/teams/{opp_abrv}.png'
            if os.path.exists(opp_logo_path):
                try:
                    opp_logo = Image.open(opp_logo_path)
                    opp_logo = image_utils.crop_image(opp_logo)
                    opp_logo.thumbnail((22, 22))
                    x_pos = 63 - opp_logo.width
                    y_pos = (32 - opp_logo.height) // 2
                    self.images['full'].paste(opp_logo, (x_pos, max(0, y_pos)))
                except Exception:
                    pass

        # 3. Header text: PHX SUNS
        w_title = get_text_3x5_width("PHX SUNS")
        draw_text_3x5(self.draw['full'], 30, 1, "PHX SUNS", self.SUNS_ORANGE)

        # 4. Countdown / Matchup details
        cur_datetime = dt.today().astimezone()
        
        if next_game and not next_game.get('is_completed'):
            start_dt = next_game['start_datetime_local']
            days_diff = (start_dt.date() - cur_datetime.date()).days

            if days_diff == 0:
                time_str = start_dt.strftime('%I:%M %p').lstrip('0')
                draw_text_3x5(self.draw['full'], 30, 8, "GAMEDAY!", self.COLOURS['yellow_bright'])
                draw_text_3x5(self.draw['full'], 30, 16, time_str, self.COLOURS['white'])
            elif days_diff == 1:
                draw_text_3x5(self.draw['full'], 30, 8, "TOMORROW", self.COLOURS['cyan'])
                time_str = start_dt.strftime('%I:%M %p').lstrip('0')
                draw_text_3x5(self.draw['full'], 30, 16, time_str, self.COLOURS['white'])
            else:
                # Count in days
                count_str = f"IN {days_diff} DAYS"
                draw_text_3x5(self.draw['full'], 30, 8, count_str, self.COLOURS['yellow_bright'])
                # Date and compact time (e.g. OCT 5 4:00P)
                time_compact = start_dt.strftime('%I:%M%p').lstrip('0').replace(':00', '').lower()
                date_str = start_dt.strftime('%b %d').upper()
                if " 0" in date_str: date_str = date_str.replace(" 0", " ")
                info_line = f"{date_str} {time_compact}"
                draw_text_3x5(self.draw['full'], 30, 16, info_line, self.COLOURS['white'])
            
            # Bottom matchup line (@ DET or VS DET)
            venue_str = f"@ {next_game['opponent_abrv']}" if next_game.get('home_or_away') == 'away' else f"VS {next_game['opponent_abrv']}"
            draw_text_3x5(self.draw['full'], 30, 25, venue_str, self.COLOURS['cyan'])

        elif next_game and next_game.get('is_completed'):
            draw_text_3x5(self.draw['full'], 30, 8, "LAST GAME", self.COLOURS['grey_light'])
            res_color = self.COLOURS['green_bright'] if next_game.get('is_win') else self.COLOURS['red_bright']
            res_str = "WIN" if next_game.get('is_win') else "LOSS"
            draw_text_3x5(self.draw['full'], 30, 16, res_str, res_color)
            score_str = next_game.get('score_str', '')
            if score_str:
                draw_text_3x5(self.draw['full'], 30, 25, score_str, self.COLOURS['white'])
        else:
            draw_text_3x5(self.draw['full'], 30, 9, "VALLEY", self.SUNS_ORANGE)
            draw_text_3x5(self.draw['full'], 30, 18, "SUNS HUB", self.COLOURS['white'])
