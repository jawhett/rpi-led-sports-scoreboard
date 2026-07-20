import os
import math
from PIL import Image, ImageDraw, ImageFont
from utils.data_utils import TEAM_COLORS

# Define fonts
FONTS = {
    'sm':       ImageFont.load('assets/fonts/Tamzen5x9r.pil'),
    'sm_bold':  ImageFont.load('assets/fonts/Tamzen5x9b.pil'),
    'med':      ImageFont.load('assets/fonts/Tamzen6x12r.pil'),
    'med_bold': ImageFont.load('assets/fonts/Tamzen6x12b.pil'),
    'lrg':      ImageFont.load('assets/fonts/Tamzen8x16r.pil'),
    'lrg_bold': ImageFont.load('assets/fonts/Tamzen8x16b.pil'),
    'giant_bold': ImageFont.load('assets/fonts/Tamzen10x20b.pil'),
}

COLOURS = {
    'white':        (255, 255, 255),
    'black':        (0, 0, 0),
    'grey_dark':    (70, 70, 70),
    'grey_light':   (180, 180, 180),
    'red':          (255, 50, 50),
    'yellow':       (255, 209, 0),
    'green':        (28, 122, 0),
    'cyan':         (0, 192, 255),
    'green_bright': (0, 255, 127),
    'red_bright':   (255, 48, 48),
    'yellow_bright':(255, 215, 0)
}

def crop_image(image):
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    
    cropped_image = Image.new('RGB', image.size, (0, 0, 0))
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        cropped_image.paste(image, (0, 0), image)
    else:
        cropped_image.paste(image)
    return cropped_image

def load_logo(league, team_abrv):
    logo_path = f'assets/images/{league}/teams/{team_abrv}.png'
    if not os.path.exists(logo_path):
        return None
    try:
        logo = Image.open(logo_path)
        logo = crop_image(logo)
        return logo
    except Exception as e:
        print(f"Error loading logo {logo_path}: {e}")
        return None






def build_mock_image(game, clock_seconds_override=None, rotation_mode=0):
    img = Image.new('RGB', (64, 32), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    away_logo = load_logo(game['league'], game['away_abrv'])
    home_logo = load_logo(game['league'], game['home_abrv'])

    status_code = game['status_code']
    league = game['league']

    # Keep logos compact in the top corners (size 12x9) for live, but enlarge to 24x16 for scheduled
    logo_size = (24, 16) if status_code == 1 else (12, 9)

    if away_logo:
        away_logo.thumbnail(logo_size)
    if home_logo:
        home_logo.thumbnail(logo_size)

    # Draw Away Logo (clean floating in top-left or centered)
    if away_logo:
        if status_code == 1: # Scheduled: center it in left half, rows 0..17
            x = (32 - away_logo.width) // 2
            y = (18 - away_logo.height) // 2
        else: # Live
            x = 1
            y = (10 - away_logo.height) // 2
        img.paste(away_logo, (x, max(0, y)))

    # Draw Home Logo (clean floating in top-right or centered)
    if home_logo:
        if status_code == 1: # Scheduled: center it in right half, rows 0..17
            x = 32 + (32 - home_logo.width) // 2
            y = (18 - home_logo.height) // 2
        else: # Live
            x = 63 - home_logo.width
            y = (10 - home_logo.height) // 2
        img.paste(home_logo, (x, max(0, y)))

    # 2. Top Center channel (cols 14..49, y=1..10) for Clock / Period or FINAL
    if status_code == 2:  # In Progress
        if clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            clock_str = f"{m}:{s:02d}"
        else:
            clock_str = game['period_time_remaining']
        
        status_text = f"{game['period_str']} {clock_str}"
        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(draw, x, 1, status_text, COLOURS['yellow'])

        # Draw clean possession indicator dots right next to status channel
        if league == 'NFL' and game.get('possession'):
            poss_color = COLOURS['red_bright'] if game.get('is_red_zone') else COLOURS['yellow_bright']
            if game['possession'] == 'away':
                draw.rectangle([(x - 4, 4), (x - 3, 5)], fill=poss_color)
            elif game['possession'] == 'home':
                draw.rectangle([(x + w + 2, 4), (x + w + 3, 5)], fill=poss_color)

    elif status_code == 3:  # Completed
        ot_str = game.get('ot_str', '')
        status_text = f"FINAL/{ot_str}" if ot_str else "FINAL"
        w = get_text_3x5_width(status_text)
        x = 32 - w // 2
        draw_text_3x5(draw, x, 1, status_text, COLOURS['red_bright'])

    # 3. Draw Timeouts/Bonus Indicators (row 11) - placed cleanly under the logos
    if status_code != 1:  # Not for Scheduled games
        if league == 'NFL':
            # 3 timeout dots for NFL
            for i in range(3):
                color = COLOURS['yellow_bright'] if i < game.get('away_timeouts', 0) else COLOURS['grey_dark']
                draw.point((1 + i * 3, 10), fill=color)
                draw.point((2 + i * 3, 10), fill=color)
            for i in range(3):
                color = COLOURS['yellow_bright'] if i < game.get('home_timeouts', 0) else COLOURS['grey_dark']
                draw.point((53 + i * 3, 10), fill=color)
                draw.point((54 + i * 3, 10), fill=color)
        else:  # NBA/WNBA
            # 7 timeout dots for NBA
            for i in range(7):
                color = COLOURS['yellow_bright'] if i < game.get('away_timeouts', 0) else COLOURS['grey_dark']
                draw.point((0 + i * 2, 10), fill=color)
            for i in range(7):
                color = COLOURS['yellow_bright'] if i < game.get('home_timeouts', 0) else COLOURS['grey_dark']
                draw.point((50 + i * 2, 10), fill=color)
            
            # NBA Bonus lights next to timeouts on row 11
            if game.get('away_fouls', 0) >= 5:
                draw.rectangle([(15, 10), (17, 10)], fill=COLOURS['red_bright'])
            if game.get('home_fouls', 0) >= 5:
                draw.rectangle([(46, 10), (48, 10)], fill=COLOURS['red_bright'])

    # 4. Draw Scores (row 11..30) - using FONTS['giant_bold'] (10x20)
    if status_code == 2 or status_code == 3:  # In Progress or Completed
        # Draw Away Score
        away_score = game['away_score']
        away_color = TEAM_COLORS.get(game['away_abrv'], COLOURS['white'])
        if status_code == 3 and game['away_score'] < game['home_score']:
            away_color = (away_color[0] // 3, away_color[1] // 3, away_color[2] // 3)
            
        w = len(str(away_score)) * 8
        x = 16 - w // 2
        draw.text((x, 12), str(away_score), font=FONTS['lrg_bold'], fill=away_color)

        # Draw Home Score
        home_score = game['home_score']
        home_color = TEAM_COLORS.get(game['home_abrv'], COLOURS['white'])
        if status_code == 3 and game['home_score'] < game['away_score']:
            home_color = (home_color[0] // 3, home_color[1] // 3, home_color[2] // 3)
            
        w = len(str(home_score)) * 8
        x = 48 - w // 2
        draw.text((x, 12), str(home_score), font=FONTS['lrg_bold'], fill=home_color)

    # 5. Horizontal bottom banner (row 27..31) for secondary info (leaves row 26 blank for padding)
    if status_code == 2:  # In Progress
        banner_text = ""
        banner_color = COLOURS['white']

        if league == 'NFL' and game.get('down_distance_text'):
            banner_text = compact_down_distance(game['down_distance_text'])
            banner_color = COLOURS['white']
        elif league in ('NBA', 'WNBA') and (game.get('away_fouls') is not None or game.get('home_fouls') is not None):
            banner_text = f"FOULS {game.get('away_fouls', 0)}-{game.get('home_fouls', 0)}"
            if game.get('away_fouls', 0) >= 5 or game.get('home_fouls', 0) >= 5:
                banner_color = COLOURS['red_bright']
            else:
                banner_color = COLOURS['yellow_bright']

        # Handle win probability logic specifically
        if rotation_mode == 2 and league == 'NFL' and game.get('home_win_pct') is not None:
            pct = game['home_win_pct']
            fav_abrv = game['home_abrv'] if pct >= 50 else game['away_abrv']
            fav_pct = int(pct if pct >= 50 else (100 - pct))
            banner_text = f"{fav_abrv} WIN PROB {fav_pct}%"
            banner_color = COLOURS['green_bright']

        # Center banner text using our 3x5 font helper (drawn at y=27 to create 1px padding on row 26)
        if banner_text:
            w = get_text_3x5_width(banner_text)
            x = 32 - w // 2
            draw_text_3x5(draw, x, 27, banner_text, banner_color)

    elif status_code == 1:  # Scheduled
        parsed_odds = parse_odds(game.get('odds_str'))
        # Show matchup abbreviations below logos for scheduled (using sm_bold for smaller names, y=18)
        w = len(game['away_abrv']) * 5
        x = 16 - w // 2
        draw.text((x, 18), game['away_abrv'], font=FONTS['sm_bold'], fill=COLOURS['white'])

        w = len(game['home_abrv']) * 5
        x = 48 - w // 2
        draw.text((x, 18), game['home_abrv'], font=FONTS['sm_bold'], fill=COLOURS['white'])

        # Banner at the bottom for kickoff / odds (starting at y=27)
        if rotation_mode == 1 and parsed_odds:
            odds_str = f"{parsed_odds['fav_team']} {parsed_odds['spread']}"
            if parsed_odds['ou']:
                odds_str = f"{odds_str} U{parsed_odds['ou']}"
            w = get_text_3x5_width(odds_str)
            x = 32 - w // 2
            draw_text_3x5(draw, x, 27, odds_str, COLOURS['yellow_bright'])
        else:
            time_str = f"{game['date_str']} {game['time_str']}"
            w = get_text_3x5_width(time_str)
            x = 32 - w // 2
            draw_text_3x5(draw, x, 27, time_str, COLOURS['white'])

    elif status_code == 3:  # Completed
        # Display OT details in bottom banner
        ot_str = game.get('ot_str', '')
        banner_text = f"FINAL / {ot_str}" if ot_str else "FINAL"
        w = get_text_3x5_width(banner_text)
        x = 32 - w // 2
        draw_text_3x5(draw, x, 27, banner_text, COLOURS['red_bright'])

    return img

if __name__ == '__main__':
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
        'home_fouls': 5
    }

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

    test_sched_nfl = {
        'league': 'NFL',
        'away_abrv': 'DAL',
        'home_abrv': 'PHI',
        'status_code': 1,
        'date_str': 'TODAY',
        'time_str': '8:15',
        'odds_str': 'PHI -3.5 O/U 48.5',
        'away_timeouts': 3,
        'home_timeouts': 3
    }

    build_mock_image(test_live_nba, clock_seconds_override=624, rotation_mode=1).save('test_layout_nba_live_fouls.png')
    build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=1).save('test_layout_nfl_live_downdist.png')
    build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=2).save('test_layout_nfl_live_winprob.png')
    build_mock_image(test_sched_nfl, rotation_mode=1).save('test_layout_nfl_sched_odds.png')
    
    print("Mockups generated!")
