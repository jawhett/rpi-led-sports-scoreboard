from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.mlb_data
from utils import data_utils, date_utils

from datetime import datetime as dt
from time import sleep


from utils.font_utils import draw_text_3x5, get_text_3x5_width
from utils.format_utils import parse_odds
import os
from utils import image_utils
from PIL import Image
class MLBGamesScene(GamesScene):
    """ Game scene for the MLB. Contains functionality to pull data from MLB API, parse, and build+display specific images based on the result.
    This class extends the general Scene and GameScene classes. An object of this class type is created when the scoreboard is started.
    """

    def __init__(self):
        """ Defines the league as MLB. Used to identify the correct files when adding logos to images.
        First runs init from the generic GameScene class.
        """
        
        super().__init__()
        self.LEAGUE = 'MLB'


    def display_scene(self):
        """ Displays the scene on the matrix.
        Includes logic on which image to build, when to display, etc.
        """

        # Refresh config and load to settings key.
        self.settings = data_utils.read_yaml('config.yaml')['scene_settings'][self.LEAGUE.lower()]['games']
        self.alt_logos = data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] if data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] else {} # Note the teams with an alternative logo per config.yaml.

        # Determine which days should be displayed. Will generate a list with one or two elements. Two means rollover time and yesterdays games should be displayed.
        dates_to_display = date_utils.determine_dates_to_display_games(self.settings['rollover']['rollover_start_time_local'], self.settings['rollover']['rollover_end_time_local'])
        display_yesterday = True if len(dates_to_display) == 2 else False # Will have to display yesterdays games if dates_to_display has 2 elements.

        # If in rollover time, and the data for previous day hasn't been saved / is from a different date than needed, then pull it.
        # This will ensure we don't need to pull the previous day data (that doesn't change) every loop.
        if display_yesterday:
            if (hasattr(self, 'data_previous_day') and self.data_previous_day['saved_date'] != dates_to_display[0]) or not hasattr(self, 'data_previous_day'):
                self.data_previous_day = {
                    'saved_date': dates_to_display[0], # Note the previous date.
                    'games': data.mlb_data.get_games(dates_to_display[0]) # Get data for previous date.
                }
        
        # Get current day game data. Save this for future reference.
        self.data = {
            'games_previous_pull': self.data['games'] if hasattr(self, 'data') else None, # If this is the first time this is run, we'd expect self.data to not exist.
            'games': data.mlb_data.get_games(dates_to_display[-1]), # Get data for current day. Current day will always be the last element of dates_to_display.
        }

        # If there are games to display from yesterday (and setting is enabled), build and display splash image (if enabled), then images for those games.
        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time']:
            if self.settings['splash']['display_splash']:
                self.display_splash_image(len(self.data_previous_day['games']), date=dates_to_display[0])
            self.display_game_images(self.data_previous_day['games'], date=dates_to_display[0])

        # For the current day's games, note if any runs were scored since the last data pull.
        if self.data['games_previous_pull']: # Only applicable if there's a previous copy to compare to.
            for game in self.data['games']:
                if game['status'] not in ['Preview']: # Not applicable if the game hasn't started yet.
                    # Match games between data pulls.
                    matched_game = next(filter(lambda x: x['game_id'] == game['game_id'], self.data['games_previous_pull']))

                    if matched_game['status'] not in ['Preview']: # Not applicable if the game hasn't started yet in the previous pull.
                        # Determine if either team scored and set keys accordingly.
                        game['away_team_scored'] = True if game['away_score'] > matched_game['away_score'] else False
                        game['home_team_scored'] = True if game['home_score'] > matched_game['home_score'] else False
                        
                        if game['away_team_scored'] and game['home_team_scored']:
                            game['scoring_team'] = 'both'
                        elif game['away_team_scored']:
                            game['scoring_team'] = 'away'
                        elif game['home_team_scored']:
                            game['scoring_team'] = 'home'
                    
        # Display splash (if enabled) for current day.
        if self.settings['splash']['display_splash']:
            self.display_splash_image(len(self.data['games']), date=dates_to_display[-1])
        
        # Display game image(s) for current day.
        self.display_game_images(self.data['games'], date=dates_to_display[-1])


    def display_splash_image(self, num_games, date):
        """ Builds and displays splash screen for games on date.

        Args:
            num_games (int): Num of games happening on date.
            date (date): Date of games.
        """
        
        # Build splash image, transition in, pause, transition out. 
        self.build_splash_image(num_games, date)
        self.transition_image(direction='in', image_already_combined=True)
        sleep(self.settings['splash']['splash_display_duration'])
        self.transition_image(direction='out', image_already_combined=True)
                                                                                               

    def display_game_images(self, games, date=None):
        """ Builds and displays images on the matrix for each game in games.

        Args:
            games (list): List of game dicts. Each element has all details for a single game.
            date (date, optional): Date of games. Only used to build 'no games' image when there's... well, no games on that data. Defaults to None.
        """
        
        # If there's any games to display, loop through them and build the appropriate images.
        if games:
            for game in games:
                # If the game has yet to begin, build the game not started image (or TBD image if the start time is to be determined).
                if game['status'] in ['Preview']:
                    if game['start_time_tbd'] or 'Delayed' in game['detailed_status']:
                        self.build_game_tbd_image(game)
                    else:
                        self.build_game_not_started_image(game)

                # If the game is postponed, build the game postponed image. Need to check for these first as the API also says these games are 'Final'.
                elif game['detailed_status'] in ['Postponed']:
                    self.build_game_postponed_image(game)

                # If the game is over, build the final score image.
                elif game['status'] in ['Final']:
                    self.build_game_complete_image(game)

                # Otherwise, the game is in progress. Build the game in progress screen.
                elif game['status'] in ['Live', 'Delayed']: # TODO: Confirm that a game is delayed once it's started due to weather or other factors. Adjust logic as needed if there are any differences in the API results for a delayed game vs a live game.
                    self.build_game_in_progress_image(game)
                else:
                    print(f"Unexpected game status encountered from API: {game['status']}.")

                # Transition the image in on the matrix.
                self.transition_image(direction='in', image_already_combined=True)

                # If a run was scored, do score fade animation (if enabled).
                if self.settings['score_alerting']['score_coloured'] and self.settings['score_alerting']['score_fade_animation']:
                    if game['scoring_team']:
                        self.fade_score_change(game)
                
                # Hold image for calculated duration and transition out.
                sleep(self.settings['game_display_duration'])
                self.transition_image(direction='out', image_already_combined=True)
        
        # If there's no games to display, and splash is disabled, build and display the no games image.
        elif not self.settings['splash']['display_splash']:
            self.build_no_games_image(date)
            self.transition_image(direction='in', image_already_combined=True)
            sleep(self.settings['game_display_duration'])
            self.transition_image(direction='out', image_already_combined=True)





    def get_not_started_banner_text(self, game, rotation_mode=0):
        from utils.format_utils import parse_odds
        from utils.font_utils import get_text_3x5_width

        odds_raw = game.get('odds_str')
        parsed_odds = parse_odds(odds_raw) if odds_raw else None
        if parsed_odds:
            spread = parsed_odds.get('spread', '')
            fav = parsed_odds.get('fav_team', '')
            ou = parsed_odds.get('ou', '')

            if rotation_mode == 1 and ou:
                ou_clean = ou.replace(".0", "")
                return f"U{ou_clean}", self.COLOURS['yellow_bright']
            elif fav and spread:
                fav_short = fav[:2] if len(fav) > 2 else fav
                cand = f"{fav_short} {spread}"
                if get_text_3x5_width(cand) <= 19:
                    return cand, self.COLOURS['yellow_bright']
                cand2 = f"{fav_short}{spread}"
                if get_text_3x5_width(cand2) <= 19:
                    return cand2, self.COLOURS['yellow_bright']
                return spread, self.COLOURS['yellow_bright']
            elif spread:
                return spread, self.COLOURS['yellow_bright']
            elif ou:
                return f"U{ou}", self.COLOURS['yellow_bright']

        broadcaster = game.get('broadcaster') or game.get('tv')
        if broadcaster:
            return broadcaster.upper()[:6], self.COLOURS['cyan']

        return "", self.COLOURS['white']

    def get_final_period_str(self, game):
        if game.get('inning_num', 9) > 9:
            return str(game['inning_num'])
        return ""

    def build_game_in_progress_image(self, game):
        """ Builds a unified stadium-style scoreboard image for live MLB games in progress.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])

        # Helper to scale and center logos with aspect-ratio awareness
        def paste_logo(logo_img, target_x_center, target_y_center=10):
            if not logo_img:
                return
            w, h = logo_img.size
            if w <= 0 or h <= 0:
                return
            aspect = float(w) / float(h)
            if aspect > 1.3:  # Wide logo: allow expanding up to 28px width
                scale = min(28.0 / w, 20.0 / h)
            elif aspect < 0.77:  # Tall logo: allow expanding up to 21px height
                scale = min(22.0 / w, 21.0 / h)
            else:  # Square-ish logo
                scale = min(22.0 / w, 20.0 / h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            resized = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            pos_x = max(0, min(64 - new_w, target_x_center - new_w // 2))
            pos_y = max(0, min(32 - new_h, target_y_center - new_h // 2))
            self.images['full'].paste(resized, (pos_x, pos_y))

        # 1. ROWS 0..21: TEAM LOGOS (aspect-ratio aware)
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                paste_logo(away_logo, target_x_center=11, target_y_center=10)
            except Exception as e:
                pass

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                paste_logo(home_logo, target_x_center=53, target_y_center=10)
            except Exception as e:
                pass

        # Center Channel (cols 22..41, rows 0..21): Inning & Graphical Diamond & Outs
        inning_num = game.get('inning_num', 1)
        inning_state = game.get('inning_state', 'Top')
        
        # 1. Row 1: Inning Arrow & Number
        if inning_state in ['Top', 'Start']:
            num_str = str(inning_num)
            w_num = get_text_3x5_width(num_str)
            total_w = 3 + 1 + w_num
            x_start = 32 - total_w // 2
            # 3x5 Up Arrow (▲)
            self.draw['full'].point((x_start + 1, 1), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].line([(x_start, 2), (x_start + 2, 2)], fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 3), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 4), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 5), fill=self.COLOURS['yellow_bright'])
            draw_text_3x5(self.draw['full'], x_start + 4, 1, num_str, self.COLOURS['white'])
        elif inning_state == 'Bottom':
            num_str = str(inning_num)
            w_num = get_text_3x5_width(num_str)
            total_w = 3 + 1 + w_num
            x_start = 32 - total_w // 2
            # 3x5 Down Arrow (▼)
            self.draw['full'].point((x_start + 1, 1), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 2), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 3), fill=self.COLOURS['yellow_bright'])
            self.draw['full'].line([(x_start, 4), (x_start + 2, 4)], fill=self.COLOURS['yellow_bright'])
            self.draw['full'].point((x_start + 1, 5), fill=self.COLOURS['yellow_bright'])
            draw_text_3x5(self.draw['full'], x_start + 4, 1, num_str, self.COLOURS['white'])
        else:
            mid_str = "MID" if inning_state == 'Middle' else ("END" if inning_state == 'End' else str(inning_state)[:3].upper())
            lbl = f"{mid_str} {inning_num}"
            w_lbl = get_text_3x5_width(lbl)
            draw_text_3x5(self.draw['full'], 32 - w_lbl // 2, 1, lbl, self.COLOURS['yellow_bright'])

        # 2. Rows 7..15: Graphical Baseball Diamond
        dim_line = (60, 60, 60)
        self.draw['full'].line([(31, 9), (27, 12)], fill=dim_line)
        self.draw['full'].line([(32, 9), (36, 12)], fill=dim_line)
        self.draw['full'].line([(27, 13), (31, 15)], fill=dim_line)
        self.draw['full'].line([(36, 13), (32, 15)], fill=dim_line)

        # 2nd Base (Top Apex): (31..32, 8..9)
        color_2nd = self.COLOURS['yellow_bright'] if game.get('runner_on_second') else (75, 75, 75)
        self.draw['full'].rectangle([(31, 8), (32, 9)], fill=color_2nd)

        # 3rd Base (Left Apex): (26..27, 12..13)
        color_3rd = self.COLOURS['yellow_bright'] if game.get('runner_on_third') else (75, 75, 75)
        self.draw['full'].rectangle([(26, 12), (27, 13)], fill=color_3rd)

        # 1st Base (Right Apex): (36..37, 12..13)
        color_1st = self.COLOURS['yellow_bright'] if game.get('runner_on_first') else (75, 75, 75)
        self.draw['full'].rectangle([(36, 12), (37, 13)], fill=color_1st)

        # 3. Row 16..18: Out Indicator Dots ('O' + 2 pips)
        outs = game.get('outs', 0)
        out1_color = self.COLOURS['red_bright'] if outs >= 1 else (55, 55, 55)
        out2_color = self.COLOURS['red_bright'] if outs >= 2 else (55, 55, 55)
        
        draw_text_3x5(self.draw['full'], 25, 16, 'O', self.COLOURS['grey_light'])
        self.draw['full'].rectangle([(30, 17), (31, 18)], fill=out1_color)
        self.draw['full'].rectangle([(34, 17), (35, 18)], fill=out2_color)

        # Batting team possession under-glow on row 21
        if inning_state in ['Top', 'Start']:
            self.draw['full'].rectangle([(6, 21), (16, 21)], fill=self.COLOURS['yellow_bright'])
        elif inning_state == 'Bottom':
            self.draw['full'].rectangle([(47, 21), (57, 21)], fill=self.COLOURS['yellow_bright'])

        # Win Probability / Momentum Micro-Bar (cols 22..41, row 21)
        if game.get('home_win_pct') is not None:
            h_pct = game['home_win_pct']
            away_px = int(round(20 * (100 - h_pct) / 100.0))
            away_color = data_utils.get_team_color(game.get('away_abrv'), self.COLOURS['white'])
            home_color = data_utils.get_team_color(game.get('home_abrv'), self.COLOURS['white'])
            if away_px > 0:
                self.draw['full'].line([(22, 21), (22 + away_px - 1, 21)], fill=away_color)
            if away_px < 20:
                self.draw['full'].line([(22 + away_px, 21), (41, 21)], fill=home_color)
            self.draw['full'].point((32, 21), fill=self.COLOURS['black'])

        # 2. BOTTOM 10 PIXELS (rows 22..31, cols 0..63): ENLARGED SCORES
        away_score_str = str(game.get('away_score', 0))
        home_score_str = str(game.get('home_score', 0))

        color_away = data_utils.get_team_color(game.get('away_abrv'), self.COLOURS['white'])
        if self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']

        color_home = data_utils.get_team_color(game.get('home_abrv'), self.COLOURS['white'])
        if self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']

        score_font = self.FONTS['sm_bold']
        bbox_away = self.draw['full'].textbbox((0, 0), away_score_str, font=score_font)
        w_away = bbox_away[2] - bbox_away[0]
        bbox_home = self.draw['full'].textbbox((0, 0), home_score_str, font=score_font)
        w_home = bbox_home[2] - bbox_home[0]
        bbox_dash = self.draw['full'].textbbox((0, 0), "-", font=score_font)
        w_dash = bbox_dash[2] - bbox_dash[0]

        x_dash = 32 - w_dash // 2
        x_away = x_dash - 2 - w_away
        x_home = x_dash + w_dash + 2

        self.draw['full'].text((x_away, 22), away_score_str, font=score_font, fill=color_away)
        self.draw['full'].text((x_dash, 22), "-", font=score_font, fill=self.COLOURS['grey_light'])
        self.draw['full'].text((x_home, 22), home_score_str, font=score_font, fill=color_home)






