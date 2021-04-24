from pprint import pprint

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials


class Problem:
    def __init__(self, beforeproblem, text, answer, correct, incorrect, reusable):
        self.beforeproblem = beforeproblem
        self.text = text
        self.answer = answer
        self.correct = correct
        self.incorrect = incorrect
        self.reusable = int(reusable)
        self.solved = 0
        self.tried = 0


# Файл, полученный в Google Developer Console
CREDENTIALS_FILE = 'creds.json'

# ID Google Sheets документа (можно взять из его URL)

from config import labirint_id
from config import info_id

# Авторизуемся и получаем service — экземпляр доступа к API
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http = httpAuth)

# Пример чтения файла
field = service.spreadsheets().values().get(
    spreadsheetId=labirint_id,
    range='A1:J11',
    majorDimension='ROWS'
).execute()['values']

arproblems = service.spreadsheets().values().get(
    spreadsheetId=info_id,
    range='A2:G7',
    majorDimension='ROWS'
).execute()['values']

arreactions = service.spreadsheets().values().get(
    spreadsheetId=info_id,
    range='A14:B30',
    majorDimension='ROWS'
).execute()['values']

namelist = dict()
problems = dict()
position = dict()
solving = dict()
closed = dict()
succsesSolved = dict()
reactions = dict()

startPosition = [0, 0]
finishPosition = [0, 0]
teleportposition = [0, 0]
backteleport = [0, 0]
finishteleport = [0, 0]

#TODO Осторожно, ниже много костылей

for i in range(len(field)):
    for j in range(len(field[i])):
        if field[i][j] == 'вход':
            startPosition = [i, j]
        if field[i][j] == 'выход':
            finishPosition = [i, j]
        if field[i][j] == '(0; 5)':
            teleportposition = [i, j]
        if field[i][j] == ':)':
            finishteleport = [i, j]
        if field[i][j] == 'приз':
            backteleport = [i, j]


for cur in arproblems:
    toadd = Problem(cur[1], cur[2], cur[3], cur[4], cur[5], cur[6])
    problems[cur[0]] = toadd

for cur in arreactions:
    if len(cur) == 2:
        reactions[cur[0]] = cur[1]

def getCharFromField(pos):
    return field[pos[0]][pos[1]]


# for i in range(len(field)):
#     for j in range(len(field[i])):
#         if field[i][j] == 'o' or field[i][j] == 'о':
#             field[i][j] = chr(ord('a') + random.randint(0, 25))

# Пример записи в файл

# values = service.spreadsheets().values().batchUpdate(
#     spreadsheetId=spreadsheet_id,
#     body={
#         "valueInputOption": "USER_ENTERED",
#         "data": [
#             {"range": 'A18:A18',
#              "majorDimension": "COLUMNS",
#              "values": [["This information is written by Artem's bot"]]}
# 	    ]
#     }
# ).execute()

# values = service.spreadsheets().values().batchUpdate(
#     spreadsheetId=spreadsheet_id,
#     body={
#         "valueInputOption": "USER_ENTERED",
#         "data": [
#             {"range": 'A18:H27',
#              "majorDimension": "COLUMNS",
#              "values": values}
# 	    ]
#     }
# ).execute()