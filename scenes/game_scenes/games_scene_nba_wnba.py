from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.nba_wnba_data
from utils import data_utils, date_utils, image_utils
from PIL import Image

from utils.font_utils import FONT_3X5, draw_text_3x5, get_text_3x5_width
from utils.format_utils import parse_odds, compact_down_distance
from datetime import datetime as dt
from time import sleep
import os












class NBAWNBAGamesScene(GamesScene):
    """ Game scene for the NBA/WNBA. Contains functionality to pull data from NBA/WNBA API, parse, and build+display specific images based on the result.
    This class extends the general Scene and GameScene classes. An object of this class type is created when the scoreboard is started.
    """

    def __init__(self, league_abrv):
        """ Defines the league as NBA/WNBA. Used to identify the correct files when adding logos to images.
        First runs init from the generic GameScene class.

        Args:
            league_abrv (str): Abbreviation of the league for which to fetch game data (e.g., 'NBA', 'WNBA').
        """
        
        super().__init__()
        self.LEAGUE = league_abrv


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
        if display_yesterday:
            if (hasattr(self, 'data_previous_day') and self.data_previous_day['saved_date'] != dates_to_display[0]) or not hasattr(self, 'data_previous_day'):
                self.data_previous_day = {
                    'saved_date': dates_to_display[0],
                    'games': data.nba_wnba_data.get_games(dates_to_display[0], self.LEAGUE)
                }
        
        # Get current day game data. Save this for future reference.
        current_games = data.nba_wnba_data.get_games(dates_to_display[-1], self.LEAGUE)
        
        # If no games today, look back up to 14 days for the most recent games (except when showing yesterday's rollover)
        if not current_games and not display_yesterday:
            from datetime import timedelta
            for days_back in range(1, 15):
                check_date = dates_to_display[-1] - timedelta(days=days_back)
                recent_games = data.nba_wnba_data.get_games(check_date, self.LEAGUE)
                if recent_games:
                    current_games = recent_games
                    break

        self.data = {
            'games_previous_pull': self.data['games'] if hasattr(self, 'data') else None,
            'games': current_games,
        }

        # If there are games to display from yesterday (and setting is enabled), build and display splash image (if enabled), then images for those games.
        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time']:
            if self.settings['splash']['display_splash']:
                self.display_splash_image(len(self.data_previous_day['games']), date=dates_to_display[0])
            self.display_game_images(self.data_previous_day['games'], date=dates_to_display[0])

        # For the current day's games, note if any goals were scored since the last data pull.
        if self.data['games_previous_pull']: # Only applicable if there's a previous copy to compare to.
            for game in self.data['games']:
                if game['status_code'] != 1: # Not applicable if the game hasn't started yet.
                    # Match games between data pulls.
                    matched_game = next(filter(lambda x: x['game_id'] == game['game_id'], self.data['games_previous_pull']), None)

                    if matched_game and matched_game['status_code'] != 1: # Not applicable if the game hasn't started yet in the previous pull.
                        # Determine if either team scored and set keys accordingly.
                        game['away_team_scored'] = True if game['away_score'] > matched_game['away_score'] else False
                        game['home_team_scored'] = True if game['home_score'] > matched_game['home_score'] else False
                        
                        if game['away_team_scored'] and game['home_team_scored']:
                            game['scoring_team'] = 'both'
                            game['score_difference'] = game['away_score'] - matched_game['away_score']
                        elif game['away_team_scored']:
                            game['scoring_team'] = 'away'
                            game['score_difference'] = game['away_score'] - matched_game['away_score']
                        elif game['home_team_scored']:
                            game['scoring_team'] = 'home'
                            game['score_difference'] = game['home_score'] - matched_game['home_score']
                    
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
                if game['status_code'] == 1:
                    duration = self.settings['game_display_duration']
                    elapsed = 0.0
                    step = 1.0
                    
                    has_odds = bool(game.get('odds_str'))
                    num_modes = 2 if has_odds else 1
                    
                    # First build/transition
                    self.build_game_not_started_image(game, rotation_mode=0)
                    self.transition_image(direction='in', image_already_combined=True)
                    
                    while elapsed < duration:
                        rotation_mode = int(elapsed // 2) % num_modes
                        self.build_game_not_started_image(game, rotation_mode=rotation_mode)
                        matrix.SetImage(self.images['full'])
                        
                        sleep_time = min(step, duration - elapsed)
                        sleep(sleep_time)
                        elapsed += sleep_time
                        
                    self.transition_image(direction='out', image_already_combined=True)

                # If the game is over, build the final score image.
                elif game['status_code'] == 3:
                    self.build_game_complete_image(game)
                    self.transition_image(direction='in', image_already_combined=True)
                    sleep(self.settings['game_display_duration'])
                    self.transition_image(direction='out', image_already_combined=True)

                # Otherwise, the game is in progress. Build the game in progress screen.
                elif game['status_code'] == 2:
                    clock_str = game['period_time_remaining']
                    clock_seconds = None
                    if clock_str and not game['is_halftime']:
                        clock_seconds = self.parse_clock_str(clock_str)
                    
                    self.build_game_in_progress_image(game, clock_seconds_override=clock_seconds, rotation_mode=0, blink_colon=False)
                    self.transition_image(direction='in', image_already_combined=True)

                    if self.settings['score_alerting']['score_coloured'] and self.settings['score_alerting']['score_fade_animation']:
                        if game['scoring_team']:
                            self.fade_score_change(game, clock_seconds=clock_seconds)
                    
                    duration = self.settings['game_display_duration']
                    elapsed = 0.0
                    step = 1.0
                    
                    num_modes = 3 if self.LEAGUE == 'NFL' else 2
                    
                    while elapsed < duration:
                        rotation_mode = int(elapsed // 2) % num_modes
                        blink = (int(elapsed) % 2 == 1)
                        self.build_game_in_progress_image(
                            game,
                            clock_seconds_override=clock_seconds,
                            rotation_mode=rotation_mode,
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


    def get_not_started_banner_text(self, game, rotation_mode):
        from utils.format_utils import parse_odds
        from datetime import datetime as dt

        parsed_odds = parse_odds(game.get('odds_str'))
        if rotation_mode == 1 and parsed_odds:
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

    def draw_complete_extras(self, game, rotation_mode):
        for i in range(7):
            color = self.COLOURS['yellow_bright'] if i < game.get('away_timeouts', 0) else self.COLOURS['grey_dark']
            self.draw['full'].point((0 + i * 2, 28), fill=color)
        for i in range(7):
            color = self.COLOURS['yellow_bright'] if i < game.get('home_timeouts', 0) else self.COLOURS['grey_dark']
            self.draw['full'].point((50 + i * 2, 28), fill=color)

    def get_final_period_str(self, game):
        if game.get('period_num', 4) == 5:
            return "OT"
        elif game.get('period_num', 4) > 5:
            return f"{game['period_num'] - 4}OT"
        return ""

    def build_game_in_progress_image(self, game, score_fade_color=None, clock_seconds_override=None, rotation_mode=0, blink_colon=False, alert_text_override=None):
        """ Builds a unified stadium-style scoreboard image for live NBA/WNBA games in progress.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])

        # 1. ROWS 0..21: TEAM LOGOS (22x22)
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((22, 22))
                self.images['full'].paste(away_logo, (0, 0))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((22, 22))
                self.images['full'].paste(home_logo, (42, 0))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # Possession Accent (Under-Glow on row 21)
        poss = game.get('possession')
        if poss == 'away' or poss == game.get('away_abrv'):
            self.draw['full'].rectangle([(6, 21), (15, 21)], fill=self.COLOURS['yellow_bright'])
        elif poss == 'home' or poss == game.get('home_abrv'):
            self.draw['full'].rectangle([(48, 21), (57, 21)], fill=self.COLOURS['yellow_bright'])

        # Bonus Foul Penalty Visual Indicator (Outer 1px vertical strip, rows 6..15)
        away_f = game.get('away_fouls') if game.get('away_fouls') is not None else 0
        home_f = game.get('home_fouls') if game.get('home_fouls') is not None else 0

        if away_f >= 5 or game.get('away_bonus'):
            self.draw['full'].rectangle([(0, 6), (0, 15)], fill=self.COLOURS['red_bright'])
        if home_f >= 5 or game.get('home_bonus'):
            self.draw['full'].rectangle([(63, 6), (63, 15)], fill=self.COLOURS['red_bright'])

        # Center Info (cols 22..41, rows 0..21): Period & Clock & Info
        clock_str = ""
        period_str = ""
        if game.get('is_halftime'):
            clock_str = "HALF"
        elif clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            sep = " " if blink_colon else ":"
            clock_str = f"{m}{sep}{s:02d}"
        else:
            clock_str = game.get('period_time_remaining', '') if game.get('period_time_remaining') else ""

        if game.get('period_num') == 1: period_str = "1ST"
        elif game.get('period_num') == 2: period_str = "2ND"
        elif game.get('period_num') == 3: period_str = "3RD"
        elif game.get('period_num') == 4: period_str = "4TH"
        elif game.get('period_num') == 5: period_str = "OT"
        elif game.get('period_num', 0) > 5: period_str = f"{game['period_num'] - 4}OT"

        if period_str:
            w_p = get_text_3x5_width(period_str)
            draw_text_3x5(self.draw['full'], 32 - w_p // 2, 1, period_str, self.COLOURS['yellow'])
        if clock_str:
            w_c = get_text_3x5_width(clock_str)
            draw_text_3x5(self.draw['full'], 32 - w_c // 2, 7, clock_str, self.COLOURS['white'])

        info_text = ""
        info_color = self.COLOURS['yellow_bright']
        if alert_text_override:
            info_text = alert_text_override
            info_color = self.COLOURS['yellow_bright']
        elif game.get('away_fouls') is not None or game.get('home_fouls') is not None:
            info_text = f"F {away_f}-{home_f}"
            info_color = self.COLOURS['red_bright'] if (away_f >= 5 or home_f >= 5) else self.COLOURS['yellow_bright']

        if info_text:
            w_i = get_text_3x5_width(info_text)
            draw_text_3x5(self.draw['full'], max(22, min(32 - w_i // 2, 41 - w_i)), 14, info_text, info_color)

        # 2. BOTTOM 10 PIXELS (rows 22..31, cols 0..63): ENLARGED SCORES & TIMEOUTS
        away_score_str = str(game.get('away_score', 0))
        home_score_str = str(game.get('home_score', 0))

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

        # Left Corner Indicator (cols 0..7, rows 30..31): Away timeouts
        for i in range(3):
            if i < game.get('away_timeouts', 0):
                self.draw['full'].rectangle([(i * 3, 30), (i * 3 + 1, 31)], fill=self.COLOURS['yellow_bright'])
            else:
                self.draw['full'].point((i * 3, 31), fill=self.COLOURS['grey_dark'])

        # Right Corner Indicator (cols 56..63, rows 30..31): Home timeouts
        for i in range(3):
            if i < game.get('home_timeouts', 0):
                self.draw['full'].rectangle([(56 + i * 3, 30), (56 + i * 3 + 1, 31)], fill=self.COLOURS['yellow_bright'])
            else:
                self.draw['full'].point((56 + i * 3, 31), fill=self.COLOURS['grey_dark'])






    def fade_score_change(self, game, clock_seconds=None, rotation_mode=0):
        """ Fades score from red to white after a score change and shows dynamic alerts.
        """
        # Determine specific alert play text (e.g. PHX 3-POINTER!)
        alert_text = None
        scoring_team = game.get('scoring_team')
        score_diff = game.get('score_difference', 2)
        
        if scoring_team in ['away', 'home']:
            team_abrv = game['away_abrv'] if scoring_team == 'away' else game['home_abrv']
            if score_diff == 3:
                alert_text = f"{team_abrv} 3-POINTER!"
            elif score_diff == 1:
                alert_text = f"{team_abrv} FREE THROW!"
            else:
                alert_text = f"{team_abrv} BASKET!"
        elif scoring_team == 'both':
            alert_text = "SCORE CHANGE!"

        sleep(0.5)
        for n in range(self.COLOURS['red'][2], self.COLOURS['white'][2]):
            self.build_game_in_progress_image(
                game,
                score_fade_color=(255, n, n),
                clock_seconds_override=clock_seconds,
                rotation_mode=rotation_mode,
                blink_colon=False,
                alert_text_override=alert_text
            )
            matrix.SetImage(self.images['full'])
            sleep(0.015)