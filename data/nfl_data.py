from setup.session_setup import session
from datetime import datetime as dt
from datetime import timezone as tz

# Headers for ESPN API
espn_headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'application/json, text/plain, */*',
}

TEAM_TO_DIVISION = {
    'ARI': ('NFC West', 'West', 'NFC'),
    'ATL': ('NFC South', 'South', 'NFC'),
    'BAL': ('AFC North', 'North', 'AFC'),
    'BUF': ('AFC East', 'East', 'AFC'),
    'CAR': ('NFC South', 'South', 'NFC'),
    'CHI': ('NFC North', 'North', 'NFC'),
    'CIN': ('AFC North', 'North', 'AFC'),
    'CLE': ('AFC North', 'North', 'AFC'),
    'DAL': ('NFC East', 'East', 'NFC'),
    'DEN': ('AFC West', 'West', 'AFC'),
    'DET': ('NFC North', 'North', 'NFC'),
    'GB': ('NFC North', 'North', 'NFC'),
    'HOU': ('AFC South', 'South', 'AFC'),
    'IND': ('AFC South', 'South', 'AFC'),
    'JAX': ('AFC South', 'South', 'AFC'),
    'KC': ('AFC West', 'West', 'AFC'),
    'LV': ('AFC West', 'West', 'AFC'),
    'LAC': ('AFC West', 'West', 'AFC'),
    'LAR': ('NFC West', 'West', 'NFC'),
    'MIA': ('AFC East', 'East', 'AFC'),
    'MIN': ('NFC North', 'North', 'NFC'),
    'NE': ('AFC East', 'East', 'AFC'),
    'NO': ('NFC South', 'South', 'NFC'),
    'NYG': ('NFC East', 'East', 'NFC'),
    'NYJ': ('AFC East', 'East', 'AFC'),
    'PHI': ('NFC East', 'East', 'NFC'),
    'PIT': ('AFC North', 'North', 'AFC'),
    'SF': ('NFC West', 'West', 'NFC'),
    'SEA': ('NFC West', 'West', 'NFC'),
    'TB': ('NFC South', 'South', 'NFC'),
    'TEN': ('AFC South', 'South', 'AFC'),
    'WSH': ('NFC East', 'East', 'NFC'),
}

def get_games(date):
    try:
        games = []
        # ESPN expects YYYYMMDD
        date_str = date.strftime('%Y%m%d')
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_str}'
        try:
            response = session.get(url, headers=espn_headers, timeout=10)
            data_json = response.json()

            # Fallback to the active week of games if no events are scheduled for this specific date
            if not data_json.get('events'):
                fallback_url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
                response = session.get(fallback_url, headers=espn_headers, timeout=10)
                data_json = response.json()
            
            if 'events' in data_json:
                for event in data_json['events']:
                    comp = event['competitions'][0]
                    status_obj = comp['status']
                    status_name = status_obj['type']['name']
                    status_state = status_obj['type']['state']
                
                    # Mapping state: pre -> 1, in -> 2, post -> 3
                    if status_state == 'pre':
                        status_code = 1
                    elif status_state == 'in':
                        status_code = 2
                    else:
                        status_code = 3
                
                    # Parse datetime
                    try:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=tz.utc)
                    except ValueError:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                
                    start_time_local = start_time_utc.astimezone(tz=None)
                
                    home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                    away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')
                
                    home_abrv = home_team['team']['abbreviation']
                    away_abrv = away_team['team']['abbreviation']
                
                    home_score = int(home_team['score']) if home_team.get('score') is not None else 0
                    away_score = int(away_team['score']) if away_team.get('score') is not None else 0
                
                    # Status text
                    if status_code == 1:
                        status_text = 'Scheduled'
                    elif status_name == 'STATUS_HALFTIME':
                        status_text = 'Halftime'
                    else:
                        status_text = status_obj['type']['detail']
                
                    period_num = status_obj.get('period', 0)
                    is_halftime = (status_name == 'STATUS_HALFTIME')
                
                    # Timeouts
                    home_timeouts = home_team.get('timeouts', 3)
                    away_timeouts = away_team.get('timeouts', 3)

                    # Possession and Down/Distance
                    possession = None
                    down_distance_text = ""
                    home_win_pct = None
                    is_red_zone = False
                
                    if 'situation' in comp:
                        sit = comp['situation']
                        is_red_zone = sit.get('isRedZone', False)
                        poss_id = sit.get('possession')
                        if poss_id:
                            if str(poss_id) == str(home_team['team']['id']):
                                possession = 'home'
                            elif str(poss_id) == str(away_team['team']['id']):
                                possession = 'away'
                    
                        down = sit.get('down')
                        distance = sit.get('distance')
                        if down and distance:
                            suffixes = {1: 'ST', 2: 'ND', 3: 'RD', 4: 'TH'}
                            down_distance_text = f"{down}{suffixes.get(down, 'TH')} & {distance}"
                        
                        # Win probability
                        prob = sit.get('lastPlay', {}).get('probability', {})
                        if prob and 'homeWinPercentage' in prob:
                            home_win_pct = float(prob['homeWinPercentage']) * 100

                    # Odds
                    odds_str = ""
                    odds_list = comp.get('odds', [])
                    if odds_list:
                        spread_text = odds_list[0].get('details', '')
                        ou = odds_list[0].get('overUnder')
                        if spread_text and ou:
                            odds_str = f"{spread_text} O/U {ou}"
                        elif spread_text:
                            odds_str = spread_text

                    # Check for OT
                    period_type = 'OT' if period_num > 4 else 'Std'
                
                    games.append({
                        'game_id': event['id'],
                        'home_abrv': home_abrv,
                        'away_abrv': away_abrv,
                        'home_score': home_score,
                        'away_score': away_score,
                        'start_datetime_utc': start_time_utc,
                        'start_datetime_local': start_time_local,
                        'status': status_text,
                        'status_code': status_code,
                        'has_started': True if status_code > 1 else False,
                        'period_num': period_num,
                        'period_type': period_type,
                        'period_time_remaining': status_obj.get('displayClock'),
                        'is_halftime': is_halftime,
                        'home_timeouts': home_timeouts,
                        'away_timeouts': away_timeouts,
                        'possession': possession,
                        'is_red_zone': is_red_zone,
                        'down_distance_text': down_distance_text,
                        'home_win_pct': home_win_pct,
                        'odds_str': odds_str,
                        'home_team_scored': False,
                        'away_team_scored': False,
                        'scoring_team': None
                    })
        except Exception as e:
            print(f"Error fetching NFL games: {e}")
        return games

    except Exception as e:
        print(f'Error in get_games: {e}')
        return []
def get_next_game(team):
    cur_datetime = dt.today().astimezone()
    cur_date = cur_datetime.date()
    url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team.lower()}/schedule'
    try:
        response = session.get(url, headers=espn_headers, timeout=10)
        data = response.json()
        if 'events' in data:
            # Find next non-post game
            for event in data['events']:
                comp = event['competitions'][0]
                status_state = comp['status']['type']['state']
                if status_state != 'post':
                    # This is our next game
                    try:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=tz.utc)
                    except ValueError:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                    
                    start_time_local = start_time_utc.astimezone(tz=None)
                    
                    home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                    away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')
                    
                    home_abrv = home_team['team']['abbreviation']
                    away_abrv = away_team['team']['abbreviation']
                    
                    return {
                        'home_or_away': 'away' if home_abrv != team.upper() else 'home',
                        'opponent_abrv': home_abrv if home_abrv != team.upper() else away_abrv,
                        'start_datetime_utc': start_time_utc,
                        'start_datetime_local': start_time_local,
                        'is_today': True if start_time_local.date() == cur_date or start_time_local < cur_datetime else False,
                        'has_started': True if status_state == 'in' else False
                    }
            
            # Fallback: Find the last completed game
            for event in reversed(data['events']):
                comp = event['competitions'][0]
                status_state = comp['status']['type']['state']
                if status_state == 'post':
                    home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                    away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')
                    
                    home_abrv = home_team['team']['abbreviation']
                    away_abrv = away_team['team']['abbreviation']
                    
                    home_score = int(home_team.get('score', 0))
                    away_score = int(away_team.get('score', 0))
                    
                    is_home = home_abrv == team.upper()
                    fav_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    is_win = fav_score > opp_score
                    
                    try:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=tz.utc)
                    except ValueError:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                        
                    return {
                        'home_or_away': 'home' if is_home else 'away',
                        'opponent_abrv': away_abrv if is_home else home_abrv,
                        'start_datetime_utc': start_time_utc,
                        'start_datetime_local': start_time_utc.astimezone(tz=None),
                        'is_today': False,
                        'has_started': True,
                        'is_completed': True,
                        'is_win': is_win,
                        'score_str': f"{fav_score}-{opp_score}"
                    }
    except Exception as e:
        print(f"Error fetching NFL next game: {e}")
    return None

def get_standings():
    try:
        url = 'https://site.api.espn.com/apis/v2/sports/football/nfl/standings'
        standings = {
            'retrieved_on': dt.now().astimezone(),
            'conference': {
                conf: {
                    'subdivision_abrv': conf,
                    'rank_method': 'Win Percentage',
                    'playoff_cutoff_hard': 7,
                    'playoff_cutoff_soft': 4,
                    'team_standings': []
                } for conf in ['AFC', 'NFC']
            },
            'division': {
                div: {
                    'subdivision_abrv': div_abrv,
                    'rank_method': 'Win Percentage',
                    'team_standings': []
                } for div, div_abrv in [
                    ('AFC East', 'AFCE'), ('AFC North', 'AFCN'), ('AFC South', 'AFCS'), ('AFC West', 'AFCW'),
                    ('NFC East', 'NFCE'), ('NFC North', 'NFCN'), ('NFC South', 'NFCS'), ('NFC West', 'NFCW')
                ]
            }
        }
        try:
            response = session.get(url, headers=espn_headers, timeout=10)
            data = response.json()
            if 'children' in data:
                for conf_child in data['children']:
                    conf_name = conf_child['name']
                    conf_abrv = 'AFC' if 'American' in conf_name else 'NFC'
                
                    if 'standings' in conf_child and 'entries' in conf_child['standings']:
                        for entry in conf_child['standings']['entries']:
                            team_abrv = entry['team']['abbreviation']
                        
                            # Find stats
                            stats_dict = {stat.get('name') or stat.get('type'): stat for stat in entry['stats']}
                        
                            wins = int(stats_dict['wins']['value']) if 'wins' in stats_dict else 0
                            losses = int(stats_dict['losses']['value']) if 'losses' in stats_dict else 0
                            win_pct = float(stats_dict['winPercent']['value']) if 'winPercent' in stats_dict else 0.0
                            seed = int(stats_dict['playoffSeed']['value']) if 'playoffSeed' in stats_dict else 16
                        
                            clincher_val = stats_dict.get('clincher', {}).get('displayValue', '')
                            has_clinched = True if clincher_val in ['x', 'y', 'z', '*'] else False
                        
                            # Add to conference
                            standings['conference'][conf_abrv]['team_standings'].append({
                                'team_abrv': team_abrv,
                                'rank': seed,
                                'percent': f'{win_pct:.3f}',
                                'has_clinched': has_clinched
                            })

                            # Add to division
                            div_info = TEAM_TO_DIVISION.get(team_abrv)
                            if div_info:
                                div_name = div_info[0]
                                standings['division'][div_name]['team_standings'].append({
                                    'team_abrv': team_abrv,
                                    'rank': 1, # Will be set during sorting
                                    'percent': f'{win_pct:.3f}',
                                    'wins': wins,
                                    'has_clinched': has_clinched
                                })
                            
            # Sort each division
            for div in standings['division'].values():
                div['team_standings'] = sorted(div['team_standings'], key=lambda x: (-float(x['percent']), -x['wins']))
                for rank, team_standing in enumerate(div['team_standings'], 1):
                    team_standing['rank'] = rank
                    if 'wins' in team_standing:
                        del team_standing['wins']
                    
            # Sort conference standings by rank (seed)
            for conf in standings['conference'].values():
                conf['team_standings'] = sorted(conf['team_standings'], key=lambda x: x['rank'])
            
        except Exception as e:
            print(f"Error fetching NFL standings: {e}")
        return standings

    except Exception as e:
        print(f'Error in get_standings: {e}')
        return {}