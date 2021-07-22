from cmd_base import Activity, get_options_keyboard, save_user_progress, send_description, DATA_DIR
from json import load, loads, dumps
from os import path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from dpad_manager import read_dp, write_dp

CHOOSE_ACTIVITY, CHOOSE_OPTION, CHECK_ANSWER, CHOOSE_CONTINUE_OPTION = range(4)

DATA_DIR = path.join('.', 'bot_data')
DATA_PATH = path.join(DATA_DIR, 'forfeits.json')

with open(DATA_PATH, 'r') as f:
    forfeit_data = load(f)

def forfeits(data, social, academic, happiness, health):
    # type(data) = dict, stores how many forfeits you have encountered before
    result = []

    if (social <= 0 and data.get('social',0) == 0) or (social <= -1 and data.get('social',0) == 1):
        result.append('social')
    if (academic <= 0 and data.get('academic',0) == 0) or (academic <= -1 and data.get('academic',0) == 1):
        result.append('academic')
    if (happiness <= 0 and data.get('happiness',0) == 0) or (happiness <= -1 and data.get('happiness',0) == 1):
        result.append('happiness')
    if (health <= 0 and data.get('health',0) == 0) or (health <= -1 and data.get('health',0) == 1):
        result.append('health')

    return result

def sgn(x):
    return '+'+str(x) if x > 0 else str(x)

def show_activities_menu(update, context):
    msg = update.message
    user_id = msg.from_user.id

    reply_markup = get_options_keyboard(context.chat_data, user_id)
    msg.reply_text('Choose an activity to view ...', reply_markup=reply_markup)

    return CHOOSE_ACTIVITY

def choose_activity(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    query.answer()

    # This can be 'back' in some occassions but we'll see :)
    activity_idx = query.data

    activities = context.chat_data[user_id]
    context.user_data['cur_activity_idx'] = activity_idx
    context.user_data['username'] = update.effective_user.username

    # We need to check whether we have completed all activities before the selected activity
    user_data_str = read_dp(str(user_id))
    if user_data_str:
        user_progress = loads(user_data_str)['progress']
    else:
        user_progress = list()

    bot = context.bot
    try:
        idx = activities[activity_idx].idx
    except:
        # Just return them to the main menu
        return CHOOSE_ACTIVITY

    # Using the underlying data in bot_data.json
    id_num = int(idx[4:6])

    # We have completed all activities before the selected activity
    if len(user_progress) >= id_num - 1:
        name = activities[activity_idx].name
        description = activities[activity_idx].description
        is_completed = activities[activity_idx].is_completed

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

        txt = [f'Showing <b>{name}</b>.']
        # Update response for completed activity
        if is_completed:
            if 'T' in idx:
                first_answer = activities[activity_idx].answers[0]
                txt.append(f' You already completed this question! The answer was "{first_answer}".\n')
            else: # scenario or game
                txt.append(f' You already completed this activity!\n')

            keyboard = [
                [InlineKeyboardButton(text='Back to activities list 📃', callback_data='back')],
                [InlineKeyboardButton(text='Exit ✔️', callback_data='done')]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['last_description'] = send_description(description, user_id, bot)
        query.message.reply_text(text=''.join(txt), reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_OPTION
    else: # The activity is still locked
        reply_markup = get_options_keyboard(context.chat_data, user_id)
        try:
            query.edit_message_text('Activity still locked! Complete all previous activities first!', reply_markup=reply_markup)
        except:
            pass # unmodified message

        return CHOOSE_ACTIVITY

def return_to_activities_menu(update, context):
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

    return CHOOSE_ACTIVITY

def answer_activity(update, context):
    query = update.callback_query
    user_id = update.effective_user.id

    query.answer()

    activity_idx = context.user_data['cur_activity_idx']
    activities = context.chat_data[user_id]

    name = activities[activity_idx].name
    query.edit_message_text(text=f'Trying "{name}", type the answer')

    return CHECK_ANSWER

# This will only run if the activity is a trivia
def check_answer(update, context):
    user_id = update.message.from_user.id
    activities = context.chat_data[user_id]
    activity_idx = context.user_data['cur_activity_idx']
    user_name = context.user_data['username']

    right_answers = activities[activity_idx].answers
    # Caps lock everything
    user_answer = update.message.text.upper()

    keyboard = [
        [
            InlineKeyboardButton(text='Back to activities list 📃', callback_data='back'),
            InlineKeyboardButton(text='Exit ✔️', callback_data='done')
        ]
    ]

    if user_answer in right_answers:
        result = f'Right answer! Congratulations @{user_name}!'
        activities[activity_idx].is_completed = True
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
    activities = context.chat_data[user_id]
    activity_idx = context.user_data['cur_activity_idx']
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

    user_soc += activities[activity_idx].social[0]
    user_acad += activities[activity_idx].academic[0]
    user_hap += activities[activity_idx].happiness[0]
    user_hlth += activities[activity_idx].health[0]

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
            f'Social: <b>{sgn(activities[activity_idx].social[0])}</b>',
            f'Academic: <b>{sgn(activities[activity_idx].academic[0])}</b>',
            f'Happiness: <b>{sgn(activities[activity_idx].happiness[0])}</b>',
            f'Health: <b>{sgn(activities[activity_idx].health[0])}</b>\n',
            f'----------\n<b>{activities[activity_idx].information[0]}</b>\n----------',
            '\nYou can always check your current meter score with the /meter command.\n',
            '<b>WARNING: You are required to do a list of forfeit(s) as follows!</b>'
            ]

        for meter in forf: # for every meter that needs a forfeit
            user_forf[meter] = user_forf.get(meter,0) + 1
            result.append(f'❇️ <b>{meter.capitalize()}:</b> {forfeit_data[meter][user_forf[meter]-1]}')

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

        activities[activity_idx].is_completed = True
        user_progress.append(activity_idx)

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
            f'Social: <b>{sgn(activities[activity_idx].social[0])}</b>',
            f'Academic: <b>{sgn(activities[activity_idx].academic[0])}</b>',
            f'Happiness: <b>{sgn(activities[activity_idx].happiness[0])}</b>',
            f'Health: <b>{sgn(activities[activity_idx].health[0])}</b>\n',
            f'----------\n<b>{activities[activity_idx].information[0]}</b>\n----------',
            '\nYou can always check your current meter score with the /meter command.'
            ]

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_CONTINUE_OPTION

def no(update, context):
    user_id = update['callback_query'].from_user['id']
    activities = context.chat_data[user_id]
    activity_idx = context.user_data['cur_activity_idx']
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

    user_soc += activities[activity_idx].social[1]
    user_acad += activities[activity_idx].academic[1]
    user_hap += activities[activity_idx].happiness[1]
    user_hlth += activities[activity_idx].health[1]

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
            f'Social: <b>{sgn(activities[activity_idx].social[1])}</b>',
            f'Academic: <b>{sgn(activities[activity_idx].academic[1])}</b>',
            f'Happiness: <b>{sgn(activities[activity_idx].happiness[1])}</b>',
            f'Health: <b>{sgn(activities[activity_idx].health[1])}</b>\n',
            f'----------\n<b>{activities[activity_idx].information[1]}</b>\n----------',
            '\nYou can always check your current meter score with the /meter command.\n',
            '<b>WARNING: You are required to do a list of forfeit(s) as follows!</b>'
            ]

        for meter in forf: # for every meter that needs a forfeit
            user_forf[meter] = user_forf.get(meter,0) + 1
            result.append(f'❇️ <b>{meter.capitalize()}:</b> {forfeit_data[meter][user_forf[meter]-1]}')

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

        activities[activity_idx].is_completed = True
        user_progress.append(activity_idx)

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
            f'Social: <b>{sgn(activities[activity_idx].social[1])}</b>',
            f'Academic: <b>{sgn(activities[activity_idx].academic[1])}</b>',
            f'Happiness: <b>{sgn(activities[activity_idx].happiness[1])}</b>',
            f'Health: <b>{sgn(activities[activity_idx].health[1])}</b>\n',
            f'----------\n<b>{activities[activity_idx].information[1]}</b>\n----------',
            '\nYou can always check your current meter score with the /meter command.'
            ]

        result = '\n'.join(result)
        query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')

        return CHOOSE_CONTINUE_OPTION

def complete(update, context):
    user_id = update.effective_user.id
    activities = context.chat_data[user_id]
    activity_idx = context.user_data['cur_activity_idx']
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

    activities[activity_idx].is_completed = True
    user_progress.append(activity_idx)

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

def leave_activities_menu(update, context):
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

activities_menu = ConversationHandler(
    entry_points=[CommandHandler('activities', show_activities_menu)],
    states={
        CHOOSE_ACTIVITY: [
            CallbackQueryHandler(choose_activity)
        ],
        CHOOSE_OPTION: [
            CallbackQueryHandler(answer_activity, pattern='^try$'),
            CallbackQueryHandler(return_to_activities_menu, pattern='^back$'),
            CallbackQueryHandler(yes, pattern='^yes$'),
            CallbackQueryHandler(no, pattern='^no$'),
            CallbackQueryHandler(complete, pattern='^complete$')
        ],
        CHECK_ANSWER: [
            MessageHandler(~Filters.regex('^/'), check_answer)
        ],
        CHOOSE_CONTINUE_OPTION: [
            CallbackQueryHandler(return_to_activities_menu, pattern='^back$'),
            CallbackQueryHandler(try_again, pattern='^try_again$')
        ]
    },
    fallbacks=[CallbackQueryHandler(leave_activities_menu, pattern='^done$')]
)