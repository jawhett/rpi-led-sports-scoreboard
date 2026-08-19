import datetime
from main import get_league_games
import time

today = datetime.datetime.now().date()
print("Date:", today)

games = get_league_games('WNBA', today)
print(f"Total WNBA games found: {len(games)}")
for g in games:
    print(f"Game ID: {g.get('game_id')}")
    print(f"Matchup: {g.get('away_abrv')} @ {g.get('home_abrv')}")
    print(f"Odds: {g.get('odds_str')}")
    print("---")
