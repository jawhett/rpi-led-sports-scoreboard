from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.pwhl_data
from utils import data_utils, date_utils

from datetime import datetime as dt
from time import sleep


from utils.font_utils import draw_text_3x5, get_text_3x5_width
from utils.format_utils import parse_odds
import os
from utils import image_utils
from PIL import Image
class PWHLGamesScene(GamesScene):
    """ Game scene for the PWHL. Contains functionality to pull data from PWHL data sources, parse, and build+display specific images based on the result.
    This class extends the general Scene and GameScene classes. An object of this class type is created when the scoreboard is started.
    """

    def __init__(self):
        super().__init__()
        self.LEAGUE = 'PWHL'


    def display_scene(self):
        # Refresh config and load to settings key.
        self.settings = data_utils.read_yaml('config.yaml')['scene_settings'][self.LEAGUE.lower()]['games']
        self.alt_logos = data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] if data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] else {} # Note the teams with an alternative logo per config.yaml.

        # Determine which days should be displayed. Will generate a list with one or two elements. Two means rollover time and yesterday's games should be displayed.
        dates_to_display = date_utils.determine_dates_to_display_games(self.settings['rollover']['rollover_start_time_local'], self.settings['rollover']['rollover_end_time_local'])
        display_yesterday = True if len(dates_to_display) == 2 else False # Will have to display yesterday's games if dates_to_display has 2 elements.

        # If in rollover time, and the data for previous day hasn't been saved / is from a different date than needed, then pull it.
        # This will ensure we don't need to pull the previous day data (that doesn't change) every loop.
        if display_yesterday:
            if (hasattr(self, 'data_previous_day') and self.data_previous_day['saved_date'] != dates_to_display[0]) or not hasattr(self, 'data_previous_day'):
                self.data_previous_day = {
                    'saved_date': dates_to_display[0], # Note the previous date.
                    'games': data.pwhl_data.get_games(dates_to_display[0]) # Get data for previous date.
                }

        # Get current day game data. Save this for future reference.
        self.data = {
            'games_previous_pull': self.data['games'] if hasattr(self, 'data') else None, # If this is the first time this is run, we'd expect self.data to not exist.
            'games': data.pwhl_data.get_games(dates_to_display[-1]), # Get data for current day. Current day will always be the last element of dates_to_display.
        }

        # If there are games to display from yesterday (and setting is enabled), build and display splash image (if enabled), then images for those games.
        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time']:
            if self.settings['splash']['display_splash']:
                self.display_splash_image(len(self.data_previous_day['games']), date=dates_to_display[0])
            self.display_game_images(self.data_previous_day['games'], date=dates_to_display[0])

        # For the current day's games, note if any goals were scored since the last data pull.
        if self.data['games_previous_pull']: # Only applicable if there's a previous copy to compare to.
            for game in self.data['games']:
                if game['status'] != 1: # Not applicable if the game hasn't started yet.
                    # Match games between data pulls.
                    matched_game = next(filter(lambda x: x['game_id'] == game['game_id'], self.data['games_previous_pull']))

                    if matched_game['status']  != 1: # Not applicable if the game hasn't started yet in the previous pull.
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
                if game['status'] in ['1']:
                    self.build_game_not_started_image(game)

                # If the game is over, build the final score image.
                elif game['status'] in ['3','4']:
                    self.build_game_complete_image(game)

                # Otherwise, the game is in progress. Build the game in progress screen.
                elif game['status'] in ['2']:
                    self.build_game_in_progress_image(game)
                else:
                    print(f"Unexpected gameState encountered from API: {game['status']}.")

                # Transition the image in on the matrix.
                self.transition_image(direction='in')

                # If a goal was scored, do goal fade animation (if enabled).
                if self.settings['score_alerting']['score_coloured'] and self.settings['score_alerting']['score_fade_animation']:
                    if game['scoring_team']:
                        self.fade_score_change(game)
                
                # Hold image for calculated duration and transition out.
                sleep(self.settings['game_display_duration'])
                self.transition_image(direction='out')
        
        # If there's no games to display, and splash is disabled, build and display the no games image.
        elif not self.settings['splash']['display_splash']:
            self.build_no_games_image(date)
            self.transition_image(direction='in', image_already_combined=True)
            sleep(self.settings['game_display_duration'])
            self.transition_image(direction='out', image_already_combined=True)


    def add_playing_period_to_image(self, game):
        """ Adds current playing period to the centre image.
        This exists within the specific league class due to huge differences in playing periods between sports (periods, quarters, innings, etc.).

        Args:
            game (dict): Dictionary with all details of a specific game.
        """

        # If intermission, add "INT" to the image.
        if game.get('is_intermission'):
            self.draw['centre'].text((1, 7), 'INT', font=self.FONTS['med'], fill=self.COLOURS['white'])

        # If the first period, add "1st" to the image.
        if game.get('period_num') == 1:
            self.draw['centre'].text((4, -1), '1', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((8, -1), 's', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((12, -1), 't', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the second period, add "2nd" to the image.
        elif game.get('period_num') == 2:
            self.draw['centre'].text((3, -1), '2', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((9, -1), 'n', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If the third period, add "3rd" to the image.
        elif game.get('period_num') == 3:
            self.draw['centre'].text((3, -1), '3', font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((9, -1), 'r', font=self.FONTS['sm'], fill=self.COLOURS['white'])
            self.draw['centre'].text((13, -1), 'd', font=self.FONTS['sm'], fill=self.COLOURS['white'])

        # If game ended in a SO, add that to the centre image.
        if game.get('period_type') == 'SO':
            self.draw['centre'].text((4, -1), 'SO', font=self.FONTS['med'], fill=self.COLOURS['white'])

        # API returns all OT w/ a number, so need to process that.
        if game.get('period_type') == 'OT1':
            self.draw['centre'].text((4, -1), 'OT', font=self.FONTS['med'], fill=self.COLOURS['white'])
        # If in 2OT or later. Calculate the number of OT periods and add that to the centre image.
        elif 'OT' in game.get('period_type'):
            self.draw['centre'].text((1, -1), str(game.get('period_num') - 3), font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((8, -1), 'OT', font=self.FONTS['med'], fill=self.COLOURS['white'])


    def add_final_playing_period_to_image(self, game):
        """ Adds final playing period to the centre image if game ended in OT, xOT, or a SO.

        Args:
            game (dict): Dictionary with all details of a specific game.
        """

        # If game ended in a SO, add that to the centre image.
        if game.get('period_type') == 'SO':
            self.draw['centre'].text((4, 8), 'SO', font=self.FONTS['med'], fill=self.COLOURS['white'])

        # API returns all OT w/ a number, so need to process that.
        if game.get('period_type') == 'OT1':
            self.draw['centre'].text((4, 8), 'OT', font=self.FONTS['med'], fill=self.COLOURS['white'])
        # If in 2OT or later. Calculate the number of OT periods and add that to the centre image.
        elif 'OT' in game.get('period_type'):
            self.draw['centre'].text((1, 8), str(game.get('period_num') - 3), font=self.FONTS['med'], fill=self.COLOURS['white'])
            self.draw['centre'].text((8, 8), 'OT', font=self.FONTS['med'], fill=self.COLOURS['white'])


    def should_display_time_remaining_in_playing_period(self, game):
        """ Determines if the time remaining in the playing period should be added to the centre image.

        Args:
            game (dict): Dictionary with all details of a specific game.

        Returns:
            Bool: f the time remaining in the playing period should be added to the centre image (True) or not (False).
        """

        if not game.get('is_intermission') and game.get('period_type') != 'SO':
            return True
        else:
            return False

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
                away_logo.thumbnail((24, 16))
                x = (32 - away_logo.width) // 2
                y = (18 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, y))
            except Exception as e:
                pass

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 32 + (32 - home_logo.width) // 2
                y = (18 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, y))
            except Exception as e:
                pass

        # Always show team abbreviations at the bottom (y=20)
        w = len(game['away_abrv']) * 6
        x = 16 - w // 2
        self.draw['full'].text((x, 20), game['away_abrv'], font=self.FONTS['med_bold'], fill=self.COLOURS['white'])

        w = len(game['home_abrv']) * 6
        x = 48 - w // 2
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

        time_str = game['start_datetime_local'].time().strftime('%I:%M %p')
        if time_str.startswith('0'):
            time_str = time_str[1:]

        banner_text = f"{date_str} {time_str}"
        w = get_text_3x5_width(banner_text)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 27, banner_text, self.COLOURS['white'])

    def build_game_in_progress_image(self, game):
        """ Builds a stadium-style scoreboard image for games in progress.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])

        # 1. Draw Away Team Logo
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((24, 16))
                x = (32 - away_logo.width) // 2
                y = (15 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, y))
            except Exception as e:
                pass

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 32 + (32 - home_logo.width) // 2
                y = (15 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, y))
            except Exception as e:
                pass

        # 3. Draw Clock (top center, yellow - y=0)
        clock_str = ""
        if game.get('is_intermission'):
            clock_str = "INT"
        else:
            clock_str = game.get('period_time_remaining', '')

        # Period string
        period_str = ""
        if game.get('period_num') == 1:
            period_str = "1ST"
        elif game.get('period_num') == 2:
            period_str = "2ND"
        elif game.get('period_num') == 3:
            period_str = "3RD"
        elif game.get('period_type') == 'SO':
            period_str = "SO"
        elif game.get('period_type') == 'OT1':
            period_str = "OT"
        elif 'OT' in game.get('period_type', ''):
            period_str = f"{game.get('period_num', 4) - 3}OT"

        status_text = f"{period_str} {clock_str}" if clock_str else period_str
        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 0, status_text, self.COLOURS['yellow'])

        # Draw Scores
        away_score = game['away_score']
        home_score = game['home_score']

        color_away = self.COLOURS['white']
        color_home = self.COLOURS['white']
        if self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']
        if self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']

        # Determine if we should offset scores down (same as NHL logic)
        y_offset = 20 if len(str(away_score)) <= 1 and len(str(home_score)) <= 1 else 18
        away_font = self.FONTS['giant_bold'] if len(str(away_score)) <= 1 else self.FONTS['lrg_bold']
        home_font = self.FONTS['giant_bold'] if len(str(home_score)) <= 1 else self.FONTS['lrg_bold']

        w = len(str(away_score)) * (10 if len(str(away_score)) <= 1 else 8)
        x = 16 - w // 2
        self.draw['full'].text((x, y_offset), str(away_score), font=away_font, fill=color_away)

        w = len(str(home_score)) * (10 if len(str(home_score)) <= 1 else 8)
        x = 48 - w // 2
        self.draw['full'].text((x, y_offset), str(home_score), font=home_font, fill=color_home)

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
                away_logo.thumbnail((24, 16))
                x = (32 - away_logo.width) // 2
                y = (15 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, y))
            except Exception as e:
                pass

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 32 + (32 - home_logo.width) // 2
                y = (15 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, y))
            except Exception as e:
                pass

        # 3. Center top shows FINAL (y=0)
        final_str = "FINAL"
        w = len(final_str) * 6
        x = 32 - w // 2
        self.draw['full'].text((x, 0), final_str, font=self.FONTS['med_bold'], fill=self.COLOURS['red_bright'])

        # 4. Center bottom shows OT/SO details if applicable (y=20, using med_bold)
        ot_str = ""
        if game.get('period_type') == 'SO':
            ot_str = "SO"
        elif game.get('period_type') == 'OT1':
            ot_str = "OT"
        elif 'OT' in game.get('period_type', ''):
            ot_str = f"{game.get('period_num', 4) - 3}OT"

        if ot_str:
            w = len(ot_str) * 6
            x = 32 - w // 2
            self.draw['full'].text((x, 20), ot_str, font=self.FONTS['med_bold'], fill=self.COLOURS['white'])

        # Highlight winner and dim loser scores
        away_score = game['away_score']
        home_score = game['home_score']
        color_away = self.COLOURS['white'] if away_score >= home_score else self.COLOURS['grey_dark']
        color_home = self.COLOURS['white'] if home_score >= away_score else self.COLOURS['grey_dark']

        # Determine if we should offset scores down (same as NHL logic)
        y_offset = 20 if len(str(away_score)) <= 1 and len(str(home_score)) <= 1 else 18
        away_font = self.FONTS['giant_bold'] if len(str(away_score)) <= 1 else self.FONTS['lrg_bold']
        home_font = self.FONTS['giant_bold'] if len(str(home_score)) <= 1 else self.FONTS['lrg_bold']

        w = len(str(away_score)) * (10 if len(str(away_score)) <= 1 else 8)
        x = 16 - w // 2
        self.draw['full'].text((x, y_offset), str(away_score), font=away_font, fill=color_away)

        w = len(str(home_score)) * (10 if len(str(home_score)) <= 1 else 8)
        x = 48 - w // 2
        self.draw['full'].text((x, y_offset), str(home_score), font=home_font, fill=color_home)
