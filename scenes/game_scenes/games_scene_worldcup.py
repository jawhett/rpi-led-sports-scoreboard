from .games_scene import GamesScene
from setup.matrix_setup import matrix
import data.worldcup_data
from utils import data_utils, date_utils

from datetime import datetime as dt
from time import sleep


class WorldCupGamesScene(GamesScene):
    """ Game scene for the FIFA World Cup. Contains functionality to pull data from ESPN World Cup API,
    parse, and build+display specific images based on the result.
    This class extends the general Scene and GameScene classes.
    """

    def __init__(self):
        super().__init__()
        self.LEAGUE = 'WORLDCUP'

    def display_scene(self):
        # Refresh config and load to settings key.
        self.settings = data_utils.read_yaml('config.yaml')['scene_settings'][self.LEAGUE.lower()]['games']
        self.alt_logos = data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] if data_utils.read_yaml('config.yaml')['alt_logos'][self.LEAGUE.lower()] else {}

        # Determine which days should be displayed.
        dates_to_display = date_utils.determine_dates_to_display_games(self.settings['rollover']['rollover_start_time_local'], self.settings['rollover']['rollover_end_time_local'])
        display_yesterday = True if len(dates_to_display) == 2 else False

        if display_yesterday:
            if (hasattr(self, 'data_previous_day') and self.data_previous_day['saved_date'] != dates_to_display[0]) or not hasattr(self, 'data_previous_day'):
                self.data_previous_day = {
                    'saved_date': dates_to_display[0],
                    'games': data.worldcup_data.get_games(dates_to_display[0])
                }

        # Get current day game data.
        self.data = {
            'games_previous_pull': self.data['games'] if hasattr(self, 'data') else None,
            'games': data.worldcup_data.get_games(dates_to_display[-1]),
        }

        # If there are games to display from yesterday, build and display them.
        if display_yesterday and self.settings['rollover']['show_completed_games_until_rollover_end_time']:
            if self.settings['splash']['display_splash']:
                self.display_splash_image(len(self.data_previous_day['games']), date=dates_to_display[0])
            self.display_game_images(self.data_previous_day['games'], date=dates_to_display[0])

        # Mark any goals scored since last pull.
        if self.data['games_previous_pull']:
            for game in self.data['games']:
                if game['status_code'] != 1:
                    matched_game = next(filter(lambda x: x['game_id'] == game['game_id'], self.data['games_previous_pull']), None)
                    if matched_game and matched_game['status_code'] != 1:
                        prev_goals = len([e for e in matched_game.get('events', []) if e['type'] == 'goal'])
                        curr_goals = len([e for e in game.get('events', []) if e['type'] == 'goal'])
                        
                        if curr_goals > prev_goals:
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
        self.build_splash_image(num_games, date)
        self.transition_image(direction='in', image_already_combined=True)
        sleep(self.settings['splash']['splash_display_duration'])
        self.transition_image(direction='out', image_already_combined=True)

    def display_game_images(self, games, date=None):
        games = self.filter_games(games)
        if games:
            for game in games:
                if game['status_code'] == 1:
                    self.build_game_not_started_image(game)
                    self.transition_image(direction='in')
                elif game['status_code'] == 3:
                    duration = max(12.0, self.settings['game_display_duration'] * 4)
                    elapsed = 0.0
                    step = 1.0
                    match_events = game.get('events', [])
                    num_modes = max(2, len(match_events))
                    
                    self.build_game_complete_image(game, rotation_mode=0)
                    self.transition_image(direction='in')
                    
                    while elapsed < duration:
                        rotation_mode = int(elapsed // 2) % num_modes
                        self.build_game_complete_image(game, rotation_mode=rotation_mode)
                        matrix.SetImage(self.images['full'])
                        
                        sleep_time = min(step, duration - elapsed)
                        sleep(sleep_time)
                        elapsed += sleep_time
                        
                    self.transition_image(direction='out')
                    continue
                elif game['status_code'] == 2:
                    duration = max(12.0, self.settings['game_display_duration'] * 4)
                    elapsed = 0.0
                    step = 1.0
                    match_events = game.get('events', [])
                    num_modes = max(2, len(match_events))
                    
                    self.build_game_in_progress_image(game, rotation_mode=0)
                    self.transition_image(direction='in')
                    
                    while elapsed < duration:
                        rotation_mode = int(elapsed // 2) % num_modes
                        self.build_game_in_progress_image(game, rotation_mode=rotation_mode)
                        matrix.SetImage(self.images['full'])
                        
                        sleep_time = min(step, duration - elapsed)
                        sleep(sleep_time)
                        elapsed += sleep_time
                        
                    self.transition_image(direction='out')
                    continue
                else:
                    print(f"Unexpected game status code encountered: {game['status_code']}.")

                if self.settings['score_alerting']['score_coloured'] and self.settings['score_alerting']['score_fade_animation']:
                    if game['scoring_team']:
                        self.fade_score_change(game)
                
                sleep(self.settings['game_display_duration'])
                self.transition_image(direction='out')
        
        elif not self.settings['splash']['display_splash']:
            self.build_no_games_image(date)
            self.transition_image(direction='in', image_already_combined=True)
            sleep(self.settings['game_display_duration'])
            self.transition_image(direction='out', image_already_combined=True)

    def build_game_not_started_image(self, game, rotation_mode=0):
        from utils import image_utils
        from PIL import Image
        import os
        from test_layout import get_text_3x5_width, draw_text_3x5

        image_utils.clear_image(self.images['full'], self.draw['full'])

        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((24, 16))
                x = (32 - away_logo.width) // 2
                y = (18 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception:
                pass

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((24, 16))
                x = 32 + (32 - home_logo.width) // 2
                y = (18 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception:
                pass

        w = len(game['away_abrv']) * 5
        x = 16 - w // 2
        self.draw['full'].text((x, 18), game['away_abrv'], font=self.FONTS['sm_bold'], fill=self.COLOURS['white'])

        w = len(game['home_abrv']) * 5
        x = 48 - w // 2
        self.draw['full'].text((x, 18), game['home_abrv'], font=self.FONTS['sm_bold'], fill=self.COLOURS['white'])

        # Alternate between Date/Time and the tournament stage at the bottom
        if rotation_mode % 2 == 1 and game.get('stage'):
            time_str = f"STAGE {game['stage']}"
        else:
            time_str = game['start_datetime_local'].strftime('%-I:%M%p').replace('AM', 'A').replace('PM', 'P')
            date_str = game['start_datetime_local'].strftime('%-m/%-d')
            time_str = f"{date_str} {time_str}"

        w = get_text_3x5_width(time_str)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 27, time_str, self.COLOURS['white'])

    def build_game_in_progress_image(self, game, score_fade_color=None, clock_seconds_override=None, rotation_mode=0, blink_colon=False, alert_text_override=None):
        from utils import image_utils
        from PIL import Image
        import os
        from utils.data_utils import TEAM_COLORS
        from test_layout import get_text_3x5_width, draw_text_3x5

        image_utils.clear_image(self.images['full'], self.draw['full'])

        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((12, 9))
                x = 1
                y = (10 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception:
                pass

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((12, 9))
                x = 63 - home_logo.width
                y = (10 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception:
                pass

        # Alternate the top display to avoid crowding
        if rotation_mode % 2 == 1 and game.get('stage'):
            status_text = f"STAGE {game['stage']}"
        else:
            clock_str = game.get('period_time_remaining', '')
            period_str = ""
            if game.get('period_num') == 1:
                period_str = "1H"
            elif game.get('period_num') == 2:
                period_str = "2H"
            elif game.get('period_num') > 2:
                period_str = "OT"
            status_text = f"{period_str} {clock_str}".strip()

        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 1, status_text, self.COLOURS['yellow'])

        away_score = game['away_score']
        w = len(str(away_score)) * 8
        x = 16 - w // 2
        color_away = TEAM_COLORS.get(game['away_abrv'], self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['away', 'both']:
            color_away = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('away_team_scored'):
            color_away = self.COLOURS['red_bright']
        self.draw['full'].text((x, 10), str(away_score), font=self.FONTS['lrg_bold'], fill=color_away)

        home_score = game['home_score']
        w = len(str(home_score)) * 8
        x = 48 - w // 2
        color_home = TEAM_COLORS.get(game['home_abrv'], self.COLOURS['white'])
        if score_fade_color and game.get('scoring_team') in ['home', 'both']:
            color_home = score_fade_color
        elif self.settings['score_alerting']['score_coloured'] and game.get('home_team_scored'):
            color_home = self.COLOURS['red_bright']
        self.draw['full'].text((x, 10), str(home_score), font=self.FONTS['lrg_bold'], fill=color_home)

        # Cycle events (goals/red cards) at the bottom
        match_events = game.get('events', [])
        if match_events:
            idx = rotation_mode % len(match_events)
            ev = match_events[idx]
            team_abrv = game['away_abrv'] if ev['team'] == 'away' else game['home_abrv']
            
            if ev['type'] == 'goal':
                event_text = f"{team_abrv}: {ev['name']} {ev['clock']}"
                color = self.COLOURS['white']
            else:
                event_text = f"RC-{team_abrv}: {ev['name']} {ev['clock']}"
                color = self.COLOURS['red_bright']
                
            w = get_text_3x5_width(event_text)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], max(0, x), 27, event_text, color)

    def build_game_complete_image(self, game, rotation_mode=0):
        from utils import image_utils
        from PIL import Image
        import os
        from utils.data_utils import TEAM_COLORS
        from test_layout import get_text_3x5_width, draw_text_3x5

        image_utils.clear_image(self.images['full'], self.draw['full'])

        away_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["away_abrv"]}.png' if game["away_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["away_abrv"]}_{self.alt_logos[game["away_abrv"]]}.png'
        if os.path.exists(away_logo_path):
            try:
                away_logo = Image.open(away_logo_path)
                away_logo = image_utils.crop_image(away_logo)
                away_logo.thumbnail((12, 9))
                x = 1
                y = (10 - away_logo.height) // 2
                self.images['full'].paste(away_logo, (x, max(0, y)))
            except Exception:
                pass

        home_logo_path = f'assets/images/{self.LEAGUE}/teams/{game["home_abrv"]}.png' if game["home_abrv"] not in self.alt_logos else f'assets/images/{self.LEAGUE}/teams_alt/{game["home_abrv"]}_{self.alt_logos[game["home_abrv"]]}.png'
        if os.path.exists(home_logo_path):
            try:
                home_logo = Image.open(home_logo_path)
                home_logo = image_utils.crop_image(home_logo)
                home_logo.thumbnail((12, 9))
                x = 63 - home_logo.width
                y = (10 - home_logo.height) // 2
                self.images['full'].paste(home_logo, (x, max(0, y)))
            except Exception:
                pass

        # Alternate the top display to avoid crowding
        if rotation_mode % 2 == 1 and game.get('stage'):
            status_text = f"STAGE {game['stage']}"
        else:
            status_text = game.get('status', 'FINAL')
            if game.get('away_shootout') is not None and game.get('home_shootout') is not None:
                status_text = f"PEN {game['away_shootout']}-{game['home_shootout']}"
            
        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(self.draw['full'], x, 1, status_text, self.COLOURS['red_bright'])

        away_score = game['away_score']
        w = len(str(away_score)) * 8
        x = 16 - w // 2
        color_away = TEAM_COLORS.get(game['away_abrv'], self.COLOURS['white'])
        if game['away_score'] < game['home_score']:
            color_away = (color_away[0] // 3, color_away[1] // 3, color_away[2] // 3)
        self.draw['full'].text((x, 10), str(away_score), font=self.FONTS['lrg_bold'], fill=color_away)

        home_score = game['home_score']
        w = len(str(home_score)) * 8
        x = 48 - w // 2
        color_home = TEAM_COLORS.get(game['home_abrv'], self.COLOURS['white'])
        if game['home_score'] < game['away_score']:
            color_home = (color_home[0] // 3, color_home[1] // 3, color_home[2] // 3)
        self.draw['full'].text((x, 10), str(home_score), font=self.FONTS['lrg_bold'], fill=color_home)

        # Cycle events (goals/red cards) at the bottom
        match_events = game.get('events', [])
        if match_events:
            idx = rotation_mode % len(match_events)
            ev = match_events[idx]
            team_abrv = game['away_abrv'] if ev['team'] == 'away' else game['home_abrv']
            
            if ev['type'] == 'goal':
                event_text = f"{team_abrv}: {ev['name']} {ev['clock']}"
                color = self.COLOURS['white']
            else:
                event_text = f"RC-{team_abrv}: {ev['name']} {ev['clock']}"
                color = self.COLOURS['red_bright']
                
            w = get_text_3x5_width(event_text)
            x = 32 - w // 2
            draw_text_3x5(self.draw['full'], max(0, x), 27, event_text, color)
