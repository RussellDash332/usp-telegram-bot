from activities_menu import activities_menu
from env import TOKEN
from os import path
from telegram.ext import Updater, CommandHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from json import load, loads
from dpad_manager import read_dp

def start(update, context):
    welcome_txt = [
        'Dummy text',
        ]

    update.message.reply_text('\n'.join(welcome_txt))

def meter(update, context):
    msg = update.message
    user_id = msg.from_user.id

    user_data_str = read_dp(str(user_id))

    if user_data_str:
        social = loads(user_data_str)['social']
        academic = loads(user_data_str)['academic']
        happiness = loads(user_data_str)['happiness']
        health = loads(user_data_str)['health']
    else:
        social = 3
        academic = 3
        happiness = 3
        health = 3

    rep = [
        f'Social: {social}',
        f'Academic: {academic}',
        f'Happiness: {happiness}',
        f'Health: {health}'
        ]
    
    # bold everything
    rep = list(map(lambda x: f'<b>{x}</b>', rep))

    update.message.reply_text('\n'.join(rep), parse_mode='HTML')

def main(request):
    updater = Updater(token=TOKEN, use_context=True)

    if request.method == 'POST':
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("meter", meter))
        dp.add_handler(activities_menu)

        updater.start_polling()
        # print("++++++++++ STARTING BOT +++++++++++")
        # updater.idle()
        # print("++++++++++  KILLING BOT  ++++++++++")

    return "OK"