import argparse
import configparser
import time
import datetime as dt
import os

from datetime import date, datetime
from spreadsheet_helper import *

path = os.environ['HOME'] + '/.timer_records/';

# use google api to update spreadsheet
def api_push(url):
  data = []
  api = API(url)
  i = 0

  #api call to create spreadsheet needed before anything else
  for filename in os.listdir(path):
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
    os.remove(path+filename)

  exit(0)
  
# insert into config, or create section if required
def cfg_insert(cfg, section, var, val):
  if section in cfg:
    cfg[section][var] = val
  else:
    cfg[section] = { var : val }     
  with open('task_timing.cfg', 'w') as cfg_file:
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
  ex = parser.add_mutually_exclusive_group(required=False)
  ex.add_argument('-on', metavar=(' TASK','SUBTASK'), nargs=2)
  ex.add_argument('-off', metavar=('TASK','SUBTASK'), nargs=2)
  parser.add_argument('-n','--note', metavar='"NOTE"',  help='Store in spreadsheet with this note. If omitted spreadsheet will not be updated.') 
  ex.add_argument('--spreadsheet', metavar='URL', help='The spreadsheet to modify') 
  ex.add_argument('--push', action='store_true', help='Update spreadsheet with recorded times')
  ex.add_argument('--reset', action='store_true', help='Clear all current timers')
 
  args = parser.parse_args()

  # read config file
  cfg = configparser.ConfigParser()
  cfg.read('task_timing.cfg')

  # reset current timers. Cancels all running timers
  if args.reset:
    clear_cfg = configparser.ConfigParser()
    clear_cfg['CONFIG'] = cfg['CONFIG']

    with open('task_timing.cfg', 'w') as cfg_file:
      clear_cfg.write(cfg_file) 
    exit(0)

  URL = ''
  if args.spreadsheet != None:
    cfg_insert(cfg, 'CONFIG', 'URL', args.spreadsheet)
 
  if 'CONFIG' in cfg and 'URL' in cfg['CONFIG']:
    URL = cfg['CONFIG']['URL']
  # Push timers to the spreadsheet.
    if args.push:
      api_push(URL)
 
  else:
    print('No spreadsheet specified. Used --spreadsheet to pass ID')
    cfg['CONFIG'] = { 'URL' : '' }     

  if args.on == None and args.off == None:
    if (args.spreadsheet == None):
      print("No operation provided! Try -on, -off or -h")
    exit(0)
  
  # add action
  if args.off == None:
    args.on.append('on');
    action = args.on
  else:
    args.off.append('off');
    action = args.off

  action[0] = action[0].title()
  action[1] = action[1].title()
  today     = date.today().strftime("%d/%m/%Y")
 
  cfg_insert(cfg, 'TASKS', 'TODAY', today)

  subtitle = action[0]+'_'+action[1]
  action_time = time.time()

  cfg_insert(cfg, subtitle, action[2], str(action_time))

  if action[2] == 'on':
    print('Timer for ' + action[0] + ' - ' + action[1] + ' Running')
  elif cfg[action[0]][action[1]] == 'on': 
    print('Timer for '+ action[0] + ' - ' + action[1] + ' Stopped')
    if 'on' in cfg[subtitle]:
      sec = int(action_time - float(cfg[subtitle]['on']))
      print("Duration: " + str(dt.timedelta(seconds=sec)))
      days = sec/60/60/24

      if args.note != None:
        writeFile(action[0], today, days, action[1], args.note)
    else:
      print("Error: Corrupted data")

  cfg_insert(cfg, action[0], action[1], action[2])

if __name__ == "__main__":
  main()
