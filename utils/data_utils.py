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
    'SF': (170, 0, 0),
    'KC': (227, 24, 55),
    'DAL': (0, 34, 68),
    'PHI': (0, 76, 84),
    'BOS': (0, 122, 51),
    'LAL': (85, 37, 130),
    'TOR': (206, 17, 65),
    'NYK': (0, 107, 182),
    'NYY': (0, 48, 135),
    'LAD': (0, 90, 156),
    'BUF': (0, 51, 141),
    'CHI': (200, 16, 46)
}
