import os
from github import Github
from zipfile import ZipFile
import zipfile
from savefiles import backup, get_days, get_all_names, get_date_string
from dbinterface import get_setting

from savefiles import delete_folder


BUFSIZE = 1024

def backup_full(upload=True):
  #print("-----------starting backup-----------")
  backup()
  
  if upload:
    save_to_github("backup")



def is_new_day():
  file_names = get_all_names(path="backup/")
  file_names.sort(key=lambda x: get_days(x))
  last_day = get_days(file_names[-1])
  today_day = get_days(get_date_string())
  return last_day != today_day


def save_to_github(message):
  
  if not os.path.exists("savedata"):
    print("savedata folder does not exist")
    return
  
  token = get_setting("github_token")
  if token is None:
    return
  #print(f"github: {token}")
  g = Github(token)
  if g is None:
    print("github token not valid")
    return
  
  repo_name = get_setting("save_repo")
  repo = g.get_user().get_repo(repo_name)
  all_files = []
  contents = repo.get_contents("")
  #shutil.make_archive("backup", 'zip', "savedata/")
  d = "backup"
  try:
    os.remove("backup.zip")
  except:
    print("file backup.zip not found")
    
  with ZipFile(d + '.zip', "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for root, _, filenames in os.walk("savedata/"):
      for name in filenames:
        name = os.path.join(root, name)
        name = os.path.normpath(name)
        zf.write(name, name)
    zf.close()
    
  while contents:
    file_content = contents.pop(0)
    if file_content.type == "dir":
      contents.extend(repo.get_contents(file_content.path))
    else:
      file = file_content 
      all_files.append(str(file).replace('ContentFile(path="','').replace('")',''))

  
  content = repo.get_contents(all_files[0])
  
  try:
    os.remove("backup.zip")
  except:
    print("backup.zip not found")
  
  zip_savedata()
  
  data = open("backup.zip", "rb").read()
  
  repo.update_file("backup.zip", message, data, content.sha)
  return
  
def zip_savedata():
  with ZipFile("backup.zip", "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for root, _, filenames in os.walk("savedata/"):
      for name in filenames:
        name = os.path.join(root, name)
        name = os.path.normpath(name)
        zf.write(name, name)
    zf.close()

