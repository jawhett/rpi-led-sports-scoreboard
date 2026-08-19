
import datetime
import json
import os
from data.nba_wnba_data import get_games

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

def test_matching():
    today = datetime.date.today()
    try:
        games_data = get_games(today, 'WNBA')
    except Exception as e:
        print(f"Error fetching live WNBA games: {e}")
        return

    # Create WNBA games list
    games = []
    for g in games_data:
        games.append({
            'away_abrv': g['away_abrv'],
            'home_abrv': g['home_abrv'],
            'odds_str': None
        })
        
    print(f"Loaded {len(games)} live games from WNBA API.")

    # 2. Load cached odds using absolute path
    cache_file = "/home/nba/rpi-led-sports-scoreboard/wnba_odds_cache.json"
    cached_odds = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_odds = json.load(f)
    print("Cached odds read:", cached_odds)

    # 3. Match
    for game in games:
        away_raw = game.get('away_abrv', '')
        home_raw = game.get('home_abrv', '')
        away = normalize_abrv(away_raw)
        home = normalize_abrv(home_raw)
        print(f"Matching game: {away_raw}@{home_raw} -> Normalized: {away}@{home}")
        
        odds = None
        for key, eo in cached_odds.items():
            ea_raw, eh_raw = key.split('@')
            ea = normalize_abrv(ea_raw)
            eh = normalize_abrv(eh_raw)
            match_away = (ea in away or away in ea)
            match_home = (eh in home or home in eh)
            print(f"  Against cache key: {key} (Normalized: {ea}@{eh}) -> Match Away? {match_away}, Match Home? {match_home}")
            if match_away and match_home:
                odds = eo
                break
        if odds:
            game['odds_str'] = odds
            print(f"  SUCCESS: matched odds: {odds}")
        else:
            print("  FAILED to match odds.")

test_matching()
