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
                self.transition_image(direction='in')

                # If a run was scored, do score fade animation (if enabled).
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





    def get_not_started_banner_text(self, game, rotation_mode):
        from utils.format_utils import parse_odds
        from datetime import datetime as dt

        parsed_odds = parse_odds(game.get('odds_str'))
        if parsed_odds:
            odds_str = f"{parsed_odds['fav_team']} {parsed_odds['spread']}"
            if parsed_odds['ou']:
                odds_str = f"{odds_str} U{parsed_odds['ou']}"
            return odds_str, self.COLOURS['yellow_bright']
        else:
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
            return banner_text, self.COLOURS['white']

    def get_final_period_str(self, game):
        if game.get('inning_num', 9) > 9:
            return str(game['inning_num'])
        return ""

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
                x = 1
                y = 0
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception as e:
                pass

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 63 - home_logo.width
                y = 0
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception as e:
                pass

        # 3. Draw Inning Indicator (top center, yellow - y=1)
        self.add_playing_period_to_image(game)

        # 4. Draw Scores
        away_score = game['away_score']
        home_score = game['home_score']

        color_away = self.COLOURS['white']
        color_home = self.COLOURS['white']
        if self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']
        if self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']

        # Determine if we should offset scores down
        y_offset = 16
        away_font = self.FONTS['lrg_bold']
        home_font = self.FONTS['lrg_bold']

        w = len(str(away_score)) * 8
        x = 12 - w // 2
        self.draw['full'].text((x, y_offset), str(away_score), font=away_font, fill=color_away)

        w = len(str(home_score)) * 8
        x = 52 - w // 2
        self.draw['full'].text((x, y_offset), str(home_score), font=home_font, fill=color_home)

        # 5. Draw Outs and Runners
        if self.settings['display_outs_and_bases']:
            self.add_outs_to_image(game)
            self.add_runners_on_base_to_image(game)




    def add_playing_period_to_image(self, game):
        col_offset = 28 if game['inning_num'] <= 9 else 25

        if game['inning_state'] in ['Top', 'Start']:
            self.draw['full'].line(((col_offset, 1), (col_offset, 6)), fill=self.COLOURS['white'])
            self.draw['full'].line(((col_offset, 1), (col_offset-2, 3)), fill=self.COLOURS['white'])
            self.draw['full'].line(((col_offset, 1), (col_offset+2, 3)), fill=self.COLOURS['white'])
        elif game['inning_state'] == 'Bottom':
            self.draw['full'].line(((col_offset, 7), (col_offset, 2)), fill=self.COLOURS['white'])
            self.draw['full'].line(((col_offset, 7), (col_offset-2, 5)), fill=self.COLOURS['white'])
            self.draw['full'].line(((col_offset, 7), (col_offset+2, 5)), fill=self.COLOURS['white'])
        elif game['inning_state'] == 'End':
            self.draw['full'].text((col_offset-1, -1), 'E', font=self.FONTS['sm'], fill=self.COLOURS['white'])
        elif game['inning_state'] == 'Middle':
            self.draw['full'].line(((col_offset-2, 4), (col_offset+2, 4)), fill=self.COLOURS['white'])

        self.draw['full'].text((col_offset+5, -1), str(game['inning_num']), font=self.FONTS['sm'], fill=self.COLOURS['white'])


    def add_outs_to_image(self, game):
        # We need to shift everything right by 22 since it used to be drawn on center
        x = 22

        # We'll use the same y coordinates as before
        # Draw grey boxes representing potential outs.
        self.draw['full'].rectangle(((2+x, 10), (4+x, 11)), fill=self.COLOURS['grey_light'])
        self.draw['full'].rectangle(((2+x, 13), (4+x, 14)), fill=self.COLOURS['grey_light'])
        self.draw['full'].rectangle(((2+x, 16), (4+x, 17)), fill=self.COLOURS['grey_light'])

        if game['outs'] >= 1:
            self.draw['full'].rectangle(((2+x, 10), (4+x, 11)), fill=self.COLOURS['yellow'])
        if game['outs'] >= 2:
            self.draw['full'].rectangle(((2+x, 13), (4+x, 14)), fill=self.COLOURS['yellow'])
        if game['outs'] == 3:
            self.draw['full'].rectangle(((2+x, 16), (4+x, 17)), fill=self.COLOURS['yellow'])


    def add_runners_on_base_to_image(self, game):
        # We need to shift everything right by 22 since it used to be drawn on center
        x = 22
        
        # 1st base.
        self.draw['full'].line(((15+x, 13), (17+x, 15)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((17+x, 15), (15+x, 17)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((15+x, 17), (13+x, 15)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((13+x, 15), (15+x, 13)), fill=self.COLOURS['grey_light'])
        # 2nd base.
        self.draw['full'].line(((12+x, 10), (14+x, 12)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((14+x, 12), (12+x, 14)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((12+x, 14), (10+x, 12)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((10+x, 12), (12+x, 10)), fill=self.COLOURS['grey_light'])
        # 3rd base.
        self.draw['full'].line(((9+x, 13), (11+x, 15)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((11+x, 15), (9+x, 17)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((9+x, 17), (7+x, 15)), fill=self.COLOURS['grey_light'])
        self.draw['full'].line(((7+x, 15), (9+x, 13)), fill=self.COLOURS['grey_light'])

        if game['runner_on_first']:
            self.draw['full'].line(((15+x, 14), (15+x, 16)), fill=self.COLOURS['yellow'])
            self.draw['full'].line(((14+x, 15), (16+x, 15)), fill=self.COLOURS['yellow'])
        if game['runner_on_second']:
            self.draw['full'].line(((12+x, 11), (12+x, 13)), fill=self.COLOURS['yellow'])
            self.draw['full'].line(((11+x, 12), (13+x, 12)), fill=self.COLOURS['yellow'])
        if game['runner_on_third']:
            self.draw['full'].line(((9+x, 14), (9+x, 16)), fill=self.COLOURS['yellow'])
            self.draw['full'].line(((8+x, 15), (10+x, 15)), fill=self.COLOURS['yellow'])

