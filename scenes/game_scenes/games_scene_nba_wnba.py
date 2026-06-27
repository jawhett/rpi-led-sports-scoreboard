from utils.data_utils import TEAM_COLORS
from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.nba_wnba_data
from utils import data_utils, date_utils, image_utils
from PIL import Image

from datetime import datetime as dt
from time import sleep
import os


def compact_down_distance(text):
    if not text:
        return ""
    text = text.upper()
    text = text.replace("GOAL", "G").replace(" & ", " ")
    return text


def parse_odds(odds_str):
    if not odds_str:
        return None
    try:
        fav_team, spread_val, ou_val = "", "", ""
        if ' O/U ' in odds_str:
            parts = odds_str.split(' O/U ')
            spread_part = parts[0].strip()
            ou_val = parts[1].strip()
        else:
            spread_part = odds_str.strip()
            ou_val = ""
            
        spread_parts = spread_part.split(' ')
        if len(spread_parts) >= 2:
            fav_team = spread_parts[0].strip()
            spread_val = spread_parts[1].strip()
        else:
            for sign in ('-', '+'):
                if sign in spread_part:
                    idx = spread_part.find(sign)
                    fav_team = spread_part[:idx].strip()
                    spread_val = spread_part[idx:].strip()
                    break
            if not fav_team:
                fav_team = spread_part
                spread_val = ""
                
        return {
            'fav_team': fav_team,
            'spread': spread_val,
            'ou': ou_val
        }
    except Exception as e:
        print(f"Error parsing odds {odds_str}: {e}")
    return None


FONT_3X5 = {
    '!': (2, 2, 2, 0, 2),
    '0': (7, 5, 5, 5, 7),
    '1': (2, 6, 2, 2, 7),
    '2': (7, 1, 7, 4, 7),
    '3': (7, 1, 7, 1, 7),
    '4': (5, 5, 7, 1, 1),
    '5': (7, 4, 7, 1, 7),
    '6': (7, 4, 7, 5, 7),
    '7': (7, 1, 1, 1, 1),
    '8': (7, 5, 7, 5, 7),
    '9': (7, 5, 7, 1, 7),
    ':': (0, 2, 0, 2, 0),
    ' ': (0, 0, 0, 0, 0),
    '-': (0, 0, 7, 0, 0),
    '/': (1, 1, 2, 4, 4),
    '.': (0, 0, 0, 0, 2),
    '%': (5, 1, 2, 4, 5),
    '+': (0, 2, 7, 2, 0),
    '|': (2, 2, 2, 2, 2),
    'A': (7, 5, 7, 5, 5),
    'B': (6, 5, 6, 5, 6),
    'C': (7, 4, 4, 4, 7),
    'D': (6, 5, 5, 5, 6),
    'E': (7, 4, 7, 4, 7),
    'F': (7, 4, 6, 4, 4),
    'G': (7, 4, 5, 5, 7),
    'H': (5, 5, 7, 5, 5),
    'I': (7, 2, 2, 2, 7),
    'J': (1, 1, 1, 5, 7),
    'K': (5, 6, 4, 6, 5),
    'L': (4, 4, 4, 4, 7),
    'M': (5, 7, 5, 5, 5),
    'N': (5, 6, 5, 3, 5),
    'O': (7, 5, 5, 5, 7),
    'P': (7, 5, 7, 4, 4),
    'Q': (7, 5, 5, 7, 3),
    'R': (7, 5, 6, 5, 5),
    'S': (7, 4, 7, 1, 7),
    'T': (7, 2, 2, 2, 2),
    'U': (5, 5, 5, 5, 7),
    'V': (5, 5, 5, 5, 2),
    'W': (5, 5, 5, 7, 5),
    'X': (5, 5, 2, 5, 5),
    'Y': (5, 5, 2, 2, 2),
    'Z': (7, 1, 2, 4, 7),
    '@': (5, 7, 5, 1, 7),
    '&': (2, 5, 2, 5, 3),
}


def draw_text_3x5(draw, x, y, text, fill_color):
    curr_x = x
    for char in text.upper():
        if char in FONT_3X5:
            rows = FONT_3X5[char]
            for row_idx, row_val in enumerate(rows):
                for col_idx in range(3):
                    if (row_val >> (2 - col_idx)) & 1:
                        draw.point((curr_x + col_idx, y + row_idx), fill=fill_color)
            curr_x += 4
        else:
            curr_x += 4
    return curr_x


def get_text_3x5_width(text):
    return len(text) * 4 - 1 if text else 0


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


    def build_game_in_progress_image(self, game, score_fade_color=None, clock_seconds_override=None, rotation_mode=0, blink_colon=False, alert_text_override=None):
        """ Builds a stadium-style scoreboard image for games in progress.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1. Draw Away Team Logo (reduced to 12x9 to prevent overlap with status)
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((12, 9))
                x = 1  # Leave 1px padding from the outer edge (where ticks are drawn)
                y = (10 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        # 2. Draw Home Team Logo (reduced to 12x9 to prevent overlap with status)
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((12, 9))
                x = 63 - home_logo.width  # Leave 1px padding from outer edge
                y = (10 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")
 
        # 3. Draw Clock (top center, yellow - y=1)
        clock_str = ""
        period_str = ""
        if game['is_halftime']:
            clock_str = "HALF"
        elif clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            sep = " " if blink_colon else ":"
            clock_str = f"{m}{sep}{s:02d}"
        else:
            clock_str = game['period_time_remaining'] if game['period_time_remaining'] else ""

        if game['period_num'] == 1:
            period_str = "1ST"
        elif game['period_num'] == 2:
            period_str = "2ND"
        elif game['period_num'] == 3:
            period_str = "3RD"
        elif game['period_num'] == 4:
            period_str = "4TH"
        elif game['period_num'] == 5:
            period_str = "OT"
        elif game['period_num'] > 5:
            period_str = f"{game['period_num'] - 4}OT"

        if clock_str:
            status_text = f"{period_str} {clock_str}" if period_str else clock_str
            w = get_text_3x5_width(status_text)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], x, 1, status_text, self.COLOURS['yellow'])

            # Draw clean possession indicator dots right next to status channel
            if self.LEAGUE == 'NFL' and game.get('possession'):
                poss_color = self.COLOURS['red_bright'] if game.get('is_red_zone') else self.COLOURS['yellow_bright']
                if game['possession'] == 'away':
                    self.draw['full'].rectangle([(x - 4, 4), (x - 3, 5)], fill=poss_color)
                elif game['possession'] == 'home':
                    self.draw['full'].rectangle([(x + w + 2, 4), (x + w + 3, 5)], fill=poss_color)

        # 4. Draw Timeouts & Bonus Indicators (row 10)
        if self.LEAGUE == 'NFL':
            for i in range(3):
                color = self.COLOURS['yellow_bright'] if i < game.get('away_timeouts', 0) else self.COLOURS['grey_dark']
                self.draw['full'].point((1 + i * 3, 10), fill=color)
                self.draw['full'].point((2 + i * 3, 10), fill=color)
            for i in range(3):
                color = self.COLOURS['yellow_bright'] if i < game.get('home_timeouts', 0) else self.COLOURS['grey_dark']
                self.draw['full'].point((53 + i * 3, 10), fill=color)
                self.draw['full'].point((54 + i * 3, 10), fill=color)
        else:  # NBA/WNBA
            for i in range(7):
                color = self.COLOURS['yellow_bright'] if i < game.get('away_timeouts', 0) else self.COLOURS['grey_dark']
                self.draw['full'].point((0 + i * 2, 10), fill=color)
            for i in range(7):
                color = self.COLOURS['yellow_bright'] if i < game.get('home_timeouts', 0) else self.COLOURS['grey_dark']
                self.draw['full'].point((50 + i * 2, 10), fill=color)
            
            # NBA Bonus indicators next to timeouts on row 11
            if game.get('away_fouls', 0) >= 5:
                self.draw['full'].rectangle([(15, 10), (17, 10)], fill=self.COLOURS['red_bright'])
            if game.get('home_fouls', 0) >= 5:
                self.draw['full'].rectangle([(46, 10), (48, 10)], fill=self.COLOURS['red_bright'])

        # 5. Draw Scores (row 11..30) - using FONTS['giant_bold'] (10x20)
        away_score = game['away_score']
        w = len(str(away_score)) * 8
        x = 16 - w // 2
        color_away = TEAM_COLORS.get(game['away_abrv'], self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['away', 'both']:
            color_away = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']
        self.draw['full'].text((x, 12), str(away_score), font=self.FONTS['lrg_bold'], fill=color_away)

        home_score = game['home_score']
        w = len(str(home_score)) * 8
        x = 48 - w // 2
        color_home = TEAM_COLORS.get(game['home_abrv'], self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['home', 'both']:
            color_home = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']
        self.draw['full'].text((x, 12), str(home_score), font=self.FONTS['lrg_bold'], fill=color_home)

        # 6. Padded Bottom Banner (row 27..31) for secondary info
        banner_text = ""
        banner_color = self.COLOURS['white']

        if alert_text_override:
            banner_text = alert_text_override
            banner_color = self.COLOURS['yellow_bright']
        elif self.LEAGUE == 'NFL' and game.get('down_distance_text'):
            banner_text = compact_down_distance(game['down_distance_text'])
            banner_color = self.COLOURS['white']
        elif self.LEAGUE in ('NBA', 'WNBA') and (game.get('away_fouls') is not None or game.get('home_fouls') is not None):
            banner_text = f"FOULS {game.get('away_fouls', 0)}-{game.get('home_fouls', 0)}"
            if game.get('away_fouls', 0) >= 5 or game.get('home_fouls', 0) >= 5:
                banner_color = self.COLOURS['red_bright']
            else:
                banner_color = self.COLOURS['yellow_bright']

        if not alert_text_override and rotation_mode == 2 and self.LEAGUE == 'NFL' and game.get('home_win_pct') is not None:
            pct = game['home_win_pct']
            fav_abrv = game['home_abrv'] if pct >= 50 else game['away_abrv']
            fav_pct = int(pct if pct >= 50 else (100 - pct))
            banner_text = f"{fav_abrv} WIN PROB {fav_pct}%"
            banner_color = self.COLOURS['green_bright']

        if banner_text:
            w = get_text_3x5_width(banner_text)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], x, 27, banner_text, banner_color)


    def build_game_not_started_image(self, game, rotation_mode=0):
        """ Builds a stadium-style scoreboard image for scheduled games.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1. Draw Away Team Logo
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((30, 24))
                x = (32 - away_logo.width) // 2
                y = (24 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        # 2. Draw Home Team Logo
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((30, 24))
                x = 32 + (32 - home_logo.width) // 2
                y = (24 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # Bottom banner for odds or start time
        parsed_odds = parse_odds(game.get('odds_str'))
        if rotation_mode == 1 and parsed_odds:
            odds_str = f"{parsed_odds['fav_team']} {parsed_odds['spread']}"
            if parsed_odds['ou']:
                odds_str = f"{odds_str} U{parsed_odds['ou']}"
            w = get_text_3x5_width(odds_str)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], x, 27, odds_str, self.COLOURS['yellow_bright'])
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
            w = get_text_3x5_width(banner_text)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], x, 27, banner_text, self.COLOURS['white'])


    def build_game_complete_image(self, game):
        """ Builds a stadium-style scoreboard image for completed games.
        """
        image_utils.clear_image(self.images['full'], self.draw['full'])
        
        # 1. Draw Away Team Logo (increased size and repositioned)
        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((24, 16))
                x = (32 - away_logo.width) // 2
                y = (15 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {away_logo_path}: {e}")

        # 2. Draw Home Team Logo (increased size and repositioned)
        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 32 + (32 - home_logo.width) // 2
                y = (15 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception as e:
                print(f"Error loading logo {home_logo_path}: {e}")

        # 3. Top Center shows FINAL (moved down to bottom banner area to save top space)
        ot_str = ""
        if game['period_num'] == 5:
            ot_str = "OT"
        elif game['period_num'] > 5:
            ot_str = f"{game['period_num'] - 4}OT"
            
        status_text = f"FINAL/{ot_str}" if ot_str else "FINAL"
        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 27, status_text, self.COLOURS['red_bright'])

        # Highlight winner and dim loser scores
        away_score = game['away_score']
        home_score = game['home_score']
        color_away = self.COLOURS['white'] if away_score >= home_score else self.COLOURS['grey_dark']
        color_home = self.COLOURS['white'] if home_score >= away_score else self.COLOURS['grey_dark']

        # Draw Away Score
        w = len(str(away_score)) * 8
        x = 16 - w // 2
        self.draw['full'].text((x, 15), str(away_score), font=self.FONTS['lrg_bold'], fill=color_away)

        # Draw Home Score
        w = len(str(home_score)) * 8
        x = 48 - w // 2
        self.draw['full'].text((x, 15), str(home_score), font=self.FONTS['lrg_bold'], fill=color_home)


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