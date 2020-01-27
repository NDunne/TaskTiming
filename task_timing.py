import argparse
import configparser
import time
import datetime as dt
import os
import re

from datetime import date, datetime
from spreadsheet_helper import *

file_pattern = re.compile("[0-9][0-9][0-9][0-9]_[0-9][0-9]_[0-9][0-9]__[0-9][0-9]_[0-9][0-9]_[0-9][0-9]")

# use google api to update spreadsheet
def api_push(url, cred):
  data = []
  api = API(url, cred)
  i = 0

  #api call to create spreadsheet needed before anything else
  for filename in os.listdir(path):
    if file_pattern.match(filename):
      data.append(configparser.ConfigParser())
      data[i].read(path+filename)
      api.getOrCreateSheet(data[i]['RECORD']['task'])
      i += 1
  
  #send request
  api.updateSpreadsheet()
  for record in data:
    api.addRecord(record['RECORD']['task'], record['RECORD']['date'], record['RECORD']['subtask'], record['RECORD']['duration'], record['RECORD']['note'])

  #send request to update values
  api.updateValues()
  
  # check success? #

  for filename in os.listdir(path):
    if file_pattern.match(filename):
      os.remove(path+filename)

  exit(0)
  
# insert into config, or create section if required
def cfg_insert(cfg, section, var, val):
  if section in cfg:
    cfg[section][var] = val
  else:
    cfg[section] = { var : val }     
  
  if not os.path.exists(path):
    os.makedirs(path)
  with open(path+'task_timing.cfg', 'w+') as cfg_file:
    cfg.write(cfg_file) 

# writes a data file to be pushed to the spreadsheet
def writeFile(task, date, dur, subtask, note):
 
  # create folder if it doesn't exist
  if not os.path.exists(path):
    os.makedirs(path)
    print('\nFolder ' + path + ' created') 
 
  record = configparser.ConfigParser()
  record['RECORD'] = { 'TASK'     : task,
                       'DATE'     : date,
                       'DURATION' : dur,
                       'SUBTASK'  : subtask,
                       'NOTE'     : note
                     }
  # name file current date and time
  f = path + datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
  print("\nRecord saved to file:\n  " + f + "\n\n Use --push to sync the google sheets file\n")
  with open(f,'w') as record_file:
    record.write(record_file)

#
# Main method
#

def main():

  # create arguments

  # might need revisiting for ease of use
  parser = argparse.ArgumentParser(description='Time tasks and subtasks using google sheets api')
  tmr_args = parser.add_argument_group('Start/Stop Timer')
  tmr_args.add_argument('task', nargs='?')
  tmr_args.add_argument('subtask', nargs='?')
  tmr_args.add_argument('action', choices={'on','off'}, nargs='?')
  tmr_args.add_argument('-n','--note', metavar='"NOTE"',  help='Store in spreadsheet with this note') 

  cfg_args = parser.add_argument_group('Configuration')
  cfg_args.add_argument('--spreadsheet', metavar='URL', help='The spreadsheet to modify') 
  cfg_args.add_argument('--cred', metavar='FILEPATH', help='Full path of credentials.json for google authentication') 
  cfg_args.add_argument('--reset', action='store_true', help='Clear all current timers and exit')
  
  api_args = parser.add_argument_group('Remote')
  api_args.add_argument('--push', action='store_true', help='Update spreadsheet with recorded times')
 
  args = parser.parse_args()

  # read config file
  cfg = configparser.ConfigParser()
  cfg.read(path + 'task_timing.cfg')

  # reset current timers. Cancels all running timers
  if args.reset:
    clear_cfg = configparser.ConfigParser()
    clear_cfg['CONFIG'] = cfg['CONFIG']

    with open(path+'task_timing.cfg', 'w') as cfg_file:
      clear_cfg.write(cfg_file) 
    exit(0)

  URL = ''
  CRED = ''
  if args.spreadsheet != None:
    cfg_insert(cfg, 'CONFIG', 'URL', args.spreadsheet)

  if args.cred != None:
    cfg_insert(cfg, 'CONFIG', 'CRED', args.cred)
 
  if 'CONFIG' in cfg: 
    if 'URL' in cfg['CONFIG']:
      URL = cfg['CONFIG']['URL']
    else:
      print(" - No Spreadsheet URL configured. Use --spreadsheet to set.")
    if 'CRED' in cfg['CONFIG']:
      CRED = cfg['CONFIG']['CRED']
    else:
      print(" - No Credential file configured. Use --cred to set.")
  # Push timers to the spreadsheet.
    if args.push:
      api_push(URL, CRED)
 
  else:
    cfg['CONFIG'] = { 'URL' : URL, 'CRED' : CRED }     


  task = "" if args.task == None else args.task
  subtask = "" if args.subtask == None else args.subtask
  action = "" if args.action == None else args.action

  if task == "":
    print("No config or timer operation provided. Try '-h' ")
    exit(0)
  elif subtask == "":
    print("No timer operation for task",task,"provided. Try '-h' ")
    exit(0)
  elif action == "":
    if subtask == "on" or subtask == "off":
      action = subtask 
      subtask = "Base"
    else:
      print("No timer operation for task",task,"-",subtask,"provided. Try '-h' ")
      exit(0)
    

  print(task,"|",subtask,"|",action)  

  today   = date.today().strftime("%d/%m/%Y")
 
  cfg_insert(cfg, 'TASKS', 'TODAY', today)

  # TITLE_SUBTITLE is section title
  subtitle = task+'_'+subtask
  action_time = time.time()

  cfg_insert(cfg, subtitle, action, str(action_time))

  if action == 'on':
    print('Timer for ' + task + ' - ' + subtask + ' Running')
  elif cfg[task][subtask] == 'on': 
    print('Timer for '+ task + ' - ' + subtask + ' Stopped')
    # calculate time difference
    if 'on' in cfg[subtitle]:
      sec = int(action_time - float(cfg[subtitle]['on']))
      print("Duration: " + str(dt.timedelta(seconds=sec)))
      days = sec/60/60/24

      if args.subtask != " ":
        if args.note == None:
          note = ""
        else: note = args.note
        writeFile(task, today, days, subtask, note)
    else:
      print("Error: Corrupted data")

  cfg_insert(cfg, task, subtask, action)

#call main function
if __name__ == "__main__":
  main()
