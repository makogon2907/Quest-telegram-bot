from aiogram import types
from game import PreparedReactions

reactions = PreparedReactions()

default_markup = types.ReplyKeyboardMarkup(resize_keyboard=False)

item0 = types.KeyboardButton(reactions.whereIsSheet)
item1 = types.KeyboardButton(reactions.goup)
item2 = types.KeyboardButton('.')
item3 = types.KeyboardButton(reactions.goleft)
item4 = types.KeyboardButton(reactions.whereIAm)
item5 = types.KeyboardButton(reactions.goright)
item6 = types.KeyboardButton('.')
item7 = types.KeyboardButton(reactions.godown)
item8 = types.KeyboardButton('.')

default_markup.row(item0, item1, item2)
default_markup.row(item3, item4, item5)
default_markup.row(item6, item7, item8)