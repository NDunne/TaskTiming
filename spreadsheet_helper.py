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

class API:
  SCOPES  = ['https://www.googleapis.com/auth/spreadsheets']
  creds   = None
  current = "" 

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

      self.service = build('sheets', 'v4', credentials=self.creds)
      self.sheet = self.service.spreadsheets()
    else:
      print("Error: Spreadsheet ID not found in URL:\n  " + url)

  def newSheet(self,name):

  def addRecord(self,date, subtask, duration, note):
    

  # might need to rethink this
  def getValues(self,tab):
    current = tab
    getFunc = self.sheet.values().get(spreadsheetId=self.id,range="'"+tab+"'!A:Z")
    try:
      result = getFunc.execute()
      self.values = result.get('values', [])
    except HttpError:
      self.values = self.newSheet(current)
    print(self.values)

  def getCell(self,cell):
    col = ord(cell[0]) - ord('A')
    row = int(cell[1]) - 1

    try:
      return self.values[row][col]
    except IndexError:
      return ''
