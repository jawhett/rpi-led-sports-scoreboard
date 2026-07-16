from setup.session_setup import session
from datetime import datetime as dt
from datetime import timezone as tz
import json
import os
import requests
import concurrent.futures


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
            downloads = set()
            # First pass: collect all unique logos that need downloading
            for event in data_json['events']:
                comp = event['competitions'][0]
                home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')

                for team_data in [home_team, away_team]:
                    abrv = team_data['team']['abbreviation'].upper()
                    logo_url = team_data['team'].get('logo')
                    if logo_url:
                        logo_path = f'assets/images/WORLDCUP/teams/{abrv}.png'
                        if not os.path.exists(logo_path):
                            downloads.add((logo_url, logo_path, f"logo for {abrv}"))

            league_logo_path = 'assets/images/WORLDCUP/league/WORLDCUP.png'
            if not os.path.exists(league_logo_path):
                leagues_data = data_json.get('leagues', [{}])
                if leagues_data and leagues_data[0].get('logos'):
                    league_logo_url = leagues_data[0]['logos'][0]['href']
                    downloads.add((league_logo_url, league_logo_path, "WORLDCUP league logo"))

            if downloads:
                os.makedirs('assets/images/WORLDCUP/teams', exist_ok=True)
                os.makedirs('assets/images/WORLDCUP/league', exist_ok=True)

                def download_image(url, path, name):
                    try:
                        img_resp = requests.get(url, timeout=5)
                        if img_resp.status_code == 200:
                            with open(path, 'wb') as f:
                                f.write(img_resp.content)
                            print(f"Downloaded {name}")
                    except Exception as e:
                        print(f"Error downloading {name}: {e}")

                with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(downloads))) as executor:
                    futures = [executor.submit(download_image, url, path, name) for url, path, name in downloads]
                    concurrent.futures.wait(futures)

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
                
                # Parse Stage (GRP, R32, R16, QF, SF, FIN)
                stage = ''
                season_slug = event.get('season', {}).get('slug', '').lower()
                if 'round-of-32' in season_slug:
                    stage = 'R32'
                elif 'round-of-16' in season_slug:
                    stage = 'R16'
                elif 'quarter' in season_slug:
                    stage = 'QF'
                elif 'semi' in season_slug:
                    stage = 'SF'
                elif 'third' in season_slug:
                    stage = '3RD'
                elif 'final' in season_slug:
                    stage = 'FIN'
                elif 'group' in season_slug:
                    stage = 'GRP'

                # Venue & Location Details
                venue_obj = comp.get('venue', {})
                venue_name = venue_obj.get('fullName', '')
                venue_city = venue_obj.get('address', {}).get('city', '')

                # Parse events (Goals and Red Cards)
                match_events = []
                home_id = str(home_team['team']['id'])
                away_id = str(away_team['team']['id'])
                for d in comp.get('details', []):
                    is_goal = d.get('scoringPlay') or 'Goal' in d.get('type', {}).get('text', '')
                    is_red = d.get('redCard') or 'Red Card' in d.get('type', {}).get('text', '')
                    
                    if is_goal or is_red:
                        scorer = "Unknown"
                        if d.get('athletesInvolved'):
                            scorer = d['athletesInvolved'][0].get('shortName', 'Unknown')
                        clock = d.get('clock', {}).get('displayValue', '')
                        team_id = str(d.get('team', {}).get('id'))
                        
                        event_team = None
                        if team_id == home_id:
                            event_team = 'home'
                        elif team_id == away_id:
                            event_team = 'away'
                            
                        match_events.append({
                            'name': scorer,
                            'clock': clock,
                            'team': event_team,
                            'type': 'goal' if is_goal else 'red_card'
                        })
                
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
                    'stage': stage,
                    'venue_name': venue_name,
                    'venue_city': venue_city,
                    'events': match_events,
                    'home_team_scored': False,
                    'away_team_scored': False,
                    'scoring_team': None
                })
        return games
    except Exception as e:
        print(f"Error in World Cup get_games: {e}")
        return []
