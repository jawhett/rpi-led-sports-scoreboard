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

    print("=== STARTING DYNAMIC LIVE GAME TEST ===")
    
    # 1. NFL Game Demo (SF @ KC)
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
        'down_distance_text': '3RD & GOAL',
        'home_win_pct': 36.2
    }
    
    clock_sec = 135 # 2:15
    print("Starting NFL live sequence (SF has the ball in the red zone)...")
    for i in range(7):
        # Update clock
        clock_sec -= 1
        
        # Simulate touchdown at i = 4 (touchdown SF!)
        if i == 3:
            print("[NFL UPDATE] Touchdown San Francisco! (Score: 31-28)")
            test_live_nfl['away_score'] = 31
            test_live_nfl['possession'] = 'home'
            test_live_nfl['is_red_zone'] = False
            test_live_nfl['down_distance_text'] = '1ST & 10'
            
        print(f"  NFL Clock: {clock_sec // 60}:{clock_sec % 60:02d} | Score: SF {test_live_nfl['away_score']} - KC {test_live_nfl['home_score']} | Possession: {test_live_nfl['possession']}")
        img = build_mock_image(test_live_nfl, clock_seconds_override=clock_sec, rotation_mode=1)
        matrix.SetImage(img)
        time.sleep(1.0)
        
    print("\nSwitching to NBA live sequence (BOS @ LAL)...")
    
    # 2. NBA Game Demo (BOS @ LAL)
    test_live_nba = {
        'league': 'NBA',
        'away_abrv': 'BOS',
        'home_abrv': 'LAL',
        'away_score': 104,
        'home_score': 99,
        'status_code': 2,
        'period_time_remaining': '10:24',
        'period_str': '3RD',
        'away_timeouts': 2,
        'home_timeouts': 4,
        'away_fouls': 3,
        'home_fouls': 4,
        'possession': 'home'
    }
    
    clock_sec = 624 # 10:24
    for i in range(8):
        clock_sec -= 1
        
        # Simulate LAL score and bonus fouls at i = 4
        if i == 4:
            print("[NBA UPDATE] Lakers score! Home fouls reach bonus limit! (Score: 104-101, Home Fouls: 5)")
            test_live_nba['home_score'] = 101
            test_live_nba['home_fouls'] = 5
            test_live_nba['possession'] = 'away'
            
        print(f"  NBA Clock: {clock_sec // 60}:{clock_sec % 60:02d} | Score: BOS {test_live_nba['away_score']} - LAL {test_live_nba['home_score']} | Possession: {test_live_nba['possession']}")
        # We can alternate rotation modes for fouls and stats display
        rot_mode = 2 if i >= 4 else 1
        img = build_mock_image(test_live_nba, clock_seconds_override=clock_sec, rotation_mode=rot_mode)
        matrix.SetImage(img)
        time.sleep(1.0)
        
    print("\nLive test complete!")

finally:
    # Always restart the service
    print("Restarting service...")
    os.system("sudo systemctl start sports-scoreboard.service")
