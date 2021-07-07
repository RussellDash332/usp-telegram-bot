from puzzles_menu import puzzles_menu
from env import TOKEN
from os import path
from telegram.ext import Updater, CommandHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from json import load, loads
from dpad_manager import read_dp

def start(update, context):
    welcome_txt = [
        'Welcome to USP: The Game Of Life!\n',
        'There will be 6 stations that revolve around 4 key aspects of mental wellness, namely academics, social, happiness, health (we will call these meters).',
        'Each group will start off with 12 points, with 3 points in each meter.',
        'Points will serve a measure for the current meter level for each aspect.',
        'With a +, you get one more point and with a -, you need to give up one of the points.',
        'The aim of the game is to maintain a good balance of all 4 aspects as the group moves through the 6 stations.\n',
        'You can check your meter levels anytime with the /meter command.'
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

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("meter", meter))
    dp.add_handler(puzzles_menu)

    updater.start_polling()
    print("++++++++++ STARTING BOT +++++++++++")
    updater.idle()
    print("++++++++++  KILLING BOT  ++++++++++")


if __name__ == '__main__':
    print("Press CTRL + C to kill the bot")
    main()