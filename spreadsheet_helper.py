import re
import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Workflow: 
# map of Task name to sheetID
# process each file:
#   if sheet exists, get sheetID
#   otherwise send request to create sheet and save sheetID
#   queue add column titles, account for empty spreadsheet below.
#   if subtask exists in sheet (now must exist) continue
#   otherwise: queue append column with formula
#   then: queue append row 
#   finally send values request

class httpRequester:
  def __init__(self, remote):
    self.service = remote
    self.requests = []

  def safeCall(self, call):
    try:
      return call.execute()
    except HttpError as e:
      print("API ERROR")
      print(e)  

class SpreadsheetAPI(httpRequester):
  def __init__(self,spreadsheet):
    super().__init__(spreadsheet)

  def getSheetsMap(self, spreadsheet):
    sheetsMap = {}
    for sheetObj in spreadsheet["sheets"]:
      sheetsMap[sheetObj["properties"]["title"]] = {
        "obj"     : sheetObj,
        "nextRow" : -1,
        "nextCol" : -1
      }
    return sheetsMap 

  def getSheets(self, spreadsheetId):
    request = self.service.get(spreadsheetId=spreadsheetId, includeGridData=True)
    response = request.execute()

    return self.getSheetsMap(response)

  def addSheet(self, name):
    for s in self.requests:
      if s["addSheet"]["properties"]["title"] == name:
        return
 
    self.requests.append({
      "addSheet" : { "properties" : { "title" : name } }
    })
    print("add",name)

  def formatCells(self, sheetId, endCol, endRow):
    # Duration as time
    self.requests.append({
      "repeatCell" : {
        "range" : {
          "sheetId"          : sheetId,
          "startRowIndex"    : 3,
          "endRowIndex"      : endRow+1,
          "startColumnIndex" : 2,
          "endColumnIndex"   : 3
        },
        "cell" : {
          "userEnteredFormat" : {
            "numberFormat" : { 
              "type"    : "TIME",
              "pattern" : "[h]:[mm]:[ss]"  
            } 
          }
        },
        "fields" : "userEnteredFormat.numberFormat.type, userEnteredFormat.numberFormat.pattern"
      }
    })
    
    # Titles bold
    self.requests.append({
      "repeatCell" : {
        "range" : {
          "sheetId"          : sheetId,
          "startRowIndex"    : 1,
          "endRowIndex"      : 2,
          "startColumnIndex" : 0,
          "endColumnIndex"   : endCol + 1
        },
        "cell" : {
          "userEnteredFormat" : {
              "textFormat" : { "bold" : True }
          }
        },
        "fields" : "userEnteredFormat.textFormat.bold"
      }
    })

  def repeatFormula(self, sheetId, endCol, endRow):
    self.requests.append({
      "repeatCell" : {
        "range" : {
          "sheetId" : sheetId,
          "startRowIndex"    : 3,
          "endRowIndex"      : endRow+1,
          "startColumnIndex" : 4,
          "endColumnIndex"   : endCol+1
        },
        "cell" : {
          "userEnteredValue" : {
            "formulaValue" : "=if($B4=E$2,$C4+E3,E3)"
          },
          "userEnteredFormat" : {
            "numberFormat" : { 
              "type"    : "TIME",
              "pattern" : "[h]:[mm]:[ss]"  
            } 
          }
        },
        "fields" : "userEnteredValue.formulaValue, userEnteredFormat.numberFormat.type, userEnteredFormat.numberFormat.pattern"
      }
    })
    self.formatCells(sheetId, endCol, endRow)
  
  def batchUpdate(self, spreadsheetId):
    request_body = {
      "requests" : self.requests,
      "includeSpreadsheetInResponse": True
    }

    request = self.service.batchUpdate(spreadsheetId=spreadsheetId, body=request_body)
    
    response = self.safeCall(request)    
    self.requests = []
   
    if response != None:
      return self.getSheetsMap(response['updatedSpreadsheet'])
    return {}

class ValuesAPI(httpRequester):
  def __init__(self,values):
    super().__init__(values)    

  def addValues(self, sheet, cells, values):
    self.requests.append({
      "range" : sheet+"!"+cells,
      "majorDimension" : "ROWS",
      "values" : values
    })

  def batchUpdate(self, spreadsheetId):
    request_body = {
      "valueInputOption" : "USER_ENTERED",
      "data" : self.requests,
      "includeValuesInResponse": False,
    }
    request = self.service.batchUpdate(spreadsheetId=spreadsheetId, body=request_body)

    self.safeCall(request)

    self.requests = []

class API:
  SCOPES  = ['https://www.googleapis.com/auth/spreadsheets']
  creds   = None

  def __init__(self,url):
    ret = re.search('/d/(.*)/edit', url)
    if ret != None:
      self.id = ret.group(1)
    
      # https://developers.google.com/sheets/api/quickstart/python
      if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
          self.creds = pickle.load(token)
      # If there are no (valid) credentials available, let the user log in.
      if not self.creds or not self.creds.valid:
        if self.creds and self.creds.expired and self.creds.refresh_token:
          self.creds.refresh(Request())
        else:
          flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
          self.creds = flow.run_local_server(port=0)
          # Save the credentials for the next run
          with open('token.pickle', 'wb') as token:
            pickle.dump(self.creds, token)

      self.spreadsheet = build('sheets', 'v4', credentials=self.creds).spreadsheets()

      self.spreadsheetAPI = SpreadsheetAPI(self.spreadsheet)
      self.sheets = self.spreadsheetAPI.getSheets(self.id)
      self.valuesAPI = ValuesAPI(self.spreadsheet.values())
 
    else:
      print("Error: Spreadsheet ID not found in URL:\n  " + url)

  def getSheetId(self, name):
    return self.sheets[name]["obj"]["properties"]["sheetId"]

  def coordToRange(self,row, col):
    return chr(ord('A') + row) + str(col+1)

  def getCellValue(self, name, cell):
    col = ord(cell[0]) - ord('A')
    row = int(cell[1:]) - 1

    #print(name, cell, col, row)

    try:
      return (self.sheets[name]["obj"]["data"][0]["rowData"][row]["values"][col]["formattedValue"])
    except KeyError:
      return ""    
    except IndexError:
      return ""    

  def getNextRow(self, name):
    read = self.sheets[name]["nextRow"]
    if read != -1:
      self.sheets[name]["nextRow"] = read + 2
      return read
    
    row = 3
    while self.getCellValue(name, self.coordToRange(0, row)) != "":
      row+=1
    
    self.sheets[name]["nextRow"] = row + 2
    return row 

  def getColIdx(self, name, subtask):
    read = self.sheets[name]["nextCol"]

    idx = 4
    found = False;
    while not found:
      heading = self.getCellValue(name, self.coordToRange(idx, 1)).lower()
      if heading == "":
        break
      elif heading == subtask:
        return idx
      else:
        idx+=1

    if read == -1:
      col = idx;
      self.sheets[name]["nextCol"] = idx + 1
    else:
      col = read
      self.sheets[name]["nextCol"] = read + 1
  
    print(name, subtask, col)
 
    start = self.coordToRange(col,1)
    end   = self.coordToRange(col,2)
    cells = start + ":" + end
    self.valuesAPI.addValues(name, cells,[[ subtask.title() ], [ 0 ]])
  
    return col

  def addRecord(self, task, date, subtask, duration, note):
    print(date, subtask, duration, note)
 
    if self.getCellValue(task, "A2") != "Date":
      self.valuesAPI.addValues(task, "A2:D3", [["Date","Sub-Task","Duration","Note"],[date, "", "", ""]])

    nxtRow = self.getNextRow(task)
    col    = self.getColIdx(task, subtask)

    start = self.coordToRange(0, nxtRow)
    end   = self.coordToRange(3, nxtRow+1)

    cells = start + ":" + end
    
    self.valuesAPI.addValues(task, cells, [[date, "", 0, ""],[ date, subtask, duration, note ]]) 
    
    self.spreadsheetAPI.repeatFormula(self.getSheetId(task), col, nxtRow+1) 

  def getOrCreateSheet(self, name):
    if name not in self.sheets.keys():
       self.spreadsheetAPI.addSheet(name)

  def updateSpreadsheet(self):
    newSheets = self.spreadsheetAPI.batchUpdate(self.id)
    if newSheets != {}:
      self.sheets = newSheets

  def updateValues(self):
    self.valuesAPI.batchUpdate(self.id)

  def getCell(self,cell):
    col = ord(cell[0]) - ord('A')
    row = int(cell[1]) - 1

    try:
      return self.values[row][col]
    except IndexError:
      return ''
