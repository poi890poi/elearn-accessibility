from enum import Enum


USERNAME = 'uername'
PASSWORD = 'password'

DOMAIN = 'www.domain.com'
COURSES = [
    (f'https://{DOMAIN}/info/10035565', 'CDDDBDBBBB'),
    (f'https://{DOMAIN}/info/10036252', ''),
    (f'https://{DOMAIN}/info/10036250', ''),
    (f'https://{DOMAIN}/info/10036256', ''),
    (f'https://{DOMAIN}/info/10035528', ''),
]

VIDEO_TIMEOUT = 900
PLAYBACK_RATE = 4

ANS_OPTIONS = {
    'A': 'option_1',
    'B': 'option_2',
    'C': 'option_3',
    'D': 'option_4',
    'E': 'option_5',
}

class PlayerType(Enum):
    MP = 0
    JP = 1
