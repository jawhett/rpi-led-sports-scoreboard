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

img = build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=1)
img.save('output_mockup.png')
print("Saved output_mockup.png")
