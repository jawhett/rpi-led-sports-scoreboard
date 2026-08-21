import yaml
import os

_yaml_cache = {}

def read_yaml(file_path):
    """ Safely reads a .yaml file and returns a dict. Caches the result to avoid unnecessary disk I/O.

    Args:
        file_path (str): Path of .yaml file.

    Returns:
        dict: Dict correspond to the values in the .yaml file.
    """
    
    try:
        current_mtime = os.path.getmtime(file_path)
    except OSError:
        current_mtime = 0

    if file_path in _yaml_cache:
        cached_mtime, cached_data = _yaml_cache[file_path]
        if current_mtime == cached_mtime:
            return cached_data

    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        _yaml_cache[file_path] = (current_mtime, data)
        return data

TEAM_COLORS = {
    # NBA
    'PHX': (229, 96, 32),    # Phoenix Suns Orange
    'BOS': (0, 122, 51),     # Celtics Green
    'BKN': (255, 255, 255),  # Nets White/Black
    'NYK': (0, 107, 182),    # Knicks Blue
    'PHI': (0, 107, 182),    # 76ers Blue
    'CHI': (206, 17, 65),    # Bulls Red
    'CLE': (134, 0, 56),     # Cavaliers Wine
    'DET': (200, 16, 46),    # Pistons Red
    'IND': (0, 45, 98),      # Pacers Navy
    'MIL': (0, 71, 27),      # Bucks Green
    'ATL': (225, 58, 62),    # Hawks Red
    'CHA': (29, 17, 96),     # Hornets Purple
    'MIA': (152, 0, 46),     # Heat Maroon
    'ORL': (0, 119, 192),    # Magic Blue
    'WAS': (0, 42, 92),      # Wizards Navy
    'DEN': (13, 34, 64),     # Nuggets Navy
    'MIN': (12, 35, 64),     # Timberwolves Navy
    'OKC': (0, 125, 195),    # Thunder Blue
    'POR': (224, 58, 62),    # Trail Blazers Red
    'UTA': (0, 43, 92),      # Jazz Navy
    'GSW': (29, 66, 138),    # Warriors Blue
    'GS':  (29, 66, 138),
    'LAC': (200, 16, 46),    # Clippers Red
    'LAL': (85, 37, 130),    # Lakers Purple
    'SAC': (91, 43, 130),    # Kings Purple
    'DAL': (0, 83, 188),     # Mavericks Blue
    'HOU': (206, 17, 65),    # Rockets Red
    'MEM': (93, 118, 169),   # Grizzlies Blue
    'NOP': (12, 35, 64),     # Pelicans Navy
    'NO':  (12, 35, 64),
    'SAS': (196, 206, 211),  # Spurs Silver
    'TOR': (206, 17, 65),    # Raptors Red

    # NFL
    'SF':  (170, 0, 0),     # 49ers Red
    'KC':  (227, 24, 55),    # Chiefs Red
    'BAL': (26, 25, 95),     # Ravens Purple
    'BUF': (0, 51, 141),     # Bills Blue
    'CIN': (251, 79, 20),    # Bengals Orange
    'CLE_NFL': (255, 60, 0), # Browns Orange
    'DEN_NFL': (251, 79, 20),# Broncos Orange
    'HOU_NFL': (3, 32, 47),  # Texans Navy
    'IND_NFL': (0, 45, 98),  # Colts Horseshoe Blue
    'JAX': (0, 103, 120),    # Jaguars Teal
    'LV':  (196, 206, 211),  # Raiders/Aces Silver (prevent pure black score on black matrix)
    'LAC_NFL': (0, 128, 198),# Chargers Powder Blue
    'MIA_NFL': (0, 142, 151),# Dolphins Teal
    'NE':  (0, 34, 68),      # Patriots Navy
    'NYJ': (18, 87, 64),     # Jets Green
    'PIT': (255, 182, 18),   # Steelers Gold
    'TEN': (75, 146, 219),   # Titans Blue
    'ARI': (151, 35, 63),    # Cardinals Red
    'ATL_NFL': (167, 25, 48),# Falcons Red
    'CAR': (0, 133, 202),    # Panthers Blue
    'CHI_NFL': (11, 22, 42), # Bears Navy
    'DAL_NFL': (0, 53, 148), # Cowboys Blue
    'DET_NFL': (0, 118, 206),# Lions Honolulu Blue
    'GB':  (32, 55, 49),     # Packers Green
    'LAR': (0, 53, 148),     # Rams Blue
    'MIN_NFL': (79, 38, 131),# Vikings Purple
    'NO_NFL': (211, 188, 141),# Saints Gold
    'NYG': (1, 35, 82),      # Giants Blue
    'PHI_NFL': (0, 76, 84),  # Eagles Midnight Green
    'SEA': (0, 34, 68),      # Seahawks Navy
    'TB':  (215, 11, 44),    # Buccaneers Red
    'WAS_NFL': (90, 20, 35), # Commanders Burgundy

    # MLB
    'NYY': (0, 48, 135),     # Yankees Navy
    'LAD': (0, 90, 156),     # Dodgers Blue
    'BOS_MLB': (189, 48, 57),# Red Sox Red
    'CHC': (14, 51, 134),    # Cubs Blue
    'CHW': (196, 206, 211),  # White Sox Silver
    'HOU_MLB': (235, 110, 31),# Astros Orange
    'NYM': (0, 44, 119),     # Mets Blue
    'PHI_MLB': (232, 24, 40),# Phillies Red
    'SD':  (255, 196, 37),   # Padres Gold
    'SF_MLB': (253, 90, 30), # Giants Orange
    'STL': (196, 30, 58),    # Cardinals Red
    'TEX': (0, 50, 120),     # Rangers Blue

    # NHL
    'BOS_NHL': (252, 181, 20),# Bruins Gold
    'COL': (111, 38, 61),    # Avalanche Burgundy
    'EDM': (4, 30, 66),      # Oilers Blue
    'FLA': (200, 16, 46),    # Panthers Red
    'MTL': (175, 30, 45),    # Canadiens Red
    'NYR': (1, 51, 161),     # Rangers Blue
    'TOR_NHL': (0, 32, 91),  # Maple Leafs Blue
    'VGK': (185, 151, 91),   # Golden Knights Gold
}

def get_team_color(abrv, fallback=(255, 255, 255)):
    """ Returns a high-contrast team color, ensuring colors are never black or too dim to see on LED matrix.
    """
    color = TEAM_COLORS.get(abrv, fallback)
    r, g, b = color
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 35 or color == (0, 0, 0):
        return (220, 220, 220)
    return color

