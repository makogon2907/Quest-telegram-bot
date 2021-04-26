import config
from spreadsheet import Spreadsheet
from exceptions import *
import storage


class Problem:
    def __init__(self, preamble='', text='', answer='',
                 reaction_for_correct_answer='', reactions_for_incorrect_answer='',
                 reusable_type=0):
        self.preamble = preamble
        self.text = text
        self.answer = answer
        self.reaction_for_correct_answer = reaction_for_correct_answer
        self.reactions_for_incorrect_answer = reactions_for_incorrect_answer
        self.reusable_type = int(reusable_type)
        self.solved = 0
        self.tried = 0
        self.position = (0, 0)


class ReplyKeyboard:
    def __init__(self, buttons=[], reply=True):
        self.reply = reply
        self.buttons = buttons
        self.defined = (len(buttons) > 0)


class SolvingSession:
    def __init__(self, problem=Problem()):
        self.problem = problem
        self.submited_answer = ''
        self.is_opened = False
        self.requires_confirm = False

    def submit(self, answer_text):
        self.submited_answer = answer_text
        self.requires_confirm = True

    def open_session(self, problem):
        self.problem = problem
        self.is_opened = True
        self.requires_confirm = False

    def close_session(self):
        self.is_opened = False
        self.requires_confirm = False

    def prepare_confirmation_message(self) -> (str, ReplyKeyboard):
        answer = 'Внимание, вы подтверждаете, что отправляете ответ <<' + self.submited_answer + '>> для проверки?'
        keyboard = ReplyKeyboard(['Да', 'Нет, ввести заново'])
        return answer, keyboard


class Student:
    def __init__(self, id: int):
        self.id = id
        self.position = (0, 0)
        self.solving_session = SolvingSession()
        self.solved_problems = set()
        self.blocked_cells = set()

    def move_to_new_position(self, new_position: (int, int)):
        self.position = new_position

    def confirm_submited_answer(self) -> str:
        correct = self.solving_session.problem.answer.strip().lower()
        submited = self.solving_session.submited_answer.strip().lower()
        cur_problem = self.solving_session.problem

        self.solving_session.close_session()

        if correct in submited and correct != '1000' or correct == submited:  # TODO заменить на метод у Problem
            self.move_to_new_position(cur_problem.position)
            self.solved_problems.add(cur_problem.position)
            return cur_problem.reaction_for_correct_answer
        elif cur_problem.reusable_type == 0:
            self.blocked_cells.add(cur_problem.position)
            return cur_problem.reactions_for_incorrect_answer
        elif cur_problem.reusable_type == 2:  # problem is automaticly passed regardless of the answer
            self.solved_problems.add(cur_problem.position)
            self.move_to_new_position(cur_problem.position)
            return cur_problem.reactions_for_incorrect_answer
        else:  # problem is reusable
            return cur_problem.reactions_for_incorrect_answer

    def open_solving_session(self, problem):
        self.solving_session.open_session(problem)


class PreparedReactions:
    def __init__(self):
        self.goleft = '⬅'
        self.goright = '➡'
        self.goup = '⬆'
        self.godown = '⬇'
        self.whereIsSheet = 'где увидеть поле?'
        self.whereIAm = 'где я?'
        self.ordinary_reactions = dict()

    def convert_reaction_to_delta_position(self, message) -> (bool, (int, int)):
        if message == self.goup:
            return True, (-1, 0)
        if message == self.godown:
            return True, (1, 0)
        if message == self.goleft:
            return True, (-1, 0)
        if message == self.goright:
            return True, (1, 0)

        return False, (0, 0)


def _add_delta_to_position(pos: (int, int), delta: (int, int)) -> (int, int):
    return (pos[0] + delta[0], pos[1] + delta[1])


class SpecialPositions:
    def __init__(self):
        self.startPosition = (0, 0)
        self.finishPosition = (0, 0)
        self.teleportposition = (0, 0)
        self.backteleport = (0, 0)
        self.finishteleport = (0, 0)


class GameHost:
    def __init__(self):
        self.players = dict()  # [id, Student]
        self.prepared_reactions = PreparedReactions()
        self.field = []
        self.special_positions = SpecialPositions()
        self.problems = dict()  # (problem_name, Problem())
        self.get_data()

    def get_data(self):
        labyrinth_sheet = Spreadsheet('creds.json')
        labyrinth_sheet.setSpreadsheetById(config.labirint_id)

        info_sheet = Spreadsheet('creds.json')
        info_sheet.setSpreadsheetById(config.info_id)

        self.field = labyrinth_sheet.get_info_from_sheet(0, 0, 11, 11)
        arproblems = info_sheet.get_info_from_sheet(1, 0, 7, 7)

        for cur in arproblems:
            self.problems[cur[0]] = Problem(cur[1], cur[2], cur[3], cur[4], cur[5], cur[6])

        arreactions = info_sheet.get_info_from_sheet(13, 0, 30, 2)

        for reaction in arreactions:
            self.prepared_reactions.ordinary_reactions[reaction[0]] = reaction[1]

        for i in range(len(self.field)):
            for j in range(len(self.field[i])):
                if self.field[i][j] == 'вход':
                    self.special_positions.startPosition = (i, j)
                if self.field[i][j] == 'выход':
                    self.special_positions.finishPosition = (i, j)
                if self.field[i][j] == '(0; 5)':
                    self.special_positions.teleportposition = (i, j)
                if self.field[i][j] == ':)':
                    self.special_positions.finishteleport = (i, j)
                if self.field[i][j] == 'приз':
                    self.special_positions.backteleport = (i, j)

                if self.problems.get(self.field[i][j]):
                    self.problems[self.field[i][j]].position = (i, j)

    def register(self, student_id: int):
        self.players[student_id] = Student(student_id)

    def _get_char_from_field(self, pos) -> str:
        return self.field[pos[0]][pos[1]]

    def _check_primary_reactions(self, student: Student, message: str) -> (bool, str):
        if message == self.prepared_reactions.whereIsSheet:
            return True, 'Вот ссылка на лабиринт, если вы вдруг потеряли: ' + storage.linkToField

        if message == self.prepared_reactions.whereIAm:
            ans = self._get_char_from_field(student.position)

            return True, 'Вы сейчас безопасно стоите на клетке < ' \
                   + ans + ' > , продолжайте исследование!)'

    def _check_move_reactions_and_move(self, student: Student, message: str) -> (bool, str):
        (succeed, delta) = self.prepared_reactions.convert_reaction_to_delta_position(message)
        if not succeed:
            return False, 'Я пока не умею отвечать на такие запросы((('

        nextpos = _add_delta_to_position(student.position, delta)

        if self._get_char_from_field(nextpos) == '#':
            return True, 'Ой, вы попробовали наступить на стену, не делайте так, прохода нет)'

        if nextpos in student.blocked_cells:
            answer = 'Ой, вы попробовали наступить на стену, не делайте так, прохода нет)\n' \
                     '-------\n'
            answer += 'Напоминаю, что для вас закрыты следующие клетки, потому что в них вы решили неправильно задачку:\n'

            for cell in student.blocked_cells:
                answer += self._get_char_from_field(cell) + '\n'

            return True, answer

        ## MOVE IS POSSIBLE

        answer = ''
        ## STEP ON A PROBLEM
        if self.problems.get(self._get_char_from_field(nextpos)):
            if nextpos not in student.solved_problems:
                cur_problem = self.problems[self._get_char_from_field(nextpos)]
                student.open_solving_session(cur_problem)

                answer = 'Вы наступили на  < ' + self._get_char_from_field(nextpos) + ' >, будьте внимательны'
                answer += '\n---------\n'
                answer += cur_problem.preamble
                answer += '\n---------\n'
                answer += cur_problem.text
                answer += '\n---------\n'

                return True, answer

            answer += 'Вы уже деактивировали эту загадку, опасности нет, можете спокойно проходить дальше'
            answer += '\n-------\n'

        # STEP ON ORDINARY CELL

        if self.prepared_reactions.ordinary_reactions.get(self._get_char_from_field(nextpos)):
            answer += self.prepared_reactions.ordinary_reactions[self._get_char_from_field(nextpos)]
            answer += '\n---------\n'

        # IF STEP ON SPECIAL POSITION -- TELEPORT

        if nextpos == self.special_positions.teleportposition:
            student.move_to_new_position(self.special_positions.finishteleport)

            answer += 'Ого, вы телепортировались в секретную комнату,' \
                      ' исследуйте дальше\n ------ \n Вы наступили на клетку < :) >'

            return True, answer

        if nextpos == self.special_positions.backteleport:
            student.move_to_new_position(self.special_positions.teleportposition)

            answer += 'Вы вышли из тайной комнаты)' \
                      ' Понравилось?\n Вы наступили на клетку < ' + self._get_char_from_field(
                self.special_positions.teleportposition) + '> , продолжайте исследование'

            return True, answer

        student.move_to_new_position(nextpos)
        answer += 'Вы наступили на клетку < ' + self._get_char_from_field(nextpos) + ' > ,' \
                                                                                     ' продолжайте исследование!'

        return True, answer

    def accept_confirmation(self, student_id: int) -> (str, ReplyKeyboard):
        student = self.players[student_id]
        answer = student.confirm_submited_answer()
        pass

    def reject_confirmation(self, student_id: int) -> (str, ReplyKeyboard):
        student = self.players[student_id]
        student.solving_session.requires_confirm = False
        return 'Ответ сброшен, вводите новый', ReplyKeyboard()

    def get_current_position(self, student_id : int) -> str:
        if not self.players.get(student_id):
            raise GameNotStarted

        student = self.players[student_id]
        return 'Вы сейчас безопасно стоите на клетке < ' \
                   + self._get_char_from_field(student.position) + ' > , продолжайте исследование!)'

    def make_action(self, student_id: int, message: str) -> (str, ReplyKeyboard):
        if not self.players.get(student_id):
            raise GameNotStarted

        # INIT player
        student = self.players[student_id]

        # PRIMARY REACTIONS
        (succeed, answer) = self._check_primary_reactions(student, message)
        if succeed:
            return answer, ReplyKeyboard()

        # CHECK SOLVING SESSION
        if student.solving_session.is_opened:
            if student.solving_session.requires_confirm:
                return student.solving_session.prepare_confirmation_message()

            student.solving_session.submit(message)
            return student.solving_session.prepare_confirmation_message()

        # CHECK MOVE
        (succeed, answer) = self._check_move_reactions_and_move(succeed, message)

        return answer, ReplyKeyboard()
