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

        def paste_logo(logo_img, target_x_center, target_y_center=10):
            if not logo_img:
                return
            w, h = logo_img.size
            if w <= 0 or h <= 0:
                return
            aspect = float(w) / float(h)
            if aspect > 1.3:
                scale = min(28.0 / w, 20.0 / h)
            elif aspect < 0.77:
                scale = min(22.0 / w, 21.0 / h)
            else:
                scale = min(22.0 / w, 20.0 / h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            resized = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            pos_x = max(0, min(64 - new_w, target_x_center - new_w // 2))
            pos_y = max(0, min(32 - new_h, target_y_center - new_h // 2))
            self.images['full'].paste(resized, (pos_x, pos_y))

        # 1. Left Logo: Phoenix Suns
        suns_logo_path = 'assets/images/NBA/teams/PHX.png'
        if os.path.exists(suns_logo_path):
            try:
                suns_logo = Image.open(suns_logo_path)
                suns_logo = image_utils.crop_image(suns_logo)
                paste_logo(suns_logo, target_x_center=11, target_y_center=10)
            except Exception as e:
                print(f"Error loading Suns logo: {e}")

        # 2. Right Logo: Opponent
        opp_abrv = next_game.get('opponent_abrv') if next_game else None
        if opp_abrv:
            opp_logo_path = f'assets/images/NBA/teams/{opp_abrv}.png'
            if os.path.exists(opp_logo_path):
                try:
                    opp_logo = Image.open(opp_logo_path)
                    opp_logo = image_utils.crop_image(opp_logo)
                    paste_logo(opp_logo, target_x_center=53, target_y_center=10)
                except Exception:
                    pass

        # 3. Bottom row: Team Tricodes
        score_font = self.FONTS['sm_bold']
        self.draw['full'].text((3, 22), "PHX", font=score_font, fill=self.SUNS_ORANGE)
        if opp_abrv:
            opp_color = data_utils.get_team_color(opp_abrv, fallback=self.COLOURS['white'])
            self.draw['full'].text((47, 22), opp_abrv, font=score_font, fill=opp_color)

        # 4. Center Channel (cols 22..41, width 20px): Countdown & Matchup details
        cur_datetime = dt.today().astimezone()
        if next_game and not next_game.get('is_completed'):
            start_dt = next_game['start_datetime_local']
            days_diff = (start_dt.date() - cur_datetime.date()).days

            if days_diff == 0:
                top_str = "TODAY"
                top_color = self.COLOURS['yellow_bright']
            elif days_diff == 1:
                top_str = "TMRW"
                top_color = self.COLOURS['cyan']
            elif days_diff <= 99:
                top_str = f"IN {days_diff}D"
                top_color = self.COLOURS['yellow_bright']
            else:
                top_str = start_dt.strftime('%b %d').upper()
                top_color = self.COLOURS['yellow_bright']

            w_top = get_text_3x5_width(top_str)
            draw_text_3x5(self.draw['full'], 32 - w_top // 2, 1, top_str, top_color)

            date_str = start_dt.strftime('%b %d').upper()
            if " 0" in date_str: date_str = date_str.replace(" 0", " ")
            w_d = get_text_3x5_width(date_str)
            draw_text_3x5(self.draw['full'], 32 - w_d // 2, 7, date_str, self.COLOURS['white'])

            time_str = start_dt.strftime('%I:%M %p').lstrip('0')
            w_t = get_text_3x5_width(time_str)
            draw_text_3x5(self.draw['full'], max(22, min(32 - w_t // 2, 41 - w_t)), 14, time_str, self.COLOURS['yellow_bright'])

            # Matchup separator @ or VS
            vs_str = "@" if next_game.get('home_or_away') == 'away' else "VS"
            w_vs = get_text_3x5_width(vs_str)
            draw_text_3x5(self.draw['full'], 32 - w_vs // 2, 24, vs_str, self.COLOURS['yellow'])

        elif next_game and next_game.get('is_completed'):
            draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width("LAST") // 2, 1, "LAST", self.COLOURS['grey_light'])
            draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width("FINAL") // 2, 7, "FINAL", self.COLOURS['yellow_bright'])
            res_color = self.COLOURS['green_bright'] if next_game.get('is_win') else self.COLOURS['red_bright']
            res_str = "WIN" if next_game.get('is_win') else "LOSS"
            draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width(res_str) // 2, 14, res_str, res_color)
            score_str = next_game.get('score_str', '')
            if score_str:
                draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width(score_str) // 2, 24, score_str, self.COLOURS['white'])
        else:
            draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width("VALLEY") // 2, 7, "VALLEY", self.SUNS_ORANGE)
            draw_text_3x5(self.draw['full'], 32 - get_text_3x5_width("SUNS HUB") // 2, 14, "SUNS HUB", self.COLOURS['white'])
