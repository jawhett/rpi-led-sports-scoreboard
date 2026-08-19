import time
import os
import sys

# Append workspace directory to Python path to import correctly
sys.path.append('/home/nba/rpi-led-sports-scoreboard')
os.chdir('/home/nba/rpi-led-sports-scoreboard')

# Stop service temporarily to control the LED matrix
print("Stopping sports-scoreboard service...")
os.system("sudo systemctl stop sports-scoreboard.service")

try:
    from setup.matrix_setup import matrix
    from test_layout import build_mock_image

    print("=== STARTING DYNAMIC NBA LIVE GAME DEMO ===")
    
    test_live_nba = {
        'league': 'NBA',
        'away_abrv': 'PHX',
        'home_abrv': 'LAL',
        'away_score': 108,
        'home_score': 107,
        'status_code': 2,
        'period_time_remaining': '0:24',
        'period_str': '4TH',
        'away_timeouts': 2,
        'home_timeouts': 3,
        'away_fouls': 3,
        'home_fouls': 4,
        'possession': 'away'
    }
    
    # Timeline steps
    # We will loop for 24 simulated seconds, pausing 1.0s per step
    clock_sec = 24
    
    for i in range(25):
        # Step 0-5: PHX has ball, clock ticks down
        # Step 6: PHX scores! Score becomes PHX 110 - LAL 107.
        if i == 6:
            print("[DEMO UPDATE] PHX Scores! PHX 110 - LAL 107")
            test_live_nba['away_score'] = 110
            test_live_nba['possession'] = 'home'
            
        # Step 9: LAL calls a Timeout! Home timeouts decrease to 2.
        if i == 9:
            print("[DEMO UPDATE] LAL calls Timeout. Timeouts: PHX 2 - LAL 2")
            test_live_nba['home_timeouts'] = 2
            
        # Step 14: PHX commits a foul! Away fouls become 4.
        if i == 14:
            print("[DEMO UPDATE] PHX Foul! Fouls: PHX 4 - LAL 4")
            test_live_nba['away_fouls'] = 4
            
        # Step 18: PHX commits another foul! Away fouls become 5 (BONUS ACTIVATED!). Red bonus light shines on left side.
        if i == 18:
            print("[DEMO UPDATE] PHX Foul! BONUS ACTIVATED for LAL! Fouls: PHX 5 - LAL 4")
            test_live_nba['away_fouls'] = 5
            
        # Step 20: LAL shoots free throws and makes them. Score: PHX 110 - LAL 109.
        if i == 20:
            print("[DEMO UPDATE] LAL free throws: PHX 110 - LAL 109")
            test_live_nba['home_score'] = 109
            
        # Step 24: Clock hits 0:00. LAL buzzer-beater! Score: PHX 110 - LAL 111. Game status becomes FINAL.
        if i == 24:
            print("[DEMO UPDATE] BUZZER BEATER! LAL Wins! PHX 110 - LAL 111. FINAL")
            test_live_nba['home_score'] = 111
            test_live_nba['status_code'] = 3
            
        clock_display = max(0, clock_sec - i)
        print(f"Sec {i:02d} | Clock: 0:{clock_display:02d} | Score: PHX {test_live_nba['away_score']} - LAL {test_live_nba['home_score']} | Fouls: {test_live_nba['away_fouls']}-{test_live_nba['home_fouls']} | Timeouts: {test_live_nba['away_timeouts']}-{test_live_nba['home_timeouts']}")
        
        img = build_mock_image(test_live_nba, clock_seconds_override=clock_display, rotation_mode=1)
        matrix.SetImage(img)
        time.sleep(1.2)
        
    print("=== NBA LIVE GAME DEMO COMPLETE ===")

except Exception as e:
    print(f"Error during demo: {e}")

finally:
    # Always restart the service to restore live scoreboard operation
    print("Restarting sports-scoreboard service...")
    os.system("echo nba | sudo -S systemctl start sports-scoreboard.service")
