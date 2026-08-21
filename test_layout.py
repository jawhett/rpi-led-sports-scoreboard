from datetime import datetime as dt
import os
import math
from PIL import Image, ImageDraw, ImageFont
from utils.font_utils import get_text_3x5_width, draw_text_3x5
from utils.format_utils import compact_down_distance, parse_odds
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

    # Extra Info text (down/dist, fouls, odds, win probability) to show in middle channel
    info_text = ""
    info_color = COLOURS['white']
    if status_code == 2:  # In Progress
        if league == 'NFL' and game.get('down_distance_text'):
            info_text = compact_down_distance(game['down_distance_text'])
            info_color = COLOURS['white']
        elif league in ('NBA', 'WNBA') and (game.get('away_fouls') is not None or game.get('home_fouls') is not None):
            info_text = f"F {game.get('away_fouls', 0)}-{game.get('home_fouls', 0)}"
            info_color = COLOURS['red_bright'] if (game.get('away_fouls', 0) >= 5 or game.get('home_fouls', 0) >= 5) else COLOURS['yellow_bright']
        elif league == 'MLB':
            outs_num = game.get('outs', 0)
            runners = []
            if game.get('runner_on_first'): runners.append("1ST")
            if game.get('runner_on_second'): runners.append("2ND")
            if game.get('runner_on_third'): runners.append("3RD")
            bases_str = "LOADED" if len(runners) == 3 else (",".join(runners) if runners else "EMPTY")
            info_text = f"O:{outs_num} B:{bases_str}"
            info_color = COLOURS['yellow_bright']

        if rotation_mode == 2 and league == 'NFL' and game.get('home_win_pct') is not None:
            pct = game['home_win_pct']
            fav_abrv = game['home_abrv'] if pct >= 50 else game['away_abrv']
            fav_pct = int(pct if pct >= 50 else (100 - pct))
            info_text = f"{fav_abrv} {fav_pct}%"
            info_color = COLOURS['green_bright']

    elif status_code == 1:  # Scheduled
        parsed_odds = parse_odds(game.get('odds_str'))
        if parsed_odds and 'fav_team' in parsed_odds and 'spread' in parsed_odds:
            info_text = f"{parsed_odds['fav_team']} {parsed_odds['spread']}"
            info_color = COLOURS['yellow_bright']
        else:
            info_text = game.get('odds_str', '')

    # --- ROWS 0..21: TEAM LOGOS (22x22) & CENTER INFO ---
    logo_size = (22, 22)
    if away_logo:
        away_logo.thumbnail(logo_size)
        img.paste(away_logo, (0, 0))

    if home_logo:
        home_logo.thumbnail(logo_size)
        img.paste(home_logo, (42, 0))

    # Possession Indicator (Visual Under-Glow)
    poss = game.get('possession')  # 'away' or 'home' or tricode
    if poss == 'away' or poss == game.get('away_abrv'):
        # Away possession under-glow (cols 6..15, row 21)
        draw.rectangle([(6, 21), (15, 21)], fill=COLOURS['yellow_bright'])
    elif poss == 'home' or poss == game.get('home_abrv'):
        # Home possession under-glow (cols 48..57, row 21)
        draw.rectangle([(48, 21), (57, 21)], fill=COLOURS['yellow_bright'])

    # Bonus Foul Visual Alert (Outer 1px vertical strip, rows 6..15)
    if game.get('away_fouls', 0) >= 5 or game.get('away_bonus'):
        draw.rectangle([(0, 6), (0, 15)], fill=COLOURS['red_bright'])
    if game.get('home_fouls', 0) >= 5 or game.get('home_bonus'):
        draw.rectangle([(63, 6), (63, 15)], fill=COLOURS['red_bright'])

    # Center Channel (cols 22..41, rows 0..21): Time / Clock / Status / Info
    if status_code == 2:  # In Progress
        if clock_seconds_override is not None:
            m = clock_seconds_override // 60
            s = clock_seconds_override % 60
            clock_str = f"{m}:{s:02d}"
        else:
            clock_str = game.get('period_time_remaining', '')

        period_str = game.get('period_str', '')
        if period_str:
            w_p = get_text_3x5_width(period_str)
            draw_text_3x5(draw, 32 - w_p // 2, 1, period_str, COLOURS['yellow'])
        if clock_str:
            w_c = get_text_3x5_width(clock_str)
            draw_text_3x5(draw, 32 - w_c // 2, 7, clock_str, COLOURS['white'])
        if info_text:
            w_i = get_text_3x5_width(info_text)
            draw_text_3x5(draw, max(22, min(32 - w_i // 2, 41 - w_i)), 14, info_text, info_color)

        # Win Probability / Momentum Micro-Bar (cols 22..41, row 21)
        if game.get('home_win_pct') is not None:
            h_pct = game['home_win_pct']
            away_px = int(round(20 * (100 - h_pct) / 100.0))
            away_color = TEAM_COLORS.get(game.get('away_abrv'), COLOURS['white'])
            home_color = TEAM_COLORS.get(game.get('home_abrv'), COLOURS['white'])
            if away_px > 0:
                draw.line([(22, 21), (22 + away_px - 1, 21)], fill=away_color)
            if away_px < 20:
                draw.line([(22 + away_px, 21), (41, 21)], fill=home_color)
            draw.point((32, 21), fill=COLOURS['black'])

    elif status_code == 3:  # Completed - Clean Stadium Layout
        # Dimmed Red Border signifying Final Status
        draw.rectangle([(0, 0), (63, 31)], outline=COLOURS.get('red_dim', (80, 15, 15)))

        # Center Channel: OT or Series context only
        ot_str = game.get('ot_str', '')
        series_text = game.get('series_text', '')

        center_text = ""
        if ot_str and ot_str not in ("Std", "None", ""):
            center_text = ot_str if 'OT' in ot_str else f"{ot_str}OT"
        elif series_text:
            center_text = series_text

        if center_text:
            w_c = get_text_3x5_width(center_text)
            draw_text_3x5(draw, 32 - w_c // 2, 8, center_text, COLOURS['yellow_bright'])

    elif status_code == 1:  # Scheduled
        date_str = game.get('date_str', 'TODAY')
        time_str = game.get('time_str', '')
        w_d = get_text_3x5_width(date_str)
        draw_text_3x5(draw, 32 - w_d // 2, 1, date_str, COLOURS['yellow_bright'])
        w_t = get_text_3x5_width(time_str)
        draw_text_3x5(draw, 32 - w_t // 2, 7, time_str, COLOURS['white'])

        # Odds on row 14
        odds_raw = game.get('odds_str', '')
        parsed_odds = parse_odds(odds_raw) if odds_raw else None
        odds_line = ""
        if parsed_odds:
            if rotation_mode == 1 and parsed_odds.get('ou'):
                odds_line = f"U{parsed_odds['ou']}"
            elif parsed_odds.get('fav_team') and parsed_odds.get('spread'):
                odds_line = f"{parsed_odds['fav_team']} {parsed_odds['spread']}"
            elif parsed_odds.get('spread'):
                odds_line = parsed_odds['spread']
            elif parsed_odds.get('ou'):
                odds_line = f"U{parsed_odds['ou']}"
        elif game.get('broadcaster'):
            odds_line = game['broadcaster'][:6].upper()

        if odds_line:
            w_o = get_text_3x5_width(odds_line)
            draw_text_3x5(draw, max(22, min(32 - w_o // 2, 41 - w_o)), 14, odds_line, COLOURS['yellow_bright'])

    # --- BOTTOM 10 PIXELS (rows 22..31, cols 0..63): CENTER SCORES & CORNER INDICATORS ---
    if status_code in (2, 3):  # Live or Final
        away_score_val = game.get('away_score', 0)
        home_score_val = game.get('home_score', 0)
        away_score_str = str(away_score_val)
        home_score_str = str(home_score_val)

        color_away = TEAM_COLORS.get(game['away_abrv'], COLOURS['white'])
        color_home = TEAM_COLORS.get(game['home_abrv'], COLOURS['white'])

        if status_code == 3:
            if away_score_val < home_score_val:
                color_away = (120, 120, 120)
            elif home_score_val < away_score_val:
                color_home = (120, 120, 120)

        score_font = FONTS['sm_bold']
        bbox_away = draw.textbbox((0, 0), away_score_str, font=score_font)
        w_away = bbox_away[2] - bbox_away[0]
        bbox_home = draw.textbbox((0, 0), home_score_str, font=score_font)
        w_home = bbox_home[2] - bbox_home[0]
        bbox_dash = draw.textbbox((0, 0), "-", font=score_font)
        w_dash = bbox_dash[2] - bbox_dash[0]

        x_dash = 32 - w_dash // 2
        x_away = x_dash - 2 - w_away
        x_home = x_dash + w_dash + 2

        draw.text((x_away, 22), away_score_str, font=score_font, fill=color_away)
        draw.text((x_dash, 22), "-", font=score_font, fill=COLOURS['grey_light'])
        draw.text((x_home, 22), home_score_str, font=score_font, fill=color_home)

        if status_code == 2:
            # Left Corner Indicator: Away timeouts
            for i in range(3):
                if i < game.get('away_timeouts', 0):
                    draw.rectangle([(i * 3, 30), (i * 3 + 1, 31)], fill=COLOURS['yellow_bright'])
                else:
                    draw.point((i * 3, 31), fill=COLOURS['grey_dark'])

            # Right Corner Indicator: Home timeouts
            for i in range(3):
                if i < game.get('home_timeouts', 0):
                    draw.rectangle([(56 + i * 3, 30), (56 + i * 3 + 1, 31)], fill=COLOURS['yellow_bright'])
                else:
                    draw.point((56 + i * 3, 31), fill=COLOURS['grey_dark'])

    elif status_code == 1:  # Scheduled
        away_abrv = game.get('away_abrv', '')
        home_abrv = game.get('home_abrv', '')
        vs_str = "@" if game.get('home_or_away') == 'away' else "VS"

        color_away = TEAM_COLORS.get(away_abrv, COLOURS['white'])
        color_home = TEAM_COLORS.get(home_abrv, COLOURS['white'])

        score_font = FONTS['sm_bold']

        # Center separator (@ or VS)
        bbox_vs = draw.textbbox((0, 0), vs_str, font=score_font)
        w_vs = bbox_vs[2] - bbox_vs[0]
        x_vs = 32 - w_vs // 2
        draw.text((x_vs, 22), vs_str, font=score_font, fill=COLOURS['yellow'])

        # Away tricode beneath away logo
        bbox_away = draw.textbbox((0, 0), away_abrv, font=score_font)
        w_away = bbox_away[2] - bbox_away[0]
        x_away = 11 - w_away // 2
        draw.text((max(0, x_away), 22), away_abrv, font=score_font, fill=color_away)

        # Home tricode beneath home logo
        bbox_home = draw.textbbox((0, 0), home_abrv, font=score_font)
        w_home = bbox_home[2] - bbox_home[0]
        x_home = 53 - w_home // 2
        draw.text((min(64 - w_home, x_home), 22), home_abrv, font=score_font, fill=color_home)

    return img


def build_suns_countdown_mock(next_game):
    img = Image.new('RGB', (64, 32), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    suns_logo = load_logo('NBA', 'PHX')
    if suns_logo:
        suns_logo.thumbnail((28, 28))
        y_pos = (32 - suns_logo.height) // 2
        img.paste(suns_logo, (1, max(0, y_pos)))

    if next_game and next_game.get('opponent_abrv'):
        opp_logo = load_logo('NBA', next_game['opponent_abrv'])
        if opp_logo:
            opp_logo.thumbnail((22, 22))
            x_pos = 63 - opp_logo.width
            y_pos = (32 - opp_logo.height) // 2
            img.paste(opp_logo, (x_pos, max(0, y_pos)))

    SUNS_ORANGE = (229, 96, 32)
    draw_text_3x5(draw, 31, 1, "PHX SUNS", SUNS_ORANGE)

    from datetime import datetime as dt
    cur_datetime = dt.today().astimezone()
    if next_game and not next_game.get('is_completed'):
        start_dt = next_game['start_datetime_local']
        days_diff = (start_dt.date() - cur_datetime.date()).days
        if days_diff > 1 and days_diff <= 60:
            count_str = f"IN {days_diff} DAYS"
            draw_text_3x5(draw, 30, 9, count_str, COLOURS['yellow_bright'])
            date_str = start_dt.strftime('%b %d').upper()
            draw_text_3x5(draw, 30, 17, date_str, COLOURS['white'])
        elif days_diff == 0:
            draw_text_3x5(draw, 30, 9, "GAMEDAY!", COLOURS['yellow_bright'])
        venue_str = f"@ {next_game['opponent_abrv']}" if next_game.get('home_or_away') == 'away' else f"VS {next_game['opponent_abrv']}"
        w = get_text_3x5_width(venue_str)
        x_b = 46 - w // 2
        draw_text_3x5(draw, max(30, x_b), 25, venue_str, COLOURS['white'])
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

    test_final_nba = {
        'league': 'NBA',
        'away_abrv': 'BOS',
        'home_abrv': 'PHX',
        'away_score': 102,
        'home_score': 108,
        'status_code': 3,
        'ot_str': ''
    }

    test_sched_nba = {
        'league': 'NBA',
        'away_abrv': 'LAL',
        'home_abrv': 'GSW',
        'status_code': 1,
        'date_str': 'TODAY',
        'time_str': '7:30P',
        'odds_str': 'GSW -4.5 O/U 228.5'
    }

    build_mock_image(test_live_nba, clock_seconds_override=624, rotation_mode=1).save('test_layout_nba_live_fouls.png')
    build_mock_image(test_final_nba, rotation_mode=0).save('test_layout_nba_final_winner.png')
    build_mock_image(test_sched_nba, rotation_mode=0).save('test_layout_nba_sched_spread.png')
    build_mock_image(test_sched_nba, rotation_mode=1).save('test_layout_nba_sched_ou.png')
    build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=1).save('test_layout_nfl_live_downdist.png')
    build_mock_image(test_live_nfl, clock_seconds_override=135, rotation_mode=2).save('test_layout_nfl_live_winprob.png')
    build_mock_image(test_sched_nfl, rotation_mode=0).save('test_layout_nfl_sched_odds.png')
    
    test_suns_next = {
        'opponent_abrv': 'DET',
        'home_or_away': 'away',
        'start_datetime_local': dt.strptime('2026-10-05 16:00:00', '%Y-%m-%d %H:%M:%S').astimezone(tz=None),
        'is_completed': False
    }
    build_suns_countdown_mock(test_suns_next).save('test_layout_suns_countdown.png')

    print("Mockups generated!")
