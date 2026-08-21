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
                    has_odds = bool(game.get('odds_str'))
                    
                    if not has_odds:
                        self.build_game_not_started_image(game, rotation_mode=0)
                        self.transition_image(direction='in', image_already_combined=True)
                        sleep(duration)
                        self.transition_image(direction='out', image_already_combined=True)
                    else:
                        elapsed = 0.0
                        step = 2.5
                        self.build_game_not_started_image(game, rotation_mode=0)
                        self.transition_image(direction='in', image_already_combined=True)
                        
                        last_mode = 0
                        while elapsed < duration:
                            rotation_mode = int(elapsed // 2.5) % 3
                            if rotation_mode != last_mode:
                                self.build_game_not_started_image(game, rotation_mode=rotation_mode)
                                matrix.SetImage(self.images['full'])
                                last_mode = rotation_mode
                            
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
                    
                    # Number of carousel modes: Lead/Bonus, Scorer, Win%
                    num_modes = 3
                    if not game.get('leader_text') and game.get('home_win_pct') is None:
                        num_modes = 1
                    
                    while elapsed < duration:
                        rotation_mode = int(elapsed // 2.5) % num_modes
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


    def get_not_started_banner_text(self, game, rotation_mode=0):
        from utils.format_utils import parse_odds
        from utils.font_utils import get_text_3x5_width

        broadcaster = game.get('broadcaster') or game.get('tv')
        odds_raw = game.get('odds_str')
        parsed_odds = parse_odds(odds_raw) if odds_raw else None

        if rotation_mode == 2 and broadcaster:
            return broadcaster.upper()[:6], self.COLOURS['cyan']

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

        if broadcaster:
            return broadcaster.upper()[:6], self.COLOURS['cyan']

        return "", self.COLOURS['white']

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

        # Possession Accent (Under-Glow centered under logos on row 21)
        poss = game.get('possession')
        if poss == 'away' or poss == game.get('away_abrv'):
            self.draw['full'].rectangle([(6, 21), (16, 21)], fill=self.COLOURS['yellow_bright'])
        elif poss == 'home' or poss == game.get('home_abrv'):
            self.draw['full'].rectangle([(47, 21), (57, 21)], fill=self.COLOURS['yellow_bright'])

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
            period_color = self.COLOURS['red_bright'] if "OT" in period_str else self.COLOURS['yellow']
            draw_text_3x5(self.draw['full'], 32 - w_p // 2, 1, period_str, period_color)
        if clock_str:
            w_c = get_text_3x5_width(clock_str)
            draw_text_3x5(self.draw['full'], 32 - w_c // 2, 7, clock_str, self.COLOURS['white'])

        info_text = ""
        info_color = self.COLOURS['yellow_bright']
        if alert_text_override:
            info_text = alert_text_override
            info_color = self.COLOURS['yellow_bright']
        else:
            cards = []
            if game.get('leader_text'):
                ldr = game['leader_text']
                parts = ldr.split(' ')
                if len(parts) == 2:
                    name, pts = parts[0], parts[1]
                    cards.append((name[:5] if len(name) <= 5 else pts, self.COLOURS['yellow_bright']))
                    cards.append((pts, self.COLOURS['yellow_bright']))
                else:
                    cards.append((ldr[:5], self.COLOURS['yellow_bright']))

            if away_f > 0 or home_f > 0:
                f_color = self.COLOURS['red_bright'] if (away_f >= 5 or home_f >= 5) else self.COLOURS['yellow_bright']
                cards.append((f"F {away_f}-{home_f}", f_color))

            if game.get('home_win_pct') is not None:
                pct = game['home_win_pct']
                fav_pct = int(pct if pct >= 50 else (100 - pct))
                cards.append((f"{fav_pct}%", self.COLOURS['green_bright']))

            if cards:
                selected_card = cards[rotation_mode % len(cards)]
                info_text, info_color = selected_card[0], selected_card[1]

        if info_text:
            w_i = get_text_3x5_width(info_text)
            draw_text_3x5(self.draw['full'], max(22, min(32 - w_i // 2, 41 - w_i)), 14, info_text, info_color)

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

        # 2. BOTTOM 10 PIXELS (rows 22..31, cols 0..63): ENLARGED SCORES & TIMEOUTS
        away_score_str = str(game.get('away_score', 0))
        home_score_str = str(game.get('home_score', 0))

        color_away = data_utils.get_team_color(game.get('away_abrv'), self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['away', 'both']:
            color_away = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']

        color_home = data_utils.get_team_color(game.get('home_abrv'), self.COLOURS['white'])
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