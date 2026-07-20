def compact_down_distance(text):
    if not text:
        return ""
    text = text.upper().replace(" & ", "&")
    text = text.replace("GOAL", "G")
    return text


def parse_odds(odds_str):
    if not odds_str:
        return None
    try:
        fav_team, spread_val, ou_val = "", "", ""
        if ' O/U ' in odds_str:
            parts = odds_str.split(' O/U ')
            spread_part = parts[0].strip()
            ou_val = parts[1].strip()
        else:
            spread_part = odds_str.strip()
            ou_val = ""

        spread_parts = spread_part.split(' ')
        if len(spread_parts) >= 2:
            fav_team = spread_parts[0].strip()
            spread_val = spread_parts[1].strip()
        else:
            for sign in ('-', '+'):
                if sign in spread_part:
                    idx = spread_part.find(sign)
                    fav_team = spread_part[:idx].strip()
                    spread_val = spread_part[idx:].strip()
                    break
            if not fav_team:
                fav_team = spread_part
                spread_val = ""

        return {
            'fav_team': fav_team,
            'spread': spread_val,
            'ou': ou_val
        }
    except Exception as e:
        print(f"Error parsing odds {odds_str}: {e}")
    return None
