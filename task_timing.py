import argparse
import re
import configparser

def time_off():
  print("time off") 

def time_on():
  print("time on") 

def new_subtask(): 
  print("new subtask") 

def new_task():
  print("new task") 

def set_spreadsheet():
  print("set spreadsheet") 
  

def main():
  parser = argparse.ArgumentParser(description='Time tasks and subtasks using google sheets api')
  onoff = parser.add_mutually_exclusive_group(required=False)
  onoff.add_argument('-on', metavar=('TASK','SUBTASK'), nargs=2)
  onoff.add_argument('-off', metavar=('TASK','SUBTASK', 'NOTE'), nargs=3)
  parser.add_argument('--spreadsheet', metavar='ID', help='The spreadsheet to modify') 
 
  args = parser.parse_args()
  cfg = configparser.ConfigParser()
  cfg.read('task_timing.cfg')

  URL = ''
  if args.spreadsheet != None:
    if 'CONFIG' in cfg and 'URL' in cfg['CONFIG']:
      cfg['CONFIG']['URL'] = args.spreadsheet
    else:
      cfg['CONFIG'] = { 'URL' : args.spreadsheet }     
 
  if 'CONFIG' in cfg and 'URL' in cfg['CONFIG']:
    URL = cfg['CONFIG']['URL']
    print(URL)
 
  else:
    print('error: No spreadsheet specified. Used --spreadsheet to pass ID')
    cfg['CONFIG'] = { 'URL' : '' }     

  with open('task_timing.cfg', 'w') as cfg_file:
    cfg.write(cfg_file) 



if __name__ == "__main__":
  main()
