from setup.session_setup import session
from datetime import datetime as dt
from datetime import timezone as tz

# Note API headers that will need to be used for stats and cdn endpoints.
stats_headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.nba.com/',
    'origin': 'https://www.nba.com',
    'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
}

cdn_headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.nba.com/',
    'origin': 'https://www.nba.com',
    'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
}


def get_games(date, league_abrv):
    """ Loads NBA/WNBA game data for the provided date.

    Args:
        date (date): Date that game data should be pulled for.
        league_abrv (str): Abbreviation of the league for which to fetch game data (e.g., 'NBA', 'WNBA').

    Returns:
        list: List of dicts of game data.
    """

    try:
        # Create an empty list to hold the game dicts.
        games = []

        # Determine the league ID needed for the API calls based on the league abbreviation provided.
        league_id = determine_league_id(league_abrv)

        # First, hit the todayScoreboard endpoint to see what date it is returning.
        url = f'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_{league_id}.json'
        games_json = []
        try:
            games_response = session.get(url=url, headers=cdn_headers, timeout=5)
            if games_response.status_code == 200:
                resp_json = games_response.json()
                if 'scoreboard' in resp_json and 'gameDate' in resp_json['scoreboard']:
                    games_response_date = dt.strptime(resp_json['scoreboard']['gameDate'], '%Y-%m-%d').date()
                    if games_response_date == date:
                        games_json = resp_json['scoreboard'].get('games', [])
        except Exception:
            pass

        # Otherwise, hit the scoreboardv3 endpoint w/ the date param if no live games on todaysScoreboard
        if not games_json:
            try:
                url = f'https://stats.nba.com/stats/scoreboardv3?LeagueID={league_id}'
                games_response = session.get(url=f"{url}&GameDate={date.strftime(format='%Y-%m-%d')}", headers=stats_headers, timeout=5)
                if games_response.status_code == 200:
                    resp_json = games_response.json()
                    if 'scoreboard' in resp_json and 'games' in resp_json['scoreboard']:
                        games_json = resp_json['scoreboard']['games']
            except Exception:
                pass

        # If still no games from NBA endpoints, fallback to ESPN API
        if not games_json:
            try:
                espn_league = 'nba' if league_abrv.upper() == 'NBA' else 'wnba'
                espn_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{espn_league}/scoreboard?dates={date.strftime('%Y%m%d')}"
                espn_resp = session.get(url=espn_url, timeout=5)
                if espn_resp.status_code == 200:
                    espn_data = espn_resp.json()
                    events = espn_data.get('events', [])
                    for ev in events:
                        comp = ev['competitions'][0]
                        status_obj = ev['status']
                        status_state = status_obj['type']['state']
                        
                        # Mapping state: pre -> 1, in -> 2, post -> 3
                        status_code = 1 if status_state == 'pre' else (2 if status_state == 'in' else 3)
                        
                        try:
                            start_utc = dt.strptime(ev['date'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=tz.utc)
                        except ValueError:
                            start_utc = dt.strptime(ev['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                        start_local = start_utc.astimezone(tz=None)

                        home_team = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
                        away_team = next(t for t in comp['competitors'] if t['homeAway'] == 'away')

                        home_raw = home_team['team']['abbreviation'].upper()
                        away_raw = away_team['team']['abbreviation'].upper()

                        if league_abrv.upper() == 'NBA':
                            map_dict = {'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
                        else:
                            map_dict = {'GS': 'GSV', 'WSH': 'WAS', 'NY': 'NYL', 'LA': 'LAS', 'LV': 'LVA', 'CONN': 'CON'}

                        home_abrv = map_dict.get(home_raw, home_raw)
                        away_abrv = map_dict.get(away_raw, away_raw)

                        home_score = int(home_team['score']) if home_team.get('score') is not None else 0
                        away_score = int(away_team['score']) if away_team.get('score') is not None else 0

                        period_num = status_obj.get('period', 0)
                        clock_str = status_obj.get('displayClock', '')
                        is_halftime = (status_obj['type']['name'] == 'STATUS_HALFTIME')

                        # Odds
                        odds_str = None
                        if comp.get('odds'):
                            odds_str = comp['odds'][0].get('details')

                        # Situation / Possession
                        sit = comp.get('situation', {})
                        poss_team = None
                        if sit.get('possession'):
                            poss_team = 'home' if str(sit['possession']) == str(home_team['id']) else 'away'

                        games.append({
                            'game_id': ev['id'],
                            'home_abrv': home_abrv,
                            'away_abrv': away_abrv,
                            'home_score': home_score,
                            'away_score': away_score,
                            'start_datetime_utc': start_utc,
                            'start_datetime_local': start_local,
                            'status': status_obj['type']['detail'],
                            'status_code': status_code,
                            'has_started': True if status_code > 1 else False,
                            'period_num': period_num,
                            'period_type': 'OT' if period_num > 4 else 'Std',
                            'period_time_remaining': clock_str,
                            'is_halftime': is_halftime,
                            'home_timeouts': home_team.get('timeoutsRemaining', 3),
                            'away_timeouts': away_team.get('timeoutsRemaining', 3),
                            'home_fouls': home_team.get('fouls', 0) or 0,
                            'away_fouls': away_team.get('fouls', 0) or 0,
                            'odds_str': odds_str,
                            'possession': poss_team,
                            'home_team_scored': False,
                            'away_team_scored': False,
                            'scoring_team': None
                        })
            except Exception as e:
                print(f"ESPN fallback error: {e}")

        # For each game from NBA JSON, build a dict recording current game details.
        if games_json: # If games today.
            for game in games_json:
                if 'All-Star' not in game['gameLabel'] and 'Preseason' not in game['gameLabel'] and 'Rising Stars' not in game['gameLabel']:
                    games.append({
                        'game_id': game['gameId'],
                        'home_abrv': game['homeTeam']['teamTricode'],
                        'away_abrv': game['awayTeam']['teamTricode'],
                        'home_score': game['homeTeam']['score'],
                        'away_score': game['awayTeam']['score'],
                        'start_datetime_utc': dt.strptime(game['gameTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc),
                        'start_datetime_local': dt.strptime(game['gameTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc).astimezone(tz=None),
                        'status': game['gameStatusText'],
                        'status_code': game['gameStatus'],
                        'has_started': True if game['gameStatus'] > 1 else False,
                        'period_num': game['period'],
                        'period_type': 'OT' if game['period'] > 4 else 'Std',
                        'period_time_remaining': game['gameClock'][2:4] + ':' + game['gameClock'][5:7] if game['gameClock'] != ':' else None,
                        'is_halftime': True if game['gameClock'] == 'PT00M00.00S' and game['period'] == 2 else False,
                        'home_timeouts': game['homeTeam'].get('timeoutsRemaining', 0),
                        'away_timeouts': game['awayTeam'].get('timeoutsRemaining', 0),
                        'home_fouls': game['homeTeam'].get('fouls', 0) or 0,
                        'away_fouls': game['awayTeam'].get('fouls', 0) or 0,
                        'home_team_scored': False,
                        'away_team_scored': False,
                        'scoring_team': None
                    })

        # Sort games by game_id, ensuring that order remains consistent after games start/end.
        games = sorted(games, key=lambda x: str(x['game_id']))
        return games


    except Exception as e:
        print(f'Error in get_games: {e}')
        return []
def get_next_game(team, league_abrv):
    """ Loads next game details for the supplied NBA/WNBA team.
    If the team is currently playing, will return details of the current game.

    Args:
        team (str): Three char abbreviation of the team to pull next game details for.
        league_abrv (str): Abbreviation of the league for which to fetch game data (e.g., 'NBA', 'WNBA').

    Returns:
            dict: Dict of next game details.
    """

    # Get the current NBA/WNBA season based on the current date and league ID from abbreviation provided.
    season = determine_current_season(league_abrv)
    league_id = determine_league_id(league_abrv)

    # Call the NBA/WNBA schedule API for the team specified and store the JSON results.
    # TODO: Save these results to avoid multiple calls if multiple favorite teams are set.
    url = f'https://stats.nba.com/stats/scheduleleaguev2?LeagueID={league_id}'   
    schedule_response = session.get(url=f'{url}&Season={season}', headers=stats_headers)
    schedule_json = schedule_response.json()['leagueSchedule']['gameDates']

    # Determine the future games.
    cur_datetime = dt.today().astimezone()
    cur_date = cur_datetime.date()
    upcoming_days_games = [day_games for day_games in schedule_json if dt.strptime(day_games['gameDate'], '%m/%d/%Y %H:%M:%S').date() >= cur_date]
    
    # Determine the next game for the team specified (looking ahead across full schedule)
    for day_game in upcoming_days_games:
        for game in day_game['games']:
            if game['homeTeam']['teamTricode'] == team or game['awayTeam']['teamTricode'] == team:
                start_datetime_utc = dt.strptime(game['gameDateTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc)
                start_datetime_local = start_datetime_utc.astimezone(tz=None)
                is_today = (start_datetime_local.date() == cur_date or start_datetime_local < cur_datetime)
                has_started = (cur_datetime >= start_datetime_local)
                
                next_game = {
                    'home_or_away': 'away' if game['homeTeam']['teamTricode'] != team else 'home',
                    'opponent_abrv': game['homeTeam']['teamTricode'] if game['homeTeam']['teamTricode'] != team else game['awayTeam']['teamTricode'],
                    'start_datetime_utc': start_datetime_utc,
                    'start_datetime_local': start_datetime_local,
                    'is_today': is_today,
                    'has_started': has_started,
                    'game_label': game.get('gameLabel', '')
                }

                # Skip to next game if this one has started more than 3 hours ago
                if next_game['has_started'] and (cur_datetime - next_game['start_datetime_local']).total_seconds() > 10800:
                    continue

                return next_game
    
    # Fallback: Find the last completed game of the season for this team
    past_days_games = [day_games for day_games in schedule_json if dt.strptime(day_games['gameDate'], '%m/%d/%Y %H:%M:%S').date() < cur_date]
    for day_game in reversed(past_days_games):
        for game in reversed(day_game['games']):
            if game['gameLabel'] != 'Preseason':
                if game['homeTeam']['teamTricode'] == team or game['awayTeam']['teamTricode'] == team:
                    home_score = game['homeTeam'].get('score', 0)
                    away_score = game['awayTeam'].get('score', 0)
                    
                    is_home = game['homeTeam']['teamTricode'] == team
                    fav_score = home_score if is_home else away_score
                    opp_score = away_score if is_home else home_score
                    is_win = fav_score > opp_score
                    
                    return {
                        'home_or_away': 'home' if is_home else 'away',
                        'opponent_abrv': game['awayTeam']['teamTricode'] if is_home else game['homeTeam']['teamTricode'],
                        'start_datetime_utc': dt.strptime(game['gameDateTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc),
                        'start_datetime_local': dt.strptime(game['gameDateTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz.utc).astimezone(tz=None),
                        'is_today': False,
                        'has_started': True,
                        'is_completed': True,
                        'is_offseason': True,
                        'is_win': is_win,
                        'score_str': f"{fav_score}-{opp_score}"
                    }

    return None


def get_standings(league_abrv):
    """ Loads current NBA/WNBA standings by division, conference, and overall league.

    Args:
        league_abrv (str): Abbreviation of the league for which to fetch standings data (e.g., 'NBA', 'WNBA').

    Returns:
        dict: Dict containing all standings by each category.
    """

    try:
        # Get the current NBA/WNBA season based on the current date and league ID from abbreviation provided.
        season = determine_current_season(league_abrv)
        league_id = determine_league_id(league_abrv)
    
        standings_json = []
        try:
            url = f'https://stats.nba.com/stats/leaguestandingsv3?LeagueID={league_id}&SeasonType=Regular Season'
            standings_response = session.get(url=f'{url}&Season={season}', headers=stats_headers, timeout=5)
            if standings_response.status_code == 200:
                standings_json_unprocessed = standings_response.json()['resultSets'][0]
                for team in standings_json_unprocessed['rowSet']:
                    team_values = {}
                    for header, value in zip(standings_json_unprocessed['headers'], team):
                        team_values[header] = value
                    team_values['teamTricode'] = determine_team_abbreviation(team_values['TeamID'], league_abrv)
                    standings_json.append(team_values)
        except Exception:
            pass

        # Fallback to ESPN Standings if NBA stats API was blocked
        if not standings_json:
            try:
                espn_league = 'nba' if league_abrv.upper() == 'NBA' else 'wnba'
                espn_url = f'https://site.api.espn.com/apis/v2/sports/basketball/{espn_league}/standings'
                resp = session.get(espn_url, timeout=5)
                if resp.status_code == 200:
                    espn_data = resp.json()
                    for conf_obj in espn_data.get('children', []):
                        conf_name = 'East' if 'East' in conf_obj.get('name', '') else 'West'
                        for rank_idx, entry in enumerate(conf_obj.get('standings', {}).get('entries', []), 1):
                            raw_abrv = entry['team']['abbreviation'].upper()
                            map_dict = {'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'} if league_abrv == 'NBA' else {'GS': 'GSV', 'WSH': 'WAS', 'NY': 'NYL', 'LA': 'LAS', 'LV': 'LVA', 'CONN': 'CON'}
                            tricode = map_dict.get(raw_abrv, raw_abrv)
                            win_pct = 0.0
                            for stat in entry.get('stats', []):
                                if stat.get('name') == 'winPercent':
                                    win_pct = float(stat.get('value', 0.0))
                            clinched = any(s.get('name') == 'clincher' for s in entry.get('stats', []))

                            standings_json.append({
                                'teamTricode': tricode,
                                'Conference': conf_name,
                                'Division': 'Central', # default
                                'PlayoffRank': rank_idx,
                                'DivisionRank': rank_idx,
                                'WinPCT': win_pct,
                                'ClinchedPostSeason': 1 if clinched else 0,
                                'ClinchIndicator': ' - x' if clinched else ''
                            })
            except Exception as e:
                print(f"ESPN Standings fallback error: {e}")

        # How the standings are structured depends on the league, so determine the structure based on the league and populate accordingly.
        if league_abrv == 'NBA':
            # Set up structure of the returned dict.
            # Teams lists will be populated w/ the API results.
            standings = {
                'retrieved_on': dt.now().astimezone(),
                'conference': {
                    conf: {
                        'subdivision_abrv': conf_abrv,
                        'rank_method': 'Win Percentage',
                        'playoff_cutoff_hard': 10,
                        'playoff_cutoff_soft': 6,
                        'team_standings': []
                    } for conf, conf_abrv in [('East', 'EC'), ('West', 'WC')]
                },
                'division': {
                    div: {
                        'subdivision_abrv': div_abrv,
                        'rank_method': 'Win Percentage',
                        'team_standings': []
                    } for div, div_abrv in [('Atlantic', 'Atl'), ('Central', 'Cen'), ('Southeast', 'SE'), ('Northwest', 'NW'), ('Pacific', 'Pac'), ('Southwest', 'SW')]
                }
            }

            # Populate the team lists w/ dicts containing details of each team.
            # API returns teams in overall standing order, so generally won't have to sort.
            for team in standings_json:
                # Conferences.
                standings['conference'][team['Conference']]['team_standings'].append({
                    'team_abrv': team['teamTricode'],
                    'rank': team['PlayoffRank'],
                    'percent': f'{team["WinPCT"]:.3f}', # Make percent a string formatted to 3 decimal places. E.g., 0.625.
                    'has_clinched': True if team['ClinchedPostSeason'] == 1 else False
                })

                # Divisions.
                standings['division'][team['Division']]['team_standings'].append({
                    'team_abrv': team['teamTricode'],
                    'rank': team['DivisionRank'],
                    'percent': f'{team["WinPCT"]:.3f}',
                    'has_clinched': True if team['ClinchedPostSeason'] == 1 else False
                })
    
        elif league_abrv == 'WNBA':
            # Set up structure of the returned dict.
            # Teams lists will be populated w/ the API results.
            standings = {
                'retrieved_on': dt.now().astimezone(),
                'league': {
                    'WNBA': { # Match structure needed for other standing types.
                        'rank_method': 'Win Percentage',
                        'playoff_cutoff_hard': 8,
                        'team_standings': [] # Will be populated w/ the API results.
                    }
                }
            }

            # Populate the team lists w/ dicts containing details of each team.
            # API returns teams in overall standing order, so generally won't have to sort.
            for team in standings_json:
                # Overall.
                standings['league']['WNBA']['team_standings'].append({
                        'team_abrv': team['teamTricode'],
                        'rank': team['PlayoffRank'],
                        'percent': f'{team["WinPCT"]:.3f}', # Make percent a string formatted to 3 decimal places. E.g., 0.625.
                        'has_clinched': True if team['ClinchIndicator'] == ' - x' else False # ClinchedPostSeason isn't populated in WNBA API.
                })

        return standings


    except Exception as e:
        print(f'Error in get_standings: {e}')
        return {}
def determine_league_id(league_abrv):
    """ Gets league ID based on league abbreviation.

    Args:
        league_abrv (str): Abbreviation of the league. E.g., 'NBA', 'WNBA'.

    Returns:
        str: League ID per the NBA API.
    """

    league_abrv_to_ids = {
        'NBA': '00',
        'WNBA': '10'
    }

    return league_abrv_to_ids.get(league_abrv, None)


def determine_current_season(league_abrv):
    """ Determines the current NBA/WNBA season based on the current date.

    Args:
        league_abrv (str): Abbreviation of the league. E.g., 'NBA', 'WNBA'.

    Returns:
        str: Current NBA season in 'YYYY-YY' (NBA) or 'YYYY' (WNBA) format.
    """

    cur_date = dt.today().astimezone().date()

    if league_abrv == 'NBA':
        return f'{cur_date.year}-{str(cur_date.year + 1)[2:4]}' if cur_date.month >= 7 else f'{cur_date.year -1}-{str(cur_date.year)[2:4]}'
    elif league_abrv == 'WNBA':
        return str(cur_date.year) # WNBA season is contained within a single calendar year, so just return the year.


def determine_team_abbreviation(team_id, league_abrv):
    """ Gets NBA/WNBA team abbreviation (tricode) based on team ID.

    Args:
        team_id (int): ID of the NBA/WNBA team per the NBA/WNBA API.
        league_abrv (str): Abbreviation of the league. E.g., 'NBA', 'WNBA'.

    Returns:
        str: Team tricode.
    """

    # Mapping of NBA teams IDs to abbreviations. Needed since schedule API does not return abbreviations.
    nba_team_ids_to_abbreviations = {
        1610612737: 'ATL',
        1610612738: 'BOS',
        1610612739: 'CLE',
        1610612740: 'NOP',
        1610612741: 'CHI',
        1610612742: 'DAL',
        1610612743: 'DEN',
        1610612744: 'GSW',
        1610612745: 'HOU',
        1610612746: 'LAC',
        1610612747: 'LAL',
        1610612748: 'MIA',
        1610612749: 'MIL',
        1610612750: 'MIN',
        1610612751: 'BKN',
        1610612752: 'NYK',
        1610612753: 'ORL',
        1610612754: 'IND',
        1610612755: 'PHI',
        1610612756: 'PHX',
        1610612757: 'POR',
        1610612758: 'SAC',
        1610612759: 'SAS',
        1610612760: 'OKC',
        1610612761: 'TOR',
        1610612762: 'UTA',
        1610612763: 'MEM',
        1610612764: 'WAS',
        1610612765: 'DET',
        1610612766: 'CHA'
    }

    # Mapping of WNBA teams IDs to abbreviations. Needed since schedule API does not return abbreviations.
    wnba_team_ids_to_abbreviations = {
        1611661313: 'NYL',
        1611661317: 'PHX',
        1611661319: 'LVA',
        1611661320: 'LAS',
        1611661321: 'DAL',
        1611661322: 'WAS',
        1611661323: 'CON',
        1611661324: 'MIN',
        1611661325: 'IND',
        1611661327: 'PDX',
        1611661328: 'SEA',
        1611661329: 'CHI',
        1611661330: 'ATL',
        1611661331: 'GSV',
        1611661332: 'TOR'
    }

    # Determine which mapping to use and return the appropriate abbreviation based on the team ID.
    team_mapping = nba_team_ids_to_abbreviations if league_abrv == 'NBA' else wnba_team_ids_to_abbreviations
    return team_mapping.get(team_id, None)