import re
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class API:
  SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
 
  creds = None
 
  def __init__(self,url):
    ret = re.search('/d/(.*)/edit', url)
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
    seld.sheet = service.spreadsheets()
