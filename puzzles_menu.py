from cmd_base import Puzzle, get_options_keyboard, save_user_progress, send_description, DATA_DIR
from json import load, loads, dumps
from os import path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from dpad_manager import read_dp, write_dp

CHOOSE_PUZZLE, CHOOSE_OPTION, CHECK_ANSWER, CHOOSE_CONTINUE_OPTION = range(4)

DATA_DIR = path.join('.', 'bot_data')
DATA_PATH = path.join(DATA_DIR, 'forfeits.json')

with open(DATA_PATH, 'r') as f:
    forfeit_data = load(f)

def forfeits(data, social, academic, happiness, health):
    # type(data) = dict, stores how many forfeits you have encountered before
    result = []

    if (social <= 2 and data.get('social',0) == 0) or (social <= 3 and data.get('social',0) >= 1):
        result.append('social')
    if (academic <= 2 and data.get('academic',0) == 0) or (academic <= 3 and data.get('academic',0) >= 1):
        result.append('academic')
    if (happiness <= 2 and data.get('happiness',0) == 0) or (happiness <= 3 and data.get('happiness',0) >= 1):
        result.append('happiness')
    if (health <= 2 and data.get('health',0) == 0) or (health <= 3 and data.get('health',0) >= 1):
        result.append('health')

    return result

def sgn(x):
    return '+'+str(x) if x > 0 else str(x)

def show_puzzles_menu(update, context):
    msg = update.message
    user_id = msg.from_user.id

    reply_markup = get_options_keyboard(context.chat_data, user_id)
    msg.reply_text('Choose an activity to view ...', reply_markup=reply_markup)

    return CHOOSE_PUZZLE

def choose_puzzle(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    query.answer()

    # This can be 'back' in some occassions but we'll see :)
    puzzle_idx = query.data

    puzzles = context.chat_data[user_id]
    context.user_data['cur_puzzle_idx'] = puzzle_idx
    context.user_data['username'] = update.effective_user.username

    # We need to check whether we have completed all activities before the selected activity
    user_data_str = read_dp(str(user_id))
    if user_data_str:
        user_progress = loads(user_data_str)['progress']
    else:
        user_progress = list()

    bot = context.bot
    idx = puzzles[puzzle_idx].idx

    # Using the underlying data in bot_data.json
    id_num = int(idx[4:6])

    # We have completed all activities before the selected activity
    if len(user_progress) >= id_num - 1:
        name = puzzles[puzzle_idx].name
        description = puzzles[puzzle_idx].description
        is_completed = puzzles[puzzle_idx].is_completed

        bot.delete_message(chat_id=user_id, message_id=query.message.message_id)

        if 'T' in idx: # trivia
            keyboard = [
                [
                    InlineKeyboardButton(text='Try this question 🧩', callback_data='try')
                ],
                [
                    InlineKeyboardButton(text='Exit ✔️', callback_data='done')
                ]
            ]
        elif 'S' in idx: # scenario
            keyboard = [
                [
                    InlineKeyboardButton(text='Yes', callback_data='yes'),
                    InlineKeyboardButton(text='No', callback_data='no')
                ],
                [
                    InlineKeyboardButton(text='Exit ✔️', callback_data='done')
                ]
            ]
        else: # game
            keyboard = [
                [
                    InlineKeyboardButton(text="I'm done! ✔️", callback_data='complete')
                ]
            ]

        txt = [f'Showing {name}.']
        # Update response for completed puzzle
        if is_completed:
            if 'T' in idx:
                first_answer = puzzles[puzzle_idx].answers[0]
                txt.append(f' You already completed this question! The answer was "{first_answer}".\n')
            else: # scenario or game
                txt.append(f' You already completed this activity!\n')

            keyboard = [
                [InlineKeyboardButton(text='Back to activities list 📃', callback_data='back')],
                [InlineKeyboardButton(text='Exit ✔️', callback_data='done')]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['last_description'] = send_description(description, user_id, bot)
        query.message.reply_text(text=''.join(txt), reply_markup=reply_markup)

        return CHOOSE_OPTION
    else: # The activity is still locked
        reply_markup = get_options_keyboard(context.chat_data, user_id)
        try:
            query.edit_message_text('Activity still locked! Complete all previous activities first!', reply_markup=reply_markup)
        except:
            pass # unmodified message

        return CHOOSE_PUZZLE

def return_to_puzzles_menu(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    query.answer()
    bot = context.bot

    try:
        last_description = context.user_data['last_description']
        bot.delete_message(chat_id=user_id, message_id=last_description.message_id)
    except:
        pass
    bot.delete_message(chat_id=user_id, message_id=query.message.message_id)

    reply_markup = get_options_keyboard(context.chat_data, user_id)
    query.message.reply_text('Choose an activity to view...', reply_markup=reply_markup)

    return CHOOSE_PUZZLE

def answer_puzzle(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    query.answer()

    puzzle_idx = context.user_data['cur_puzzle_idx']
    puzzles = context.chat_data[user_id]

    name = puzzles[puzzle_idx].name
    query.edit_message_text(text=f'Trying "{name}", type the answer')

    return CHECK_ANSWER

# This will only run if the activity is a trivia
def check_answer(update, context):
    user_id = update.message.from_user.id
    puzzles = context.chat_data[user_id]
    puzzle_idx = context.user_data['cur_puzzle_idx']
    user_name = context.user_data['username']

    right_answers = puzzles[puzzle_idx].answers
    user_answer = update.message.text

    keyboard = [
        [
            InlineKeyboardButton(text='Back to activities list 📃', callback_data='back'),
            InlineKeyboardButton(text='Exit ✔️', callback_data='done')
        ]
    ]

    if user_answer in right_answers:
        result = f'Right answer! Congratulations @{user_name}!'
        puzzles[puzzle_idx].is_completed = True
        save_user_progress(str(user_id), context)
    else:
        keyboard.insert(0, [InlineKeyboardButton(text='Try again 🔄', callback_data='try_again')])
        # keyboard[1].pop(0)
        result = 'Wrong answer, want to try again?'

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(result, reply_markup=reply_markup)

    return CHOOSE_CONTINUE_OPTION

def yes(update, context):
    user_id = update['callback_query'].from_user['id']
    puzzles = context.chat_data[user_id]
    puzzle_idx = context.user_data['cur_puzzle_idx']
    user_name = update['callback_query'].from_user['username']

    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton(text='Back to activities list 📃', callback_data='back'),
            InlineKeyboardButton(text='Exit ✔️', callback_data='done')
        ]
    ]

    user_data_str = read_dp(str(user_id))
    if user_data_str:
        user_progress = loads(user_data_str)['progress']
        user_soc = int(loads(user_data_str)['social'])
        user_acad = int(loads(user_data_str)['academic'])
        user_hap = int(loads(user_data_str)['happiness'])
        user_hlth = int(loads(user_data_str)['health'])
        user_forf = loads(user_data_str)['forfeits']
    else: # probably won't happpen, but just in case
        user_progress = list()
        user_soc = 3
        user_acad = 3
        user_hap = 3
        user_hlth = 3
        user_forf = dict()

    user_soc += puzzles[puzzle_idx].social[0]
    user_acad += puzzles[puzzle_idx].academic[0]
    user_hap += puzzles[puzzle_idx].happiness[0]
    user_hlth += puzzles[puzzle_idx].health[0]
    puzzles[puzzle_idx].is_completed = True
    user_progress.append(puzzle_idx)

    forfeit_keyboard = [
            [
                InlineKeyboardButton(text="I'm done! ✔️", callback_data='complete')
            ]
        ]

    forf = forfeits(user_forf, user_soc, user_acad, user_hap, user_hlth)

    # There is something to forfeit
    if forf:
        reply_markup = InlineKeyboardMarkup(forfeit_keyboard)
        result = [
            'You chose <b>"Yes"</b> for this scenario.\n',
            'Your choice affects your meter scores as follows:',
            f'Social: <b>{sgn(puzzles[puzzle_idx].social[0])}</b>',
            f'Academic: <b>{sgn(puzzles[puzzle_idx].academic[0])}</b>',
            f'Happiness: <b>{sgn(puzzles[puzzle_idx].happiness[0])}</b>',
            f'Health: <b>{sgn(puzzles[puzzle_idx].health[0])}</b>',
            '\nYou can always check your current meter score with the /meter command.\n',
            '<b>WARNING: You are required to do a list of forfeit(s) as follows!</b>'
            ]

        for meter in forf: # for every meter that needs a forfeit
            user_forf[meter] = user_forf.get(meter,0) + 1
            result.append(f'<b>❇️ {forfeit_data[meter][(user_forf[meter]-1) % len(forfeit_data[meter])]}</b>')

        user_data_str = dumps({
                'username': user_name,
                'progress': user_progress,
                'social': str(user_soc),
                'academic': str(user_acad),
                'happiness': str(user_hap),
                'health': str(user_hlth),
                'forfeits': user_forf
                }, indent=2)
        write_dp(str(user_id), user_data_str)

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_OPTION
    else: # Nothing to forfeit, proceed
        reply_markup = InlineKeyboardMarkup(keyboard)

        user_data_str = dumps({
                'username': user_name,
                'progress': user_progress,
                'social': str(user_soc),
                'academic': str(user_acad),
                'happiness': str(user_hap),
                'health': str(user_hlth),
                'forfeits': user_forf
                }, indent=2)
        write_dp(str(user_id), user_data_str)

        result = [
            'You chose <b>"Yes"</b> for this scenario.\n',
            'Your choice affects your meter scores as follows:',
            f'Social: <b>{sgn(puzzles[puzzle_idx].social[0])}</b>',
            f'Academic: <b>{sgn(puzzles[puzzle_idx].academic[0])}</b>',
            f'Happiness: <b>{sgn(puzzles[puzzle_idx].happiness[0])}</b>',
            f'Health: <b>{sgn(puzzles[puzzle_idx].health[0])}</b>',
            '\nYou can always check your current meter score with the /meter command.'
            ]

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_CONTINUE_OPTION

def no(update, context):
    user_id = update['callback_query'].from_user['id']
    puzzles = context.chat_data[user_id]
    puzzle_idx = context.user_data['cur_puzzle_idx']
    user_name = update['callback_query'].from_user['username']

    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton(text='Back to activities list 📃', callback_data='back'),
            InlineKeyboardButton(text='Exit ✔️', callback_data='done')
        ]
    ]

    user_data_str = read_dp(str(user_id))
    if user_data_str:
        user_progress = loads(user_data_str)['progress']
        user_soc = int(loads(user_data_str)['social'])
        user_acad = int(loads(user_data_str)['academic'])
        user_hap = int(loads(user_data_str)['happiness'])
        user_hlth = int(loads(user_data_str)['health'])
        user_forf = loads(user_data_str)['forfeits']
    else: # probably won't happpen, but just in case
        user_progress = list()
        user_soc = 3
        user_acad = 3
        user_hap = 3
        user_hlth = 3
        user_forf = dict()

    user_soc += puzzles[puzzle_idx].social[1]
    user_acad += puzzles[puzzle_idx].academic[1]
    user_hap += puzzles[puzzle_idx].happiness[1]
    user_hlth += puzzles[puzzle_idx].health[1]
    puzzles[puzzle_idx].is_completed = True
    user_progress.append(puzzle_idx)

    forfeit_keyboard = [
            [
                InlineKeyboardButton(text="I'm done! ✔️", callback_data='complete')
            ]
        ]

    forf = forfeits(user_forf, user_soc, user_acad, user_hap, user_hlth)

    # There is something to forfeit
    if forf:
        reply_markup = InlineKeyboardMarkup(forfeit_keyboard)
        result = [
            'You chose <b>"No"</b> for this scenario.\n',
            'Your choice affects your meter scores as follows:',
            f'Social: <b>{sgn(puzzles[puzzle_idx].social[1])}</b>',
            f'Academic: <b>{sgn(puzzles[puzzle_idx].academic[1])}</b>',
            f'Happiness: <b>{sgn(puzzles[puzzle_idx].happiness[1])}</b>',
            f'Health: <b>{sgn(puzzles[puzzle_idx].health[1])}</b>',
            '\nYou can always check your current meter score with the /meter command.\n',
            '<b>WARNING: You are required to do a list of forfeit(s) as follows!</b>'
            ]

        for meter in forf: # for every meter that needs a forfeit
            user_forf[meter] = user_forf.get(meter,0) + 1
            result.append(f'<b>❇️ {forfeit_data[meter][(user_forf[meter]-1) % len(forfeit_data[meter])]}</b>')

        user_data_str = dumps({
                'username': user_name,
                'progress': user_progress,
                'social': str(user_soc),
                'academic': str(user_acad),
                'happiness': str(user_hap),
                'health': str(user_hlth),
                'forfeits': user_forf
                }, indent=2)
        write_dp(str(user_id), user_data_str)

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_OPTION
    else: # Nothing to forfeit, proceed
        reply_markup = InlineKeyboardMarkup(keyboard)

        user_data_str = dumps({
                'username': user_name,
                'progress': user_progress,
                'social': str(user_soc),
                'academic': str(user_acad),
                'happiness': str(user_hap),
                'health': str(user_hlth),
                'forfeits': user_forf
                }, indent=2)
        write_dp(str(user_id), user_data_str)

        result = [
            'You chose <b>"No"</b> for this scenario.\n',
            'Your choice affects your meter scores as follows:',
            f'Social: <b>{sgn(puzzles[puzzle_idx].social[1])}</b>',
            f'Academic: <b>{sgn(puzzles[puzzle_idx].academic[1])}</b>',
            f'Happiness: <b>{sgn(puzzles[puzzle_idx].happiness[1])}</b>',
            f'Health: <b>{sgn(puzzles[puzzle_idx].health[1])}</b>',
            '\nYou can always check your current meter score with the /meter command.'
            ]

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_CONTINUE_OPTION

def complete(update, context):
    user_id = update.effective_user.id
    puzzles = context.chat_data[user_id]
    puzzle_idx = context.user_data['cur_puzzle_idx']
    user_name = update['callback_query'].from_user['username']

    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton(text='Back to activities list 📃', callback_data='back'),
            InlineKeyboardButton(text='Exit ✔️', callback_data='done')
        ]
    ]

    result = f'Good job on completing the activity, @{user_name}!'
    
    user_data_str = read_dp(str(user_id))
    if user_data_str:
        user_progress = loads(user_data_str)['progress']
        user_soc = int(loads(user_data_str)['social'])
        user_acad = int(loads(user_data_str)['academic'])
        user_hap = int(loads(user_data_str)['happiness'])
        user_hlth = int(loads(user_data_str)['health'])
        user_forf = loads(user_data_str)['forfeits']
    else: # probably won't happpen, but just in case
        user_progress = list()
        user_soc = 3
        user_acad = 3
        user_hap = 3
        user_hlth = 3
        user_forf = dict()

    puzzles[puzzle_idx].is_completed = True
    user_progress.append(puzzle_idx)

    user_data_str = dumps({
            'username': user_name,
            'progress': user_progress,
            'social': str(user_soc),
            'academic': str(user_acad),
            'happiness': str(user_hap),
            'health': str(user_hlth),
            'forfeits': user_forf,
            }, indent=2)
    write_dp(str(user_id), user_data_str)

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(result, reply_markup=reply_markup)

    return CHOOSE_CONTINUE_OPTION

def try_again(update, context):
    query = update.callback_query
    query.answer()

    query.edit_message_text('Trying question again, type the answer')

    return CHECK_ANSWER

def leave_puzzles_menu(update, context):
    query = update.callback_query
    query.answer()

    user_id = update.effective_user.id

    bot = context.bot
    try:
        last_description = context.user_data['last_description']
        bot.delete_message(chat_id=user_id, message_id=last_description.message_id)
    except:
        pass

    query.edit_message_text('Bye, see you later! 😊')
    return ConversationHandler.END

puzzles_menu = ConversationHandler(
    entry_points=[CommandHandler('activities', show_puzzles_menu)],
    states={
        CHOOSE_PUZZLE: [
            CallbackQueryHandler(choose_puzzle)
        ],
        CHOOSE_OPTION: [
            CallbackQueryHandler(answer_puzzle, pattern='^try$'),
            CallbackQueryHandler(return_to_puzzles_menu, pattern='^back$'),
            CallbackQueryHandler(yes, pattern='^yes$'),
            CallbackQueryHandler(no, pattern='^no$'),
            CallbackQueryHandler(complete, pattern='^complete$')
        ],
        CHECK_ANSWER: [
            MessageHandler(~Filters.regex('^/'), check_answer)
        ],
        CHOOSE_CONTINUE_OPTION: [
            CallbackQueryHandler(return_to_puzzles_menu, pattern='^back$'),
            CallbackQueryHandler(try_again, pattern='^try_again$')
        ]
    },
    fallbacks=[CallbackQueryHandler(leave_puzzles_menu, pattern='^done$')]
)