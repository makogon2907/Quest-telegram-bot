import game
import storage
from exceptions import *

import logging

from aiogram import Bot, Dispatcher, executor, types

import config

API_TOKEN = config.TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

host = game.GameHost()


@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
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

    markup.row(item0, item1, item2)
    markup.row(item3, item4, item5)
    markup.row(item6, item7, item8)

    # проверка на читерство
    if host.players.get(message.from_user.id):
        print(message.from_user.first_name, message.from_user.last_name, ' попытался считерить)')

        await bot.send_message(message.from_user.id,
                               'Кажется, вы уже регестрировались в базе, регестрироваться заново нечестно)' \
                               + host.get_current_position(message.from_user.id))


    else:
        print(message.from_user.first_name, message.from_user.last_name, ' присоединился к игре лабиринт')

        host.register(message.from_user.id)

        sti = open('static/welcome.webp', 'rb')
        await bot.send_sticker(message.from_user.id, sti)
        await bot.send_message(message.from_user.id,
                               "Добро пожаловать, {0.first_name}!\nЯ - <b>{1.first_name}</b>. Читай историю ниже и... вперед!".format(
                                   message.from_user, await bot.get_me()),
                               parse_mode='html', reply_markup=markup)

        await bot.send_message(message.from_user.id, storage.intro)
        await bot.send_message(message.from_user.id, storage.info.format(
            storage.warn),
                               parse_mode='html', reply_markup=markup
                               )

        await bot.send_message(message.from_user.id, host.get_current_position(message.from_user.id),
                               reply_markup=markup)


@dp.callback_query_handler(text="confirm")
async def confirmation(call: types.CallbackQuery):
    answer, keyboard = host.accept_confirmation(call.from_user.id)
    await bot.send_message(call.from_user.id, answer)
    await call.message.edit_reply_markup()


@dp.callback_query_handler(text="reject")
async def rejection(call: types.CallbackQuery):
    answer, keyboard = host.reject_confirmation(call.from_user.id)
    await bot.send_message(call.from_user.id, answer)
    await call.message.edit_reply_markup()


@dp.message_handler(content_types=['text'])
async def answer(message: types.Message):
    if message.chat.type == 'private':
        try:
            answer, keyboard = host.make_action(message.from_user.id, message.text)

            if keyboard.defined:
                markup = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(keyboard.buttons[0], callback_data='confirm'),
                            types.InlineKeyboardButton(keyboard.buttons[1], callback_data='reject')
                        ]
                    ]
                )
                await bot.send_message(message.from_user.id, answer, reply_markup=markup)
            else:
                await bot.send_message(message.from_user.id, answer)

        except GameNotStarted:
            await bot.send_message(message.from_user.id, 'Вы почему-то не зарегестрированы в базе, '
                                                         'нажмите на /start, '
                                                         'тогда вы попадете в базу тех, кто ходит по лабиринту')


# RUN
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
