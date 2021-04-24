import telebot
import config
import random
from telebot import types
import time
import game
import storage

bot = telebot.TeleBot(config.TOKEN)

# telebot.apihelper.proxy = {'https':'socks5://127.0.0.1:9150'}

goleft = '⬅'
goright = '➡'
goup = '⬆'
godown = '⬇'

whereIsSheet = 'где увидеть поле?'
whereIAm = 'где я?'

from config import myID

print('Я Quest Bot и я успешно запустился!')


@bot.message_handler(commands=['start'])
def welcome(message):
    # keyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=False)

    item0 = types.KeyboardButton(whereIsSheet)
    item1 = types.KeyboardButton(goup)
    item2 = types.KeyboardButton('.')
    item3 = types.KeyboardButton(goleft)
    item4 = types.KeyboardButton(whereIAm)
    item5 = types.KeyboardButton(goright)
    item6 = types.KeyboardButton('.')
    item7 = types.KeyboardButton(godown)
    item8 = types.KeyboardButton('.')

    markup.add(item0, item1, item2)
    markup.add(item3, item4, item5)
    markup.add(item6, item7, item8)

    # проверка на читерство
    if game.position.get(message.from_user.id):
        print(message.from_user.first_name, message.from_user.last_name, ' попытался считерить)')

        curtextpos = game.getCharFromField(game.position[message.from_user.id])

        bot.send_message(message.chat.id, 'Кажется, вы уже регестрировались в базе, регестрироваться заново нечестно)'
                                          ' вы сейчас находитесь в клетке < ' + curtextpos + ' >, '
                                                                                             'продолжайте исследование!)')


    else:
        print(message.from_user.first_name, message.from_user.last_name, ' присоединился к игре лабиринт')

        game.position[message.from_user.id] = game.startPosition
        game.closed[message.from_user.id] = []
        game.succsesSolved[message.from_user.id] = []
        if game.solving.get(message.from_user.id):
            game.solving.pop(message.from_user.id)

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

        # bot.send_message(message.chat.id, storage.greeting)

        # game.namelist[message.from_user.id] = message.from_user.first_name + ' ' + message.from_user.last_name

        beginq = game.getCharFromField(game.startPosition)

        bot.send_message(message.chat.id,
                         'Вы находитесь на клетке < ' + beginq + ' > , продолжайте исследовать лабиринт'
                                                                 ' и находить что-то интересное')


def addar(a, b):
    return [a[0] + b[0], a[1] + b[1]]


@bot.message_handler(commands=['getstats'])
def answer(message):
    if not message.from_user.id == myID:
        return
    ans = ''
    for key, value in game.problems.items():
        ans += key + ' '
        ans += str(value.solved) + '/'
        ans += str(value.tried) + '\n'

    bot.send_message(myID, ans)


@bot.message_handler(commands=['getlist'])
def answer(message):
    if not message.from_user.id == myID:
        return
    ans = 'Участники квеста в базе: \n'
    for key, value in game.namelist.items():
        ans += value + '\n'

    bot.send_message(myID, ans)


@bot.message_handler(content_types=['text'])
def answer(message):
    if message.chat.type == 'private':

        if message.from_user.id == myID and message.text == 'перезапустись':
            game.solving.clear()
            game.position.clear()
            game.closed.clear()
            game.succsesSolved.clear()
            game.namelist.clear()

            for key, value in game.problems.items():
                game.problems[key].tried = 0
                game.problems[key].solved = 0
            bot.send_message(message.chat.id, 'перезапуск успешно завершился')
            print('Артем сбросил базу данных бота')
            return

        print(message.from_user.first_name, message.from_user.last_name, message.text)

        if not game.position.get(message.from_user.id):
            bot.send_message(message.chat.id, 'Вы почему-то не зарегестрированы в базе, '
                                              'нажмите на /start, '
                                              'тогда вы попадете в базу тех, кто ходит по лабиринту')
            return

        if message.text == whereIsSheet:
            bot.send_message(message.chat.id, 'Вот ссылка на лабиринт, если вы вдруг потеряли: '
                             + storage.linkToField)
            return

        if message.text == whereIAm:
            ans = game.getCharFromField(game.position[message.chat.id])

            bot.send_message(message.chat.id, 'Вы сейчас безопасно стоите на клетке < '
                             + ans + ' > , продолжайте исследование!)')
            return

        print(game.getCharFromField(game.position[message.from_user.id]))

        if game.solving.get(message.from_user.id):

            if message.text == goright or message.text == goleft or message.text == goup or message.text == godown:
                bot.send_message(message.chat.id, 'Никуда не уходите, решайте загадку...'
                                                  ' Следующее ваше сообщение будет засчитано как ответ!')
                return

            attempt = game.solving[message.from_user.id]  # [name of problem, last position]
            game.solving.pop(message.from_user.id)

            curProblem = game.problems[attempt[0]]
            lastPosition = attempt[1]

            if ((curProblem.answer in message.text.strip().lower()) and curProblem.answer != '1000') \
                    or (curProblem.answer == message.text.strip().lower()):
                game.problems[attempt[0]].tried += 1
                game.problems[attempt[0]].solved += 1

                bot.send_message(message.chat.id, curProblem.correct)
                game.succsesSolved[message.from_user.id].append(attempt[0])
                bot.send_message(message.chat.id, 'Вы сейчас безопасно стоите на клетке < ' + attempt[0] + ' > , '
                                                                                                           'продолжайте исследование)')
                return

            game.problems[attempt[0]].tried += 1
            bot.send_message(message.chat.id, curProblem.incorrect)

            if curProblem.reusable == 0:
                ##### пометка закрытости навсегда
                game.closed[message.from_user.id].append(attempt[0])
                #####
                bot.send_message(message.chat.id,
                                 'Вы перешли в клетку ' + game.getCharFromField(lastPosition))
                game.position[message.from_user.id] = lastPosition

            if curProblem.reusable == 1:
                bot.send_message(message.chat.id,
                                 'Вы перешли в клетку ' + game.getCharFromField(lastPosition))
                game.position[message.from_user.id] = lastPosition

            if curProblem.reusable == 2:
                game.succsesSolved[message.from_user.id].append(attempt[0])
                bot.send_message(message.chat.id, 'Вы сейчас безопасно стоите на клетке < ' + attempt[0] + ' > , '
                                                                                                           'продолжайте исследование)')

            return

        curpos = game.position[message.from_user.id]
        pos = curpos

        if message.text == goup:
            pos = addar(curpos, [-1, 0])
        elif message.text == godown:
            pos = addar(curpos, [1, 0])
        elif message.text == goleft:
            pos = addar(curpos, [0, -1])
        elif message.text == goright:
            pos = addar(curpos, [0, 1])
        else:
            bot.send_message(message.chat.id, 'Я пока не умею обрабатывать такие команды((')
            return

        textcell = game.getCharFromField(pos)

        if textcell == '#' or textcell in game.closed[message.from_user.id]:
            bot.send_message(message.chat.id, 'Ой, вы попробовали наступить на стену, не делайте так, прохода нет)')

            closear = game.closed[message.from_user.id]

            if len(closear) > 0:
                reply = 'Напоминаю, что для вас закрыты следующие клетки:'
                for item in closear:
                    reply += '\n' + item
                bot.send_message(message.chat.id, reply)

            return

        game.position[message.from_user.id] = pos

        if textcell in game.succsesSolved[message.from_user.id]:
            bot.send_message(message.chat.id,
                             'Вы уже деактивировали эту загадку, опасности нет, можете спокойно проходить дальше')
        elif game.problems.get(textcell):
            curProblem = game.problems[textcell]

            game.solving[message.from_user.id] = [textcell, curpos]  # [лейбл пробелмы, предыдущая позиция]

            bot.send_message(message.chat.id, 'Вы наступили на  < ' + textcell + ' >, будьте внимательны')
            bot.send_message(message.chat.id, curProblem.beforeproblem)
            bot.send_message(message.chat.id, curProblem.text)
            bot.send_message(message.chat.id,
                             'Внимание! Следующее ваше сообщение будет засчитано как ответ на эту загадку!')
            return

        if game.reactions.get(textcell):
            bot.send_message(message.chat.id, game.reactions[textcell])

        if pos == game.teleportposition:
            bot.send_message(message.chat.id, 'Ого, вы телепортировались в секретную комнату,'
                                              ' исследуйте дальше\n Вы наступили на клетку < :) >')
            game.position[message.from_user.id] = game.finishteleport
            return

        if pos == game.backteleport:
            textcell = game.getCharFromField(game.teleportposition)
            bot.send_message(message.chat.id, 'Вы вышли из тайной комнаты)'
                                              ' Понравилось?\n Вы наступили на клетку < ' + textcell + '> , продолжайте исследование')
            game.position[message.from_user.id] = game.teleportposition
            return

        bot.send_message(message.chat.id, 'Вы наступили на клетку < ' + textcell + ' > ,'
                                                                                   ' продолжайте исследование!')


# RUN
bot.polling(none_stop=True)
