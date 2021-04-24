from pprint import pprint
import httplib2
import apiclient
import googleapiclient.errors
from oauth2client.service_account import ServiceAccountCredentials


def htmlColorToJSON(htmlColor):
    if htmlColor.startswith("#"):
        htmlColor = htmlColor[1:]
    return {"red": int(htmlColor[0:2], 16) / 255.0, "green": int(htmlColor[2:4], 16) / 255.0,
            "blue": int(htmlColor[4:6], 16) / 255.0}


class SpreadsheetError(Exception):
    pass


class SpreadsheetNotSetError(SpreadsheetError):
    pass


class SheetNotSetError(SpreadsheetError):
    pass


class Spreadsheet:
    def __init__(self, jsonKeyFileName, debugMode=False):
        self.debugMode = debugMode
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(jsonKeyFileName, [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'])
        self.httpAuth = self.credentials.authorize(httplib2.Http())
        self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.driveService = None  # Needed only for sharing
        self.spreadsheetId = None
        self.sheetId = None
        self.sheetTitle = None
        self.requests = []
        self.valueRanges = []

    # Creates new spreadsheet
    def create(self, title, sheetTitle, rows=1000, cols=26, locale='en_US', timeZone='Etc/GMT'):
        spreadsheet = self.service.spreadsheets().create(body={
            'properties': {'title': title, 'locale': locale, 'timeZone': timeZone},
            'sheets': [{'properties': {'sheetType': 'GRID', 'sheetId': 0, 'title': sheetTitle,
                                       'gridProperties': {'rowCount': rows, 'columnCount': cols}}}]
        }).execute()
        if self.debugMode:
            pprint(spreadsheet)
        self.spreadsheetId = spreadsheet['spreadsheetId']
        self.sheetId = spreadsheet['sheets'][0]['properties']['sheetId']
        self.sheetTitle = spreadsheet['sheets'][0]['properties']['title']

    def share(self, shareRequestBody):
        if self.spreadsheetId is None:
            raise SpreadsheetNotSetError()
        if self.driveService is None:
            self.driveService = apiclient.discovery.build('drive', 'v3', http=self.httpAuth)
        shareRes = self.driveService.permissions().create(
            fileId=self.spreadsheetId,
            body=shareRequestBody,
            fields='id'
        ).execute()
        if self.debugMode:
            pprint(shareRes)

    def shareWithEmailForReading(self, email):
        self.share({'type': 'user', 'role': 'reader', 'emailAddress': email})

    def shareWithEmailForWriting(self, email):
        self.share({'type': 'user', 'role': 'writer', 'emailAddress': email})

    def shareWithAnybodyForReading(self):
        self.share({'type': 'anyone', 'role': 'reader'})

    def shareWithAnybodyForWriting(self):
        self.share({'type': 'anyone', 'role': 'writer'})

    def getSheetURL(self):
        if self.spreadsheetId is None:
            raise SpreadsheetNotSetError()
        if self.sheetId is None:
            raise SheetNotSetError()
        return 'https://docs.google.com/spreadsheets/d/' + self.spreadsheetId + '/edit#gid=' + str(self.sheetId)

    # Sets current spreadsheet by id; set current sheet as first sheet of this spreadsheet
    def setSpreadsheetById(self, spreadsheetId):
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()
        if self.debugMode:
            pprint(spreadsheet)
        self.spreadsheetId = spreadsheet['spreadsheetId']
        self.sheetId = spreadsheet['sheets'][0]['properties']['sheetId']
        self.sheetTitle = spreadsheet['sheets'][0]['properties']['title']

    # Sets current spreadsheet by id; set current sheet as sheetID
    def setSpreadsheetByIdAndSheetId(self, spreadsheetId, sheetId):
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()
        if self.debugMode:
            pprint(spreadsheet)
        self.spreadsheetId = spreadsheet['spreadsheetId']
        self.sheetId = sheetId
        self.sheetTitle = [sheet['properties']['title'] for sheet in spreadsheet['sheets'] \
                           if sheet['properties']['sheetId'] == sheetId][0]

    # spreadsheets.batchUpdate and spreadsheets.values.batchUpdate
    def runPrepared(self, valueInputOption="USER_ENTERED"):
        if self.spreadsheetId is None:
            raise SpreadsheetNotSetError()
        upd1Res = {'replies': []}
        upd2Res = {'responses': []}
        try:
            if len(self.requests) > 0:
                upd1Res = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheetId,
                                                                  body={"requests": self.requests}).execute()
                if self.debugMode:
                    pprint(upd1Res)
            if len(self.valueRanges) > 0:
                upd2Res = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheetId,
                                                                           body={"valueInputOption": valueInputOption,
                                                                                 "data": self.valueRanges}).execute()
                if self.debugMode:
                    pprint(upd2Res)
        finally:
            self.requests = []
            self.valueRanges = []
        return (upd1Res['replies'], upd2Res['responses'])

    def prepare_addSheet(self, sheetTitle, rows=1000, cols=26):
        self.requests.append({"addSheet": {
            "properties": {"title": sheetTitle, 'gridProperties': {'rowCount': rows, 'columnCount': cols}}}})

    # Adds new sheet to current spreadsheet, sets as current sheet and returns it's id
    def addSheet(self, sheetTitle, rows=1000, cols=26):
        if self.spreadsheetId is None:
            raise SpreadsheetNotSetError()
        self.prepare_addSheet(sheetTitle, rows, cols)
        addedSheet = self.runPrepared()[0][0]['addSheet']['properties']
        self.sheetId = addedSheet['sheetId']
        self.sheetTitle = addedSheet['title']
        return self.sheetId

    # Converts string range to GridRange of current sheet; examples:
    #   "A3:B4" -> {sheetId: id of current sheet, startRowIndex: 2, endRowIndex: 4, startColumnIndex: 0, endColumnIndex: 2}
    #   "A5:B"  -> {sheetId: id of current sheet, startRowIndex: 4, startColumnIndex: 0, endColumnIndex: 2}

    def _letters_to_number(self, letters):
        letters = letters[::-1]
        ans = 0
        deg = 0
        for let in letters:
            ans += (ord(let) - ord('A') + 1) * (26 ** deg)
            deg += 1
        return ans

    def _parce_string_range_to_numbers(self, curstring):
        rowIndex = 0
        columnIndex = 0
        letters = ''
        numbers = ''
        for element in curstring:
            if 'A' <= element <= 'Z':
                letters += element
            else:
                numbers += element

        rowIndex = int(numbers)
        columnIndex = self._letters_to_number(letters)
        return rowIndex, columnIndex

    def toGridRange(self, cellsRange):  # TODO make it safier
        if self.sheetId is None:
            raise SheetNotSetError()
        if isinstance(cellsRange, str):
            startCell, endCell = cellsRange.split(":")
            startCellRowIndex, startCellColumnIndex = self._parce_string_range_to_numbers(startCell)
            endCellRowIndex, endCellColumnIndex = self._parce_string_range_to_numbers(endCell)
            cellsRange = {}

            cellsRange["startColumnIndex"] = startCellColumnIndex - 1
            cellsRange["endColumnIndex"] = endCellColumnIndex
            cellsRange["startRowIndex"] = startCellRowIndex - 1
            cellsRange["endRowIndex"] = endCellRowIndex

        cellsRange["sheetId"] = self.sheetId
        return cellsRange

    def previous_toGridRange(self, cellsRange):
        if self.sheetId is None:
            raise SheetNotSetError()
        if isinstance(cellsRange, str):
            startCell, endCell = cellsRange.split(":")[0:2]
            cellsRange = {}
            rangeAZ = range(ord('A'), ord('Z') + 1)
            if ord(startCell[0]) in rangeAZ:
                cellsRange["startColumnIndex"] = ord(startCell[0]) - ord('A')
                startCell = startCell[1:]
            if ord(endCell[0]) in rangeAZ:
                cellsRange["endColumnIndex"] = ord(endCell[0]) - ord('A') + 1
                endCell = endCell[1:]
            if len(startCell) > 0:
                cellsRange["startRowIndex"] = int(startCell) - 1
            if len(endCell) > 0:
                cellsRange["endRowIndex"] = int(endCell)
        cellsRange["sheetId"] = self.sheetId
        return cellsRange

    def prepare_setDimensionPixelSize(self, dimension, startIndex, endIndex, pixelSize):
        if self.sheetId is None:
            raise SheetNotSetError()
        self.requests.append({"updateDimensionProperties": {
            "range": {"sheetId": self.sheetId,
                      "dimension": dimension,
                      "startIndex": startIndex,
                      "endIndex": endIndex},
            "properties": {"pixelSize": pixelSize},
            "fields": "pixelSize"}})

    def prepare_setColumnsWidth(self, startCol, endCol, width):
        self.prepare_setDimensionPixelSize("COLUMNS", startCol, endCol, width)

    def prepare_setColumnWidth(self, col, width):
        self.prepare_setColumnsWidth(col, col, width)

    def prepare_setRowsHeight(self, startRow, endRow, height):
        self.prepare_setDimensionPixelSize("ROWS", startRow, endRow + 1, height)

    def prepare_setRowHeight(self, row, height):
        self.prepare_setRowsHeight(row, row, height)

    def _get_sheets_letter_combination_from_number(self, a):
        alpaLen = ord('Z') - ord('A') + 1
        ans = ''
        while a > 0:
            if a % alpaLen == 0:
                ans += 'Z'
                a -= 1
            else:
                ans += chr(a % alpaLen + ord('A') - 1)
            a //= alpaLen

        return ans[::-1]

    def _get_range(self, startRowIndex, startColumnIndex, endRowIndex, endColumnIndex):
        # начиная с нуля, координаты сначала левого верхнего, затем правого нижнего угла
        # (не включительно. Полуинтервал!)
        leftUp = self._get_sheets_letter_combination_from_number(startColumnIndex + 1) + str(startRowIndex + 1)
        rightDouw = self._get_sheets_letter_combination_from_number(endColumnIndex) + str(endRowIndex)
        return leftUp + ':' + rightDouw

    # cellsRange - list of two elements [startRowIndex, startColumnIndex]
    def prepare_setValues(self, cellsRange, values, majorDimension="ROWS"):
        maxRowLen = max([len(i) for i in values])
        startRowIndex, startColumnIndex = cellsRange[0], cellsRange[1]
        ConvertedCellsRange = self._get_range(startRowIndex, startColumnIndex,
                                              startRowIndex + len(values), startColumnIndex + maxRowLen)
        if self.sheetTitle is None:
            raise SheetNotSetError()
        self.valueRanges.append(
            {"range": self.sheetTitle + "!" + ConvertedCellsRange, "majorDimension": majorDimension, "values": values})

    def prepare_mergeCells(self, cellsRange, mergeType="MERGE_ALL"):
        self.requests.append({"mergeCells": {"range": self.toGridRange(cellsRange), "mergeType": mergeType}})

    # formatJSON should be dict with userEnteredFormat to be applied to each cell
    def prepare_setCellsFormat(self, cellsRange, formatJSON, fields="userEnteredFormat"):
        self.requests.append({"repeatCell": {"range": self.toGridRange(cellsRange),
                                             "cell": {"userEnteredFormat": formatJSON}, "fields": fields}})

    # formatsJSON should be list of lists of dicts with userEnteredFormat for each cell in each row
    def prepare_setCellsFormats(self, cellsRange, formatsJSON, fields="userEnteredFormat"):
        self.requests.append({"updateCells": {"range": self.toGridRange(cellsRange),
                                              "rows": [{"values": [{"userEnteredFormat": cellFormat} for cellFormat in
                                                                   rowFormats]} for rowFormats in formatsJSON],
                                              "fields": fields}})

    def prepare_changeLeftBoarders(self, cellsRange, width=1):
        self.requests.append({"updateBorders": {"range": self.toGridRange(cellsRange),
                                                'left': {'style': 'SOLID',
                                                         'width': width,
                                                         'color': {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}},
                                                }})

    def prepare_changeBoarders(self, cellsRange, width=1):
        self.requests.append({"updateBorders": {"range": self.toGridRange(cellsRange),
                                                'left': {'style': 'SOLID',
                                                         'width': width,
                                                         'color': {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}},
                                                'right': {'style': 'SOLID',
                                                          'width': width,
                                                          'color': {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}},
                                                'bottom': {'style': 'SOLID',
                                                           'width': width,
                                                           'color': {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}},
                                                'top': {'style': 'SOLID',
                                                        'width': width,
                                                        'color': {'red': 0, 'green': 0, 'blue': 0, 'alpha': 1}},
                                                }})

    def prepare_deleteColumnsRequest(self, startColumnIndex, endColumnIndex):
        self.requests.append({"deleteDimension": {"range": {"sheetId": self.sheetId,
                                                            "dimension": "COLUMNS",
                                                            "startIndex": startColumnIndex,
                                                            "endIndex": endColumnIndex}}})

    def prepare_addColumnRequest(self, numberOfColumns):
        self.requests.append({"appendDimension": {
            "sheetId": self.sheetId,
            "dimension": "COLUMNS",
            "length": numberOfColumns,
        }})

    def prepare_frozeColumnsRequest(self, numberOfColumns):
        self.requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": self.sheetId,
                        "gridProperties": {
                            "frozenColumnCount": numberOfColumns
                        }
                    },
                    "fields": "gridProperties.frozenColumnCount"
                }
            }
        )

    def prepare_frozeRowsRequest(self, numberOfRows):
        self.requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": self.sheetId,
                        "gridProperties": {
                            "frozenRowCount": numberOfRows
                        }
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            }
        )

    ##### GETTING INFORMATION FROM SHEETS

    def get_info_from_sheet(self, startRowIndex, startColumnIndex, endRowIndex,
                            endColumnIndex):  # отсчет с нуля, не включая правую границу!
        if self.spreadsheetId == None or self.sheetId == None:
            raise SheetNotSetError()

        # print('hey from debug:')
        # print(self.sheetTitle + '!' + self._get_range(startRowIndex, startColumnIndex, endRowIndex, endColumnIndex))
        values = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheetId,
            range=self.sheetTitle + '!' + self._get_range(startRowIndex, startColumnIndex, endRowIndex, endColumnIndex),
            majorDimension='ROWS'
        ).execute()['values']

        maxRowLen = max([len(i) for i in values])
        for i in range(len(values)):
            while len(values[i]) < maxRowLen:
                values[i].append('')

        return values

    def _get_full_info_from_sheet(self, startRowIndex, startColumnIndex, endRowIndex, endColumnIndex):
        if self.spreadsheetId == None or self.sheetId == None:
            raise SheetNotSetError()

        # print('hey from debug:')
        # print(self.sheetTitle + '!' + self._get_range(startRowIndex, startColumnIndex, endRowIndex, endColumnIndex))
        values = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheetId,
            ranges=self.sheetTitle + '!' + self._get_range(startRowIndex, startColumnIndex, endRowIndex,
                                                           endColumnIndex),
            # majorDimension='ROWS'
        ).execute()

        return values


# returns a list of Spreadsheet, each of them contains a sheet of a spreadsheet by this spreadsheetId
def get_all_sheets_from_spreadsheet(spreadsheetId):
    spreadsheet = Spreadsheet('creds.json')
    meta_data = spreadsheet.service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()

    list_of_sheets = []

    for cur_sheet in meta_data['sheets']:
        list_of_sheets.append(Spreadsheet('creds.json'))
        list_of_sheets[-1].setSpreadsheetByIdAndSheetId(spreadsheetId, cur_sheet['properties']['sheetId'])

    # list_of_sheets = [Spreadsheet('creds.json').setSpreadsheetByIdAndSheetId(spreadsheetId,
    #                                                                          cur_sheet['properties']['sheetId'])\
    #                   for cur_sheet in meta_data['sheets']]

    return list_of_sheets


####Tests

# === Tests for class Spreadsheet ===

GOOGLE_CREDENTIALS_FILE = 'tg-tm-bot-d146fb60ef7a.json'


def testCreateSpreadsheet():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.create("Preved medved", "Тестовый лист")
    ss.shareWithEmailForWriting("volkov.ioann@gmail.com")


def testSetSpreadsheet():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    print(ss.sheetId)


def testAddSheet():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    try:
        print(ss.addSheet("Я лолка №1", 500, 11))
    except googleapiclient.errors.HttpError:
        print("Could not add sheet! Maybe sheet with same name already exists!")


def testSetDimensions():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    ss.prepare_setColumnWidth(0, 500)
    ss.prepare_setColumnWidth(1, 100)
    ss.prepare_setColumnsWidth(2, 4, 150)
    ss.prepare_setRowHeight(6, 230)
    ss.runPrepared()


def testGridRangeForStr():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    res = [ss.toGridRange("A3:B4"),
           ss.toGridRange("A5:B"),
           ss.toGridRange("A:B")]
    correctRes = [
        {"sheetId": ss.sheetId, "startRowIndex": 2, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 2},
        {"sheetId": ss.sheetId, "startRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 2},
        {"sheetId": ss.sheetId, "startColumnIndex": 0, "endColumnIndex": 2}]
    print("GOOD" if res == correctRes else "BAD", res)


def testSetCellsFormat():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    ss.prepare_setCellsFormat("B2:E7", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})
    ss.runPrepared()


def testPureBlackBorder():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0,
                  "endColumnIndex": 3},
        "bottom": {"style": "SOLID", "width": 3, "color": {"red": 0, "green": 0, "blue": 0}}}})
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0,
                  "endColumnIndex": 3},
        "bottom": {"style": "SOLID", "width": 3, "color": {"red": 0, "green": 0, "blue": 0, "alpha": 1.0}}}})
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1,
                  "endColumnIndex": 4},
        "bottom": {"style": "SOLID", "width": 3, "color": {"red": 0, "green": 0, "blue": 0.001}}}})
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 2,
                  "endColumnIndex": 5},
        "bottom": {"style": "SOLID", "width": 3, "color": {"red": 0.001, "green": 0, "blue": 0}}}})
    ss.runPrepared()
    # Reported: https://code.google.com/a/google.com/p/apps-api-issues/issues/detail?id=4696


def testUpdateCellsFieldsArg():
    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.setSpreadsheetById('19SPK--efwYq9pZ7TvBYtFItxE0gY3zpfR5NykOJ6o7I')
    ss.prepare_setCellsFormat("B2:B2", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"},
                              fields="userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment")
    ss.prepare_setCellsFormat("B2:B2", {"backgroundColor": htmlColorToJSON("#00CC00")},
                              fields="userEnteredFormat.backgroundColor")
    ss.prepare_setCellsFormats("C4:C4", [[{"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"}]],
                               fields="userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment")
    ss.prepare_setCellsFormats("C4:C4", [[{"backgroundColor": htmlColorToJSON("#00CC00")}]],
                               fields="userEnteredFormat.backgroundColor")
    pprint(ss.requests)
    ss.runPrepared()
    # Reported: https://code.google.com/a/google.com/p/apps-api-issues/issues/detail?id=4697


# This function creates a spreadsheet as https://telegram.me/TimeManagementBot can create, but with manually specified data
def testCreateTimeManagementReport():
    docTitle = "Тестовый документ"
    sheetTitle = "Тестовая таблица действий"
    values = [["Действие", "Категория полезности", "Начато", "Завершено", "Потрачено"],  # header row
              ["Обедаю", "Еда", "2 июл 2016 17:57:52", "2 июл 2016 18:43:45", "=D4-C4"],
              ["Лёг полежать", "Отдых", "2 июл 2016 18:43:47", "2 июл 2016 18:53:36", "=D5-C5"],
              ["Пью чай", "Еда", "2 июл 2016 18:53:39", "2 июл 2016 19:00:49", "=D6-C6"],
              ["Пилю и шлифую большие щиты", "Ремонт", "2 июл 2016 19:00:52", "2 июл 2016 19:52:36", "=D7-C7"],
              ["Собираю дверь шкафа", "Ремонт", "2 июл 2016 19:52:38", "2 июл 2016 21:11:21", "=D8-C8"]]
    rowCount = len(values) - 1
    colorsForCategories = {"Еда": htmlColorToJSON("#FFCCCC"),
                           "Отдых": htmlColorToJSON("#CCFFCC"),
                           "Ремонт": htmlColorToJSON("#CCCCFF")}

    values2 = [["Категория полезности", "Потрачено"],  # header row
               ["Ремонт", "=E7+E8"],
               ["Еда", "=E4+E6"],
               ["Отдых", "=E5"]]
    rowCount2 = len(values2) - 1

    ss = Spreadsheet(GOOGLE_CREDENTIALS_FILE, debugMode=True)
    ss.create(docTitle, sheetTitle, rows=rowCount + 3, cols=8, locale="ru_RU", timeZone="Europe/Moscow")
    ss.shareWithAnybodyForWriting()

    ss.prepare_setColumnWidth(0, 400)
    ss.prepare_setColumnWidth(1, 200)
    ss.prepare_setColumnsWidth(2, 3, 165)
    ss.prepare_setColumnWidth(4, 100)
    ss.prepare_mergeCells("A1:E1")  # Merge A1:E1

    rowColors = [colorsForCategories[valueRow[1]] for valueRow in values[1:]]

    ss.prepare_setCellsFormat("A1:A1", {"textFormat": {"fontSize": 14},
                                        "horizontalAlignment": "CENTER"})  # Font size 14 and center aligment for A1 cell
    ss.prepare_setCellsFormat("A3:E3", {"textFormat": {"bold": True},
                                        "horizontalAlignment": "CENTER"})  # Bold and center aligment for A3:E3 row
    ss.prepare_setCellsFormats("A4:E%d" % (rowCount + 3), [[{"backgroundColor": color}] * 5 for color in rowColors])
    ss.prepare_setCellsFormat("A4:B%d" % (rowCount + 3), {"numberFormat": {'type': 'TEXT'}},
                              fields="userEnteredFormat.numberFormat")  # Text format for A4:B* columns
    ss.prepare_setCellsFormat("E4:E%d" % (rowCount + 3), {"numberFormat": {'pattern': '[h]:mm:ss', 'type': 'TIME'}},
                              fields="userEnteredFormat.numberFormat")  # Duration number format for E4:E* column

    # Bottom border for A3:E3 row
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0,
                  "endColumnIndex": 5},
        "bottom": {"style": "SOLID", "width": 1, "color": htmlColorToJSON("#000001")}}})

    ss.prepare_setValues("A1:A1", [[sheetTitle]])
    ss.prepare_setValues("A3:E%d" % (rowCount + 3), values)

    # ss.prepare_setCellsFormat("D%d:D%d" % (rowCount + 3, rowCount + 3), {"textFormat": {"italic": True}, "horizontalAlignment": "CENTER"},
    #                          fields = "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment")  # Italic and center aligment for bottom D* cell

    ss.prepare_setColumnWidth(6, 200)
    ss.prepare_setColumnWidth(7, 100)
    ss.prepare_mergeCells("G1:H1")  # Merge G1:H1

    rowColors2 = [colorsForCategories[valueRow[0]] for valueRow in values2[1:]]

    ss.prepare_setCellsFormat("G1:G1", {"textFormat": {"fontSize": 14},
                                        "horizontalAlignment": "CENTER"})  # Font size 14 and center aligment for G1 cell
    ss.prepare_setCellsFormat("G3:H3", {"textFormat": {"bold": True},
                                        "horizontalAlignment": "CENTER"})  # Bold and center aligment for G3:H3 row
    ss.prepare_setCellsFormats("G4:H%d" % (rowCount2 + 3), [[{"backgroundColor": color}] * 2 for color in rowColors2])
    ss.prepare_setCellsFormat("G4:G%d" % (rowCount2 + 3), {"numberFormat": {'type': 'TEXT'}},
                              fields="userEnteredFormat.numberFormat")  # Text format for G4:G* column
    ss.prepare_setCellsFormat("H4:H%d" % (rowCount2 + 3), {"numberFormat": {'pattern': '[h]:mm:ss', 'type': 'TIME'}},
                              fields="userEnteredFormat.numberFormat")  # Duration number format for H4:H* column

    # Bottom border for G3:H3 row
    ss.requests.append({"updateBorders": {
        "range": {"sheetId": ss.sheetId, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 6,
                  "endColumnIndex": 8},
        "bottom": {"style": "SOLID", "width": 1, "color": htmlColorToJSON("#000001")}}})

    ss.prepare_setValues("G1:G1", [["Категории"]])
    ss.prepare_setValues("G3:H%d" % (rowCount2 + 3), values2)

    ss.runPrepared()
    print(ss.getSheetURL())


if __name__ == "__main__":
    # testCreateSpreadsheet()
    # testSetSpreadsheet()
    # testAddSheet()
    # testSetDimensions()
    # testGridRangeForStr()
    # testSetCellsFormat()
    # testPureBlackBorder()
    # testUpdateCellsFieldsArg()
    testCreateTimeManagementReport()
