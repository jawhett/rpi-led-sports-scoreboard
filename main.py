from scenes.game_scenes.games_scene_nhl import NHLGamesScene
from scenes.fav_team_next_game_scenes.fav_team_next_game_scene_nhl import NHLFavTeamNextGameScene
from scenes.standings_scenes.standings_scene_nhl import NHLStandingsScene

from scenes.game_scenes.games_scene_pwhl import PWHLGamesScene
from scenes.fav_team_next_game_scenes.fav_team_next_game_scene_pwhl import PWHLFavTeamNextGameScene
from scenes.standings_scenes.standings_scene_pwhl import PWHLStandingsScene

from scenes.game_scenes.games_scene_nba_wnba import NBAWNBAGamesScene
from scenes.fav_team_next_game_scenes.fav_team_next_game_scene_nba_wnba import NBAWNBAFavTeamNextGameScene
from scenes.standings_scenes.standings_scene_nba_wnba import NBAWNBAStandingsScene

from scenes.game_scenes.games_scene_mlb import MLBGamesScene
from scenes.fav_team_next_game_scenes.fav_team_next_game_scene_mlb import MLBFavTeamNextGameScene
from scenes.standings_scenes.standings_scene_mlb import MLBStandingsScene

from scenes.game_scenes.games_scene_nfl import NFLGamesScene
from scenes.fav_team_next_game_scenes.fav_team_next_game_scene_nfl import NFLFavTeamNextGameScene
from scenes.standings_scenes.standings_scene_nfl import NFLStandingsScene

from setup.matrix_setup import matrix, determine_matrix_brightness
from utils import data_utils

import time
import datetime
import requests
import json
import os

# Cache dict to prevent API spamming
cache = {}
CACHE_DURATION_SECS = 45

def normalize_abrv(abrv):
    mapping = {
        # WNBA
        'LVA': 'LV', 'NYL': 'NY', 'LAS': 'LA', 'WAS': 'WSH', 'PDX': 'POR',
        # NBA
        'GSW': 'GS', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'UTA': 'UTAH',
        # MLB
        'CWS': 'CHW', 'TBR': 'TB', 'KCR': 'KC', 'SFG': 'SF', 'SDP': 'SD',
        'WSN': 'WSH', 'ANA': 'LAA', 'FLA': 'MIA', 'ARI': 'AZ'
    }
    abrv = str(abrv).upper().strip()
    return mapping.get(abrv, abrv)

def inject_espn_odds(games, sport, league):
    try:
        cache_file = f"/home/nba/rpi-led-sports-scoreboard/{league}_odds_cache.json"
        
        cached_odds = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_odds = json.load(f)
            except Exception:
                pass
                
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        
        espn_odds = {}
        for event in data.get('events', []):
            for comp in event.get('competitions', []):
                odds_list = comp.get('odds', [])
                odds_str = ""
                if odds_list:
                    spread_text = odds_list[0].get('details', '')
                    ou = odds_list[0].get('overUnder')
                    if spread_text and ou:
                        odds_str = f"{spread_text} O/U {ou}"
                    elif spread_text:
                        odds_str = spread_text
                
                teams = comp.get('competitors', [])
                if len(teams) == 2:
                    away_team = teams[1].get('team', {}).get('abbreviation', '').upper()
                    home_team = teams[0].get('team', {}).get('abbreviation', '').upper()
                    if away_team and home_team:
                        if odds_str:
                            espn_odds[f"{away_team}@{home_team}"] = odds_str
                            cached_odds[f"{away_team}@{home_team}"] = odds_str
                            
        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_odds, f)
        except Exception:
            pass
            
        all_odds = {**cached_odds, **espn_odds}
                        
        for game in games:
            away = normalize_abrv(game.get('away_abrv', ''))
            home = normalize_abrv(game.get('home_abrv', ''))
            
            odds = None
            for key, eo in all_odds.items():
                ea_raw, eh_raw = key.split('@')
                ea = normalize_abrv(ea_raw)
                eh = normalize_abrv(eh_raw)
                if (ea in away or away in ea) and (eh in home or home in eh):
                    odds = eo
                    break
            if odds:
                game['odds_str'] = odds
    except Exception as e:
        print(f"Error injecting ESPN odds for {league}: {e}")


def get_league_games(league, date):
    cache_key = (league, date)
    now = time.time()
    if cache_key in cache:
        cached_time, cached_games = cache[cache_key]
        if now - cached_time < CACHE_DURATION_SECS:
            return cached_games
    
    games = []
    try:
        if league == 'NBA':
            import data.nba_wnba_data
            games = data.nba_wnba_data.get_games(date, 'NBA')
            inject_espn_odds(games, 'basketball', 'nba')
        elif league == 'WNBA':
            import data.nba_wnba_data
            games = data.nba_wnba_data.get_games(date, 'WNBA')
            inject_espn_odds(games, 'basketball', 'wnba')
        elif league == 'NFL':
            import data.nfl_data
            games = data.nfl_data.get_games(date)
        elif league == 'MLB':
            import data.mlb_data
            games = data.mlb_data.get_games(date)
            inject_espn_odds(games, 'baseball', 'mlb')
        elif league == 'NHL':
            import data.nhl_data
            games = data.nhl_data.get_games(date)
        elif league == 'PWHL':
            import data.pwhl_data
            games = data.pwhl_data.get_games(date)
    except Exception as e:
        print(f"Error fetching data for {league}: {e}")
        games = []
        
    cache[cache_key] = (now, games)
    return games


def is_game_live(game, league):
    if league == 'MLB':
        return game.get('status') in ['Live', 'Delayed']
    elif league == 'PWHL':
        return str(game.get('status')) == '2'
    else:
        return game.get('status_code') == 2


def is_game_live_or_recent(game, league):
    if is_game_live(game, league):
        return True
        
    is_final = False
    if league == 'MLB':
        is_final = game.get('status') == 'Final'
    elif league == 'PWHL':
        is_final = str(game.get('status')) == '3'
    else:
        is_final = game.get('status_code') == 3
        
    if is_final:
        start_time = game.get('start_datetime_local')
        if start_time:
            now = datetime.datetime.now().astimezone()
            elapsed_hours = (now - start_time).total_seconds() / 3600.0
            if 0 < elapsed_hours < 5.0:
                return True
    return False


def run_scoreboard():
    scene_mapping = {
        'nhl_games':                NHLGamesScene(),
        'nhl_fav_team_next_game':   NHLFavTeamNextGameScene(),
        'nhl_standings':            NHLStandingsScene(),

        'pwhl_games':               PWHLGamesScene(),
        'pwhl_fav_team_next_game':  PWHLFavTeamNextGameScene(),
        'pwhl_standings':           PWHLStandingsScene(),

        'nba_games':                NBAWNBAGamesScene('NBA'),
        'nba_fav_team_next_game':   NBAWNBAFavTeamNextGameScene('NBA'),
        'nba_standings':            NBAWNBAStandingsScene('NBA'),

        'wnba_games':               NBAWNBAGamesScene('WNBA'),
        'wnba_fav_team_next_game':  NBAWNBAFavTeamNextGameScene('WNBA'),
        'wnba_standings':           NBAWNBAStandingsScene('WNBA'),

        'mlb_games':                MLBGamesScene(),
        'mlb_fav_team_next_game':   MLBFavTeamNextGameScene(),
        'mlb_standings':            MLBStandingsScene(),

        'nfl_games':                NFLGamesScene(),
        'nfl_fav_team_next_game':   NFLFavTeamNextGameScene(),
        'nfl_standings':            NFLStandingsScene()
    }

    scene_leagues = {
        'nba_games': 'NBA',
        'nfl_games': 'NFL',
        'nhl_games': 'NHL',
        'mlb_games': 'MLB',
        'wnba_games': 'WNBA',
        'pwhl_games': 'PWHL'
    }

    PRIORITY_LEAGUES = ['NBA', 'NFL', 'NHL', 'MLB', 'WNBA', 'PWHL']

    while True:
        config = data_utils.read_yaml('config.yaml')
        scene_order = config.get('scene_order', [])
        favourite_teams = config.get('favourite_teams', {})

        matrix.brightness = determine_matrix_brightness()
        active_leagues = [scene_leagues[scene] for scene in scene_order if scene in scene_leagues]

        today = datetime.datetime.now().date()
        live_fav_games = []
        live_regular_games = {}

        for league in active_leagues:
            games = get_league_games(league, today)
            fav_list = favourite_teams.get(league.lower(), [])
            if fav_list is None:
                fav_list = []
            fav_list = [str(team).upper() for team in fav_list]

            for game in games:
                if is_game_live_or_recent(game, league):
                    is_fav = (game.get('away_abrv', '').upper() in fav_list) or (game.get('home_abrv', '').upper() in fav_list)
                    scene_name = f"{league.lower()}_games"
                    
                    if is_fav:
                        live_fav_games.append((scene_name, game['game_id']))
                    else:
                        if league not in live_regular_games:
                            live_regular_games[league] = []
                        live_regular_games[league].append(game['game_id'])

        for scene_obj in scene_mapping.values():
            if hasattr(scene_obj, 'display_only_games'):
                delattr(scene_obj, 'display_only_games')
            if hasattr(scene_obj, 'display_only_live'):
                delattr(scene_obj, 'display_only_live')

        if live_fav_games:
            print(f"[PRIORITY] Live/Recent Favorite Team Game detected: {live_fav_games}. Locking rotation.")
            for scene_name, game_id in live_fav_games:
                scene_mapping[scene_name].display_only_games = [game_id]
                scene_mapping[scene_name].display_scene()
            continue

        has_live_games = False
        for league in PRIORITY_LEAGUES:
            if league in live_regular_games and live_regular_games[league]:
                scene_name = f"{league.lower()}_games"
                print(f"[PRIORITY] Live/Recent regular games detected in {league}. Adding to cycle.")
                scene_mapping[scene_name].display_only_live = True
                scene_mapping[scene_name].display_scene()
                has_live_games = True

        if has_live_games:
            continue

        print("[PRIORITY] No live/recent games active. Running normal cycle.")
        for scene in scene_order:
            scene_mapping[scene].display_scene()


if __name__ == '__main__':
    run_scoreboard()
