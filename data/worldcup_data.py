from setup.session_setup import session
from datetime import datetime as dt
from datetime import timezone as tz
import json
import os
import requests

espn_headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'application/json, text/plain, */*',
}

def get_games(date):
    try:
        games = []
        # ESPN expects YYYYMMDD
        date_str = date.strftime('%Y%m%d')
        url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date_str}'
        response = session.get(url, headers=espn_headers, timeout=10)
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
                    try:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                    except ValueError:
                        start_time_utc = dt.strptime(event['date'], '%Y-%m-%dT%H:%M%z')
                
                start_time_local = start_time_utc.astimezone(tz=None)
                
                home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')
                
                home_abrv = home_team['team']['abbreviation'].upper()
                away_abrv = away_team['team']['abbreviation'].upper()
                
                home_score = int(home_team['score']) if home_team.get('score') is not None else 0
                away_score = int(away_team['score']) if away_team.get('score') is not None else 0
                
                # Shootout scores
                home_shootout = home_team.get('shootoutScore')
                away_shootout = away_team.get('shootoutScore')
                home_shootout = int(home_shootout) if home_shootout is not None else None
                away_shootout = int(away_shootout) if away_shootout is not None else None
                
                # Status text
                if status_code == 1:
                    status_text = 'Scheduled'
                else:
                    status_text = status_obj['type'].get('detail', status_obj['type'].get('description', ''))
                
                period_num = status_obj.get('period', 0)
                
                # Check for ET or Pen Shootout
                period_type = 'Std'
                if 'AET' in status_text or 'PEN' in status_text:
                    period_type = 'OT'
                
                # Parse scorers
                goals = []
                home_id = str(home_team['team']['id'])
                away_id = str(away_team['team']['id'])
                for d in comp.get('details', []):
                    if d.get('scoringPlay') or 'Goal' in d.get('type', {}).get('text', ''):
                        scorer = "Unknown"
                        if d.get('athletesInvolved'):
                            scorer = d['athletesInvolved'][0].get('shortName', 'Unknown')
                        clock = d.get('clock', {}).get('displayValue', '')
                        team_id = str(d.get('team', {}).get('id'))
                        
                        goal_team = None
                        if team_id == home_id:
                            goal_team = 'home'
                        elif team_id == away_id:
                            goal_team = 'away'
                            
                        goals.append({
                            'scorer': scorer,
                            'clock': clock,
                            'team': goal_team
                        })
                
                # Try downloading team logos if they don't exist
                for team_data in [home_team, away_team]:
                    abrv = team_data['team']['abbreviation'].upper()
                    logo_url = team_data['team'].get('logo')
                    if logo_url:
                        # Make sure folder exists
                        os.makedirs('assets/images/WORLDCUP/teams', exist_ok=True)
                        logo_path = f'assets/images/WORLDCUP/teams/{abrv}.png'
                        if not os.path.exists(logo_path):
                            try:
                                img_resp = requests.get(logo_url, timeout=5)
                                if img_resp.status_code == 200:
                                    with open(logo_path, 'wb') as f:
                                        f.write(img_resp.content)
                                    print(f"Downloaded logo for {abrv}")
                            except Exception as e:
                                print(f"Error downloading logo for {abrv}: {e}")
                
                # Try downloading league logo if it doesn't exist
                try:
                    os.makedirs('assets/images/WORLDCUP/league', exist_ok=True)
                    league_logo_path = 'assets/images/WORLDCUP/league/WORLDCUP.png'
                    if not os.path.exists(league_logo_path):
                        leagues_data = data_json.get('leagues', [{}])
                        if leagues_data and leagues_data[0].get('logos'):
                            league_logo_url = leagues_data[0]['logos'][0]['href']
                            img_resp = requests.get(league_logo_url, timeout=5)
                            if img_resp.status_code == 200:
                                with open(league_logo_path, 'wb') as f:
                                    f.write(img_resp.content)
                                print("Downloaded WORLDCUP league logo")
                except Exception as e:
                    print(f"Error downloading league logo: {e}")
                
                games.append({
                    'game_id': event['id'],
                    'home_abrv': home_abrv,
                    'away_abrv': away_abrv,
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_shootout': home_shootout,
                    'away_shootout': away_shootout,
                    'status': status_text,
                    'status_code': status_code,
                    'has_started': True if status_code > 1 else False,
                    'period_num': period_num,
                    'period_type': period_type,
                    'period_time_remaining': status_obj.get('displayClock', ''),
                    'goals': goals,
                    'home_team_scored': False,
                    'away_team_scored': False,
                    'scoring_team': None
                })
        return games
    except Exception as e:
        print(f"Error in World Cup get_games: {e}")
        return []
