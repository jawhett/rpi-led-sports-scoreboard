from datetime import date
from data import nba_wnba_data

games = nba_wnba_data.get_games(date(2026, 6, 21), "WNBA")
for g in games:
    print(f"{g['away_abrv']} @ {g['home_abrv']} | Start Local: {g['start_datetime_local']} | Status: {g['status']}")
