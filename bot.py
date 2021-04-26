import telebot
import config
import random
from telebot import types
import time
import game
import storage
from exceptions import *

bot = telebot.TeleBot(config.TOKEN)

# telebot.apihelper.proxy = {'https':'socks5://127.0.0.1:9150'}


from config import myID

print('Я Quest Bot и я успешно запустился!')

host = game.GameHost()

@bot.message_handler(commands=['start'])
def welcome(message):
    # keyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=False)

    item0 = types.KeyboardButton(host.prepared_reactions.whereIsSheet)
    item1 = types.KeyboardButton(host.prepared_reactions.goup)
    item2 = types.KeyboardButton('.')
    item3 = types.KeyboardButton(host.prepared_reactions.goleft)
    item4 = types.KeyboardButton(host.prepared_reactions.whereIAm)
    item5 = types.KeyboardButton(host.prepared_reactions.goright)
    item6 = types.KeyboardButton('.')
    item7 = types.KeyboardButton(host.prepared_reactions.godown)
    item8 = types.KeyboardButton('.')

    markup.add(item0, item1, item2)
    markup.add(item3, item4, item5)
    markup.add(item6, item7, item8)

    # проверка на читерство
    if host.players.get(message.from_user.id):
        print(message.from_user.first_name, message.from_user.last_name, ' попытался считерить)')

        bot.send_message(message.chat.id, 'Кажется, вы уже регестрировались в базе, регестрироваться заново нечестно)'\
                                          + host.get_current_position(message.from_user.id))


    else:
        print(message.from_user.first_name, message.from_user.last_name, ' присоединился к игре лабиринт')

        host.register(message.from_user.id)

        sti = open('static/welcome.webp', 'rb')
        bot.send_sticker(message.chat.id, sti)
        bot.send_message(message.chat.id,
                         "Добро пожаловать, {0.first_name}!\nЯ - <b>{1.first_name}</b>. Читай историю ниже и... вперед!".format(
                             message.from_user, bot.get_me()),
                         parse_mode='html', reply_markup=markup)

        bot.send_message(message.chat.id, storage.intro)
        bot.send_message(message.chat.id, storage.info.format(
            storage.warn),
                         parse_mode='html', reply_markup=markup
                         )

        bot.send_message(message.chat.id, host.get_current_position(message.from_user.id))



@bot.message_handler(content_types=['text'])
def answer(message):
    if message.chat.type == 'private':
        try:
            answer, keyboard = host.make_action(message.from_user.id, message.text)
            bot.send_message(message.chat.id, answer)

        except GameNotStarted:
            bot.send_message(message.chat.id, 'Вы почему-то не зарегестрированы в базе, '
            'нажмите на /start, '
            'тогда вы попадете в базу тех, кто ходит по лабиринту')


# RUN
bot.polling(none_stop=True)
