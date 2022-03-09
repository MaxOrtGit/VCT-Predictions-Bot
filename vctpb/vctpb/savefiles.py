import os
from datetime import datetime
from pytz import timezone
import jsonpickle
import sys
import shutil
from replit import db

def get_date_string():
  central = timezone('US/Central')
  return datetime.now(central).strftime("%Y-%m-%d-%H-%M-%S")

#year, month, day, hour, min, sec = date_string_to_vars(date_sting)
def date_string_to_vars(date_string):
  return date_string.split("-")

def get_seconds(date_string):
  hour, min, sec = (date_string_to_vars(date_string))[-3:]
  return int(hour) * 3600 + int(min) * 60 + int(sec)

def get_days(date_string):
  year, month, day = (date_string_to_vars(date_string))[:3]
  day_of_year = datetime(int(year), int(month), int(day))
  return(day_of_year - datetime(1970,1,1)).days

def get_all_names(path="files/", ext=False):
  names = os.listdir(path)
  if ext:
    return names
  return [os.path.splitext(name)[0] for name in names]

def get_prefix(prefix, path="files/", ext=False):
  names = os.listdir(path)
  prefix_names = [name for name in names if name.startswith(prefix)]
  if ext:
    return prefix_names
  return [os.path.splitext(prefix_name)[0] for prefix_name in prefix_names]

def get_file(name, path="files/"):
  rs = jsonpickle.decode(db.get_raw(name))
  path_and_file = f"{path}{name}.txt"
  r = open(path_and_file, "r")
  fs = jsonpickle.decode(r.read())
  if fs != rs:
    print(type(fs), type(rs))
    print(str(fs)[:50], str(rs)[:50])
    save_file(name, rs, False)
    create_error_file("get error", f"get not the same as DB {name} to {path_and_file}.")
    
  return rs
      

def save_file(name, obj, savekey, path="files/"):
  if savekey:
    db[name] = obj
  path_and_file = f"{path}{name}.txt"
  f = open(path_and_file, "w")
  f.write(jsonpickle.encode(obj))
  f.close()

  
  r = open(path_and_file, "r")
  fs = jsonpickle.decode(r.read())
  if fs != obj:
    create_error_file("save error", f"Didn't save {name} to {path_and_file}.")
  
def delete_file(name, path):
  path_and_file = f"{path}{name}.txt"
  print(f"deleting {path_and_file}")


def delete_folder(name, path):
  path_and_file = f"{path}{name}"
  try:
    shutil.rmtree(path_and_file)
    print(f"deleted folder {path_and_file}")
  except OSError as e:
    create_error_file("delete error", f"couldn't remove {name} path {path_and_file}.")
    print("Error: %s - %s." % (e.filename, e.strerror))


def create_error_file(name, s):
  datestring = get_date_string()
  save_file(f"{name}-{datestring}", f"{s}\n{datestring}", False, path="errors/")
  print(name, s)


def equate(x):
  #standard
  sy = (x) ** (1/2) 
  #initial boost
  iby = -20/(x+1)
  y = int(sy + iby)
  return y



def delete_old_backup():
  file_names = get_all_names(path="backup/")
  date_string = get_date_string()
  old_file_names = []
  for file_name in file_names:
    if not file_name.startswith(date_string[:10]):
      old_file_names.append(file_name)
      
  #all files from the day deleted
  file_days_dict = {}
  for old_file_name in old_file_names:
    ymd = old_file_name[:10]
    if (day_list := file_days_dict.get(ymd)) is None:
      file_days_dict[ymd] = [old_file_name]
      continue
    day_list.append(old_file_name)
    file_days_dict[ymd] = day_list
  
  file_days = list(file_days_dict.items())
  singles = []
  deleted = []
  for file_day in file_days:
    if len(file_day[1]) == 1:
      singles.append(file_day[1][0])
      continue
    times = []
    for file_name in file_day[1]:
      times.append((file_name, get_seconds(file_name)))
      
    times.sort(key=lambda x: x[1])
    for time_t in times[:-1]:
      deleted.append(time_t[0])
      delete_folder(time_t[0], "backup/")
    singles.append(times[-1][0])

  print("day delete done")
    
  singles.sort(reverse=True)
  day = []
  for single in singles:
    day.append((single, get_days(single)))
  
  #first is name second is days since flipped
  high = day[0][1]
  dates_t = [(date[0], high - date[1] + 1) for date in day]
  
  layers = {}
  for date_t in dates_t:
    y = equate(date_t[1])
    if y in layers:
      layers[y].append(date_t[0])
    else:
      layers[y] = [date_t[0]]

  layer_list = list(layers.items())
  points = []
  for layer in layer_list:
    if len(layer[1]) > 1:
      for name in layer[1][:-1]:
        delete_file(name, "backup/")

  print("done delete backup")
        
        

