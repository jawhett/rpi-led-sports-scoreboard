from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.nhl_data
from utils import data_utils, date_utils, image_utils
from PIL import Image

from datetime import datetime as dt
from time import sleep
import os


class NHLGamesScene(GamesScene):
    """ Game scene for the NHL. Contains functionality to pull data from NHL API, parse, and build+display specific images based on the result.
    This class extends the general Scene and GameScene classes. An object of this class type is created when the scoreboard is started.
    """

    def __init__(self):
        """ Defines the league as NHL. Used to identify the correct files when adding logos to images.
        First runs init from the generic GameScene class.
        """
        
        super().__init__()
        self.LEAGUE = 'NHL'


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
                    'games': data.nhl_data.get_games(dates_to_display[0]) # Get data for previous date.
                }
        
        # Get current day game data. Save this for future reference.
        current_games = data.nhl_data.get_games(dates_to_display[-1])
        
        # If no games today, look back up to 14 days for the most recent games (except when showing yesterday's rollover)
        if not current_games and not display_yesterday:
            from datetime import timedelta
            for days_back in range(1, 15):
                check_date = dates_to_display[-1] - timedelta(days=days_back)
                recent_games = data.nhl_data.get_games(check_date)
                if recent_games:
                    current_games = recent_games
                    break

        self.data = {
            'games_previous_pull': self.data['games'] if hasattr(self, 'data') else None, # If this is the first time this is run, we'd expect self.data to not exist.
            'games': current_games, # Get data for current day. Current day will always be the last element of dates_to_display.
        }

        # If there are games to display from yesterday (and setting is enabled), build and display splash image (if enabled), then images for those games.
        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time']:
            if self.settings['splash']['display_splash']:
                self.display_splash_image(len(self.data_previous_day['games']), date=dates_to_display[0])
            self.display_game_images(self.data_previous_day['games'], date=dates_to_display[0])

        # For the current day's games, note if any goals were scored since the last data pull.
        if self.data['games_previous_pull']: # Only applicable if there's a previous copy to compare to.
            for game in self.data['games']:
                if game['status'] not in ['FUT', 'PRE']: # Not applicable if the game hasn't started yet.
                    # Match games between data pulls.
                    matched_game = next(filter(lambda x: x['game_id'] == game['game_id'], self.data['games_previous_pull']))

                    if matched_game['status'] not in ['FUT', 'PRE']: # Not applicable if the game hasn't started yet in the previous pull.
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
                # If the game has yet to begin, build the game not started image.
                if game['status'] in ['FUT', 'PRE']:
                    duration = self.settings['game_display_duration']
                    elapsed = 0.0
                    step = 1.0
                    
                    self.build_game_not_started_image(game)
                    self.transition_image(direction='in', image_already_combined=True)
                    
                    while elapsed < duration:
                        self.build_game_not_started_image(game)
                        matrix.SetImage(self.images['full'])
                        
                        sleep_time = min(step, duration - elapsed)
                        sleep(sleep_time)
                        elapsed += sleep_time
                        
                    self.transition_image(direction='out', image_already_combined=True)

                # If the game is over, build the final score image.
                elif game['status'] in ['OFF', 'FINAL']:
                    self.build_game_complete_image(game)
                    self.transition_image(direction='in', image_already_combined=True)
                    sleep(self.settings['game_display_duration'])
                    self.transition_image(direction='out', image_already_combined=True)

                # Otherwise, the game is in progress. Build the game in progress screen.
                elif game['status'] in ['LIVE', 'CRIT']:
                    clock_str = game['period_time_remaining']
                    clock_seconds = None
                    if clock_str and not game['is_intermission']:
                        clock_seconds = self.parse_clock_str(clock_str)
                    
                    self.build_game_in_progress_image(game, clock_seconds_override=clock_seconds, blink_colon=False)
                    self.transition_image(direction='in', image_already_combined=True)

                    if self.settings['score_alerting']['score_coloured'] and self.settings['score_alerting']['score_fade_animation']:
                        if game['scoring_team']:
                            self.fade_score_change(game, clock_seconds=clock_seconds)
                    
                    duration = self.settings['game_display_duration']
                    elapsed = 0.0
                    step = 1.0
                    
                    while elapsed < duration:
                        blink = (int(elapsed) % 2 == 1)
                        self.build_game_in_progress_image(
                            game,
                            clock_seconds_override=clock_seconds,
                            blink_colon=blink
                        )
                        matrix.SetImage(self.images['full'])
                        
                        sleep_time = min(step, duration - elapsed)
                        sleep(sleep_time)
                        
                        elapsed += sleep_time
                        if clock_seconds is not None and clock_seconds > 0:
                            if sleep_time >= 0.99:
                                clock_seconds -= 1
                                
                    self.transition_image(direction='out', image_already_combined=True)
                else:
                    print(f"Unexpected gameState encountered from API: {game['status']}.")
        
        # If there's no games to display, and splash is disabled, build and display the no games image.
        elif not self.settings['splash']['display_splash']:
            self.build_no_games_image(date)
            self.transition_image(direction='in', image_already_combined=True)
            sleep(self.settings['game_display_duration'])
            self.transition_image(direction='out', image_already_combined=True)

    def get_final_period_str(self, game):
        if game.get('period_type') == 'SO':
            return "SO"
        elif game.get('period_type') == 'OT' and game.get('period_num', 4) == 4:
            return "OT"
        elif game.get('period_type') == 'OT' and game.get('period_num', 4) > 4:
            return f"{game['period_num'] - 3}OT"
        return ""

    def build_game_in_progress_image(self, game, score_fade_color=None, clock_seconds_override=None, blink_colon=False):
        """ Builds a unified stadium-style scoreboard image for live NHL games in progress.
        """
        from utils.font_utils import get_text_3x5_width, draw_text_3x5

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
                print(f"Error loading logo {away_logo_path}: {e}")

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                paste_logo(home_logo, target_x_center=53, target_y_center=10)
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # Power Play Visual Indicator (Outer 1px vertical strip, rows 6..15)
        if game.get('away_power_play'):
            self.draw['full'].rectangle([(0, 6), (0, 15)], fill=self.COLOURS['yellow_bright'])
        if game.get('home_power_play'):
            self.draw['full'].rectangle([(63, 6), (63, 15)], fill=self.COLOURS['yellow_bright'])

        # Center Info (cols 22..41, rows 0..21): Period & Clock & Shots on Goal
        clock_str = ""
        if game.get('is_intermission'):
            clock_str = "INT"
        elif clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            sep = " " if blink_colon else ":"
            clock_str = f"{m}{sep}{s:02d}"
        else:
            clock_str = game.get('period_time_remaining', '') if game.get('period_time_remaining') else ""

        period_str = ""
        if game.get('period_type') == 'SO': period_str = "SO"
        elif game.get('period_num') == 1: period_str = "1ST"
        elif game.get('period_num') == 2: period_str = "2ND"
        elif game.get('period_num') == 3: period_str = "3RD"
        elif game.get('period_type') == 'OT' and game.get('period_num') == 4: period_str = "OT"
        elif game.get('period_type') == 'OT' and game.get('period_num', 0) > 4: period_str = f"{game['period_num'] - 3}OT"

        if period_str:
            w_p = get_text_3x5_width(period_str)
            draw_text_3x5(self.draw['full'], 32 - w_p // 2, 1, period_str, self.COLOURS['yellow'])
        if clock_str:
            w_c = get_text_3x5_width(clock_str)
            draw_text_3x5(self.draw['full'], 32 - w_c // 2, 7, clock_str, self.COLOURS['white'])

        sog_away = game.get('away_sog')
        sog_home = game.get('home_sog')
        if sog_away is not None and sog_home is not None:
            sog_text = f"S {sog_away}-{sog_home}"
            w_s = get_text_3x5_width(sog_text)
            draw_text_3x5(self.draw['full'], max(22, min(32 - w_s // 2, 41 - w_s)), 14, sog_text, self.COLOURS['yellow_bright'])

        # 2. BOTTOM 10 PIXELS (rows 22..31, cols 0..63): ENLARGED SCORES
        away_score = game.get('away_score', 0) if game.get('away_score') is not None else 0
        home_score = game.get('home_score', 0) if game.get('home_score') is not None else 0

        away_score_str = str(away_score)
        home_score_str = str(home_score)

        color_away = data_utils.TEAM_COLORS.get(game.get('away_abrv'), self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['away', 'both']:
            color_away = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']

        color_home = data_utils.TEAM_COLORS.get(game.get('home_abrv'), self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['home', 'both']:
            color_home = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
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



    def fade_score_change(self, game, clock_seconds=None):
        """ Fades score from red to white after a score change.
        """
        sleep(0.5)
        for n in range(self.COLOURS['red'][2], self.COLOURS['white'][2]):
            self.build_game_in_progress_image(game, score_fade_color=(255, n, n), clock_seconds_override=clock_seconds, blink_colon=False)
            matrix.SetImage(self.images['full'])
            sleep(0.015)


    def add_playing_period_to_image(self, game):
        """ Adds current playing period to the centre image.
        This exists within the specific league class due to huge differences in playing periods between sports (periods, quarters, innings, etc.).

        Args:
            game (dict): Dictionary with all details of a specific game.
        """

        # If intermission, add "INT" to the image.
        if game['is_intermission']:
            self.draw['centre'].text((1, 7), 'INT', font=self.FONTS['med'], fill=self.COLOURS['white'])

        # If the first period, add "1st" to the image.
        if game['period_num'] == 1:
            self.draw['centre'].text((4, -1), '1', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((8, -1), 's', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((12, -1), 't', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the second period, add "2nd" to the image.
        elif game['period_num'] == 2:
            self.draw['centre'].text((3, -1), '2', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((9, -1), 'n', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the third period, add "3rd" to the image.
        elif game['period_num'] == 3:
            self.draw['centre'].text((3, -1), '3', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((9, -1), 'r', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If in shootout or first OT, add that to the image.
        elif game['period_type'] == 'SO' or (game['period_type'] == 'OT' and game['period_num'] == 4):
            self.draw['centre'].text((4, -1), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])

        # Otherwise, we're in 2OT, or later. Calculate the number of OT periods and add that to the image.
        elif game['period_type'] == 'OT':
            per = f"{game['period_num'] - 3}{game['period_type']}"
            self.draw['centre'].text((1, -1), per, font=self.FONTS['med'], fill=self.COLOURS['white'])


    def add_final_playing_period_to_image(self, game):
        """ Adds final playing period to the centre image if game ended in OT, xOT, or a SO.

        Args:
            game (dict): Dictionary with all details of a specific game.
        """

        # If game ended in a SO or the first OT, add that to the centre image.
        if game['period_type'] == 'SO' or (game['period_type'] == 'OT' and game['period_num'] == 4): # If the game ended in single OT a SO.
            self.draw['centre'].text((4, 8), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])

        # Or if in 2OT or later. Calculate the number of OT periods and add that to the centre image.
        elif game['period_type'] == 'OT':
            self.draw['centre'].text((1, 8), str(game['period_num'] - 3), font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((8, 8), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])


    def should_display_time_remaining_in_playing_period(self, game):
        """ Determines if the time remaining in the playing period should be added to the centre image.

        Args:
            game (dict): Dictionary with all details of a specific game.

        Returns:
            Bool: f the time remaining in the playing period should be added to the centre image (True) or not (False).
        """

        if not game['is_intermission'] and game['period_type'] != 'SO':
            return True
        else:
            return False