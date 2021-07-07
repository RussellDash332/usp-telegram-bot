from os import path
from json import load, loads, dump, dumps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from dpad_manager import read_dp, write_dp

DATA_DIR = path.join('.', 'bot_data')
DATA_PATH = path.join(DATA_DIR, 'bot_data.json')
PROGRESS_PATH = path.join('.', 'users_progress', 'users_progress.json')

class Puzzle:
    def __init__(self, idx, name, description, answers, social, academic, happiness, health):
        self.idx = idx
        self.name = name
        self.description = description
        if 'T' in idx: # trivia
            self.answers = answers
        elif 'S' in idx: # scenario
            self.social = social
            self.academic = academic
            self.happiness = happiness
            self.health = health
        self.is_completed = None

def set_progress(puzzles, user_id):
    user_data_str = read_dp(user_id)

    if user_data_str:
        user_progress = loads(user_data_str)['progress']
        user_soc = loads(user_data_str)['social']
        user_acad = loads(user_data_str)['academic']
        user_hap = loads(user_data_str)['happiness']
        user_hlth = loads(user_data_str)['health']
        user_forfeits = loads(user_data_str)['forfeits']
    else:
        user_progress = list()
        user_data_str = dumps({
            'progress': user_progress,
            'social': 3,
            'academic': 3,
            'happiness': 3,
            'health': 3,
            'forfeits': dict()
            }, indent=2)
        write_dp(user_id, user_data_str)

    for idx, p in puzzles.items():
        if idx in user_progress:
            p.is_completed = True

def load_data_from_csv(user_id):
    with open(DATA_PATH, 'r') as f:
        bot_data = load(f)

    puzzles = dict()
    for p_idx, data in bot_data.items():
        if 'T' in data['idx']: # trivia
            puzzle = Puzzle(data['idx'], data['name'], data['description'], data['answers'], 0, 0, 0, 0) # we won't use the last 4 parameters
        elif 'S' in data['idx']: # scenario
            puzzle = Puzzle(data['idx'], data['name'], data['description'], [], data['social'], data['academic'], data['happiness'], data['health']) # no answer
        else: # game
            puzzle = Puzzle(data['idx'], data['name'], data['description'], [], 0, 0, 0, 0) # combination of both above
        puzzles[p_idx] = puzzle

    set_progress(puzzles, str(user_id))
    return puzzles

def get_options_keyboard(data, user_id):
    if user_id not in data: data[user_id] = load_data_from_csv(user_id)
    puzzles = data[user_id]

    titles = [f'{c.name} ✅' if c.is_completed else c.name for c in puzzles.values()]
    keys = puzzles.keys()

    # Exactly 18 options so make it 6x3
    keyboard = [[InlineKeyboardButton(t, callback_data=k)] for t, k in zip(titles, keys)]
    keyboard = [keyboard[3*i]+keyboard[3*i+1]+keyboard[3*i+2] for i in range(6)]

    return InlineKeyboardMarkup(keyboard)

def save_user_progress(user_id, context):
    user_data_str = read_dp(user_id)

    if user_data_str:
        user_progress = loads(user_data_str)['progress']
        user_soc = loads(user_data_str)['social']
        user_acad = loads(user_data_str)['academic']
        user_hap = loads(user_data_str)['happiness']
        user_hlth = loads(user_data_str)['health']
        user_forf = loads(user_data_str)['forfeits']
    else:
        user_progress = list()
        user_soc = 3
        user_acad = 3
        user_hap = 3
        user_hlth = 3
        user_forf = dict()

    user_progress.append(context.user_data['cur_puzzle_idx'])

    user_name = context.user_data['username']
    user_data_str = dumps({
            'username': user_name,
            'progress': user_progress,
            'social': str(user_soc),
            'academic': str(user_acad),
            'happiness': str(user_hap),
            'health': str(user_hlth),
            'forfeits': user_forf
            }, indent=2)
    write_dp(user_id, user_data_str)

def send_description(description, chat_id, bot):
    for d_filename in description:
        d_filename = path.join(DATA_DIR, d_filename)

        # Will always use .txt format
        d_txt = open(d_filename).read()
        bot_message = bot.send_message(
            chat_id=chat_id,
            # Bold the text to separate from other texts.
            text=f'<b>{d_txt}</b>',
            parse_mode='HTML'
        )

    return bot_message