import time
import os
import sys

# Append workspace directory to Python path to import correctly
sys.path.append('/home/nba/rpi-led-sports-scoreboard')
os.chdir('/home/nba/rpi-led-sports-scoreboard')

# Stop service temporarily
os.system("sudo systemctl stop sports-scoreboard.service")

try:
    from setup.matrix_setup import matrix
    from test_layout import build_mock_image

    test_live_nfl = {
        'league': 'NFL',
        'away_abrv': 'SF',
        'home_abrv': 'KC',
        'away_score': 24,
        'home_score': 28,
        'status_code': 2,
        'period_time_remaining': '2:15',
        'period_str': '4TH',
        'away_timeouts': 2,
        'home_timeouts': 1,
        'possession': 'away',
        'is_red_zone': True,
        'down_distance_text': '1ST & GOAL',
        'home_win_pct': 36.2
    }

    print("Displaying Live NFL layout mockup with giant scores and outer tickers for 15 seconds...")
    img = build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=1)
    matrix.SetImage(img)
    time.sleep(15)

finally:
    # Always restart the service
    print("Restarting service...")
    os.system("sudo systemctl start sports-scoreboard.service")
