import config
from spreadsheet import Spreadsheet

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



labyrinth_sheet = Spreadsheet('creds.json')
labyrinth_sheet.setSpreadsheetById(config.labirint_id)

info_sheet = Spreadsheet('creds.json')
info_sheet.setSpreadsheetById(config.info_id)

field = labyrinth_sheet.get_info_from_sheet(0, 0, 11, 11)
arproblems = info_sheet.get_info_from_sheet(1, 0, 7, 7)
arreactions = info_sheet.get_info_from_sheet(13, 0, 30, 2)

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

