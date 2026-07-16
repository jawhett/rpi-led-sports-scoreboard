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
        config_yaml = data_utils.read_yaml('config.yaml')
        self.settings = config_yaml['scene_settings'][self.LEAGUE.lower()]['games']
        self.alt_logos = config_yaml['alt_logos'][self.LEAGUE.lower()] if config_yaml['alt_logos'][self.LEAGUE.lower()] else {} # Note the teams with an alternative logo per config.yaml.

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
        display_behavior = config_yaml.get('display_behavior', {})
        if display_behavior.get('skip_empty_scenes', True):
            has_games_yesterday = False
            has_games_today = False
            if display_yesterday and hasattr(self, 'data_previous_day'):
                has_games_yesterday = len(self.filter_games(self.data_previous_day.get('games', []))) > 0
            if hasattr(self, 'data') and self.data is not None:
                has_games_today = len(self.filter_games(self.data.get('games', []) if self.data else [])) > 0

            if not has_games_yesterday and not has_games_today:
                return

        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time'] and not hasattr(self, 'display_only_live') and not hasattr(self, 'display_only_games'):
            if self.settings['splash']['display_splash'] and not hasattr(self, 'display_only_live') and not hasattr(self, 'display_only_games'):
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
        if self.settings['splash']['display_splash'] and not hasattr(self, 'display_only_live') and not hasattr(self, 'display_only_games'):
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
        games = self.filter_games(games)
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
                    duration = max(12.0, self.settings['game_display_duration'] * 4)
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
                    
                    duration = max(12.0, self.settings['game_display_duration'] * 4)
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

    def build_game_in_progress_image(self, game, score_fade_color=None, clock_seconds_override=None, rotation_mode=0, blink_colon=False, alert_text_override=None):
        """ Builds a stadium-style scoreboard image for games in progress.
        """

        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1 & 2. Draw Team Logos or Names (alternating)
        self.draw_team_logo_or_name(game, 'away', rotation_mode)
        self.draw_team_logo_or_name(game, 'home', rotation_mode)
        # 3. Draw Clock (top center, yellow - y=0)
        clock_str = ""
        if game['is_intermission']:
            clock_str = "INT"
        elif clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            sep = " " if blink_colon else ":"
            clock_str = f"{m}{sep}{s:02d}"
        else:
            clock_str = game['period_time_remaining'] if game['period_time_remaining'] else ""

        if clock_str:
            w = len(clock_str) * 5
            x = 32 - w // 2
            self.draw['full'].text((x, 0), clock_str, font=self.FONTS['sm_bold'], fill=self.COLOURS['yellow'])

        # 4. Period / Stats centered bottom (y=20, using med_bold)
        period_str = ""
        if game['period_type'] == 'SO':
            period_str = "SO"
        elif game['period_num'] == 1:
            period_str = "1ST"
        elif game['period_num'] == 2:
            period_str = "2ND"
        elif game['period_num'] == 3:
            period_str = "3RD"
        elif game['period_type'] == 'OT' and game['period_num'] == 4:
            period_str = "OT"
        elif game['period_type'] == 'OT' and game['period_num'] > 4:
            period_str = f"{game['period_num'] - 3}OT"

        if period_str:
            w = len(period_str) * 6
            x = 32 - w // 2
            self.draw['full'].text((x, 20), period_str, font=self.FONTS['med_bold'], fill=self.COLOURS['cyan'])

        # 5. Draw Away Score (shifted center x=10)
        away_score = game['away_score'] if game['away_score'] is not None else 0
        from PIL import ImageFont
        if away_score >= 100:
            away_font = ImageFont.load('assets/fonts/Tamzen7x14b.pil')
            y_offset = 18
            w = len(str(away_score)) * 7
        else:
            away_font = self.FONTS['lrg_bold']
            y_offset = 15
            w = len(str(away_score)) * 8
        x = 12 - w // 2
        
        color_away = self.COLOURS['white']
        if score_fade_color and game.get('scoring_team') in ['away', 'both']:
            color_away = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']

        self.draw['full'].text((x, y_offset), str(away_score), font=away_font, fill=color_away)

        # 6. Draw Home Score (shifted center x=53)
        home_score = game['home_score'] if game['home_score'] is not None else 0
        if home_score >= 100:
            home_font = ImageFont.load('assets/fonts/Tamzen7x14b.pil')
            y_offset = 18
            w = len(str(home_score)) * 7
        else:
            home_font = self.FONTS['lrg_bold']
            y_offset = 15
            w = len(str(home_score)) * 8
        x = 51 - w // 2
        
        color_home = self.COLOURS['white']
        if score_fade_color and game.get('scoring_team') in ['home', 'both']:
            color_home = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']

        self.draw['full'].text((x, y_offset), str(home_score), font=home_font, fill=color_home)

    def build_game_not_started_image(self, game):
        """ Builds a stadium-style scoreboard image for scheduled games.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1. Draw Away Team Logo
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((22, 16))
                x = (24 - away_logo.width) // 2
                y = (15 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, y))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((22, 16))
                x = 40 + (24 - home_logo.width) // 2
                y = (15 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, y))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # Always show team abbreviations at the bottom (Away=10, Home=53, shifted to y=20)
        w = len(game['away_abrv']) * 6
        x = 12 - w // 2
        self.draw['full'].text((x, 20), game['away_abrv'], font=self.FONTS['med_bold'], fill=self.COLOURS['white'])

        w = len(game['home_abrv']) * 6
        x = 51 - w // 2
        self.draw['full'].text((x, 20), game['home_abrv'], font=self.FONTS['med_bold'], fill=self.COLOURS['white'])

        # Scheduled display details (date/time)
        game_date = game['start_datetime_local'].date()
        today = dt.now().astimezone().date()
        if game_date == today:
            date_str = "TODAY"
        elif (game_date - today).days == 1:
            date_str = "TOMORROW"
        else:
            date_str = game['start_datetime_local'].strftime('%b %d').upper()
            if " 0" in date_str:
                date_str = date_str.replace(" 0", " ")
                
        w = len(date_str) * 5
        x = 32 - w // 2
        self.draw['full'].text((x, 4), date_str, font=self.FONTS['sm_bold'], fill=self.COLOURS['grey_light'])

        time_str = game['start_datetime_local'].time().strftime('%I:%M')
        if time_str.startswith('0'):
            time_str = time_str[1:]
        w = len(time_str) * 5
        x = 32 - w // 2
        self.draw['full'].text((x, 21), time_str, font=self.FONTS['sm_bold'], fill=self.COLOURS['white'])

    def build_game_complete_image(self, game):
        """ Builds a stadium-style scoreboard image for completed games.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1. Draw Away Team Logo
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((22, 16))
                x = (24 - away_logo.width) // 2
                y = (15 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, y))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((22, 16))
                x = 40 + (24 - home_logo.width) // 2
                y = (15 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, y))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # 3. Center top shows FINAL (y=0)
        final_str = "FINAL"
        w = len(final_str) * 6
        x = 32 - w // 2
        self.draw['full'].text((x, 0), final_str, font=self.FONTS['med_bold'], fill=self.COLOURS['red_bright'])

        # 4. Center bottom shows OT/SO details if applicable (y=20, using med_bold)
        ot_str = ""
        if game['period_type'] == 'SO':
            ot_str = "SO"
        elif game['period_type'] == 'OT' and game['period_num'] == 4:
            ot_str = "OT"
        elif game['period_type'] == 'OT' and game['period_num'] > 4:
            ot_str = f"{game['period_num'] - 3}OT"
            
        if ot_str:
            w = len(ot_str) * 6
            x = 32 - w // 2
            self.draw['full'].text((x, 20), ot_str, font=self.FONTS['med_bold'], fill=self.COLOURS['grey_light'])

        # Highlight winner and dim loser scores (shifted centers: Away=10, Home=53)
        away_score = game['away_score'] if game['away_score'] is not None else 0
        home_score = game['home_score'] if game['home_score'] is not None else 0
        
        color_away = self.COLOURS['white'] if away_score >= home_score else self.COLOURS['grey_dark']
        color_home = self.COLOURS['white'] if home_score >= away_score else self.COLOURS['grey_dark']

        # 5. Draw Away Score
        from PIL import ImageFont
        if away_score >= 100:
            away_font = ImageFont.load('assets/fonts/Tamzen7x14b.pil')
            y_offset = 18
            w = len(str(away_score)) * 7
        else:
            away_font = self.FONTS['lrg_bold']
            y_offset = 15
            w = len(str(away_score)) * 8
        x = 12 - w // 2
        self.draw['full'].text((x, y_offset), str(away_score), font=away_font, fill=color_away)

        # 6. Draw Home Score
        if home_score >= 100:
            home_font = ImageFont.load('assets/fonts/Tamzen7x14b.pil')
            y_offset = 18
            w = len(str(home_score)) * 7
        else:
            home_font = self.FONTS['lrg_bold']
            y_offset = 15
            w = len(str(home_score)) * 8
        x = 51 - w // 2
        self.draw['full'].text((x, y_offset), str(home_score), font=home_font, fill=color_home)

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
            self.draw['full'].text((1, 7), 'INT', font=self.FONTS['med'], fill=self.COLOURS['white'])

        # If the first period, add "1st" to the image.
        if game['period_num'] == 1:
            self.draw['full'].text((4, -1), '1', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['full'].text((8, -1), 's', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['full'].text((12, -1), 't', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the second period, add "2nd" to the image.
        elif game['period_num'] == 2:
            self.draw['full'].text((3, -1), '2', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['full'].text((9, -1), 'n', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['full'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the third period, add "3rd" to the image.
        elif game['period_num'] == 3:
            self.draw['full'].text((3, -1), '3', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['full'].text((9, -1), 'r', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['full'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If in shootout or first OT, add that to the image.
        elif game['period_type'] == 'SO' or (game['period_type'] == 'OT' and game['period_num'] == 4):
            self.draw['full'].text((4, -1), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])

        # Otherwise, we're in 2OT, or later. Calculate the number of OT periods and add that to the image.
        elif game['period_type'] == 'OT':
            per = f'{game['period_num'] - 3}{game['period_type']}'
            self.draw['full'].text((1, -1), per, font=self.FONTS['med'], fill=self.COLOURS['white'])


    def add_final_playing_period_to_image(self, game):
        """ Adds final playing period to the centre image if game ended in OT, xOT, or a SO.

        Args:
            game (dict): Dictionary with all details of a specific game.
        """

        # If game ended in a SO or the first OT, add that to the centre image.
        if game['period_type'] == 'SO' or (game['period_type'] == 'OT' and game['period_num'] == 4): # If the game ended in single OT a SO.
            self.draw['full'].text((4, 8), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])

        # Or if in 2OT or later. Calculate the number of OT periods and add that to the centre image.
        elif game['period_type'] == 'OT':
            self.draw['full'].text((1, 8), str(game['period_num'] - 3), font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['full'].text((8, 8), game['period_type'], font=self.FONTS['med'], fill=self.COLOURS['white'])


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