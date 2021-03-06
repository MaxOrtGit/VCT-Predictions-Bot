import os
from github import Github
from zipfile import ZipFile
import zipfile
from savefiles import backup, get_days, get_all_names, get_date_string
from dbinterface import get_setting
import atexit

from savefiles import delete_folder




BUFSIZE = 1024

def backup_full():
  save_to_github("backup")
  
atexit.register(backup_full)


def is_new_day():
  file_names = get_all_names(path="backup/")
  file_names.sort(key=lambda x: get_days(x))
  last_day = get_days(file_names[-1])
  today_day = get_days(get_date_string())
  return last_day != today_day


def pull_from_github():
  token = get_setting("github_token")
  g = Github(token)
  repo_name = get_setting("save_repo")
  repo = g.get_user().get_repo(repo_name)
  contents = repo.get_contents("")
  all_files = []
  while contents:
    file_content = contents.pop(0)
    if file_content.type == "dir":
      contents.extend(repo.get_contents(file_content.path))
    else:
      file = file_content 
      all_files.append(str(file).replace('ContentFile(path="','').replace('")',''))
  content = repo.get_contents(all_files[0])
  delete_folder("", "")
  #get savedata.fb from zip
  with open("gitbackup.zip", "wb") as f:
    f.write(content.decoded_content)
  #unzip savedata.fb
  with ZipFile("gitbackup.zip", "r") as zf:
    zf.extractall("")
  #remove savedata.fb
  os.remove("gitbackup.zip")
  print("Pulled from github.")


def save_to_github(message):
  token = get_setting("github_token")
  #print(f"github: {token}")
  g = Github(token)
  
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

  try:
    os.remove("gitbackup.zip")
  except:
    print("file gitbackup.zip not found")
    
  content = repo.get_contents(all_files[0])
  save_savedata_from_github(content)

  
  if are_equivalent("backup.zip", "gitbackup.zip") and not is_new_day(): 
    print("Local and github are the same.")
    return
  
  print("\n-----------Backing Up-----------\n")

  
  backup()
  
  print("\n-----------Uploading-----------\n")
  
  try:
    os.remove("backup.zip")
  except:
    print("second file backup.zip not found")
  
  with ZipFile(d + '.zip', "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for root, _, filenames in os.walk("savedata/"):
      for name in filenames:
        name = os.path.join(root, name)
        name = os.path.normpath(name)
        zf.write(name, name)
    zf.close()
    
  
  data = open("backup.zip", "rb").read()
  
  repo.update_file("backup.zip", message, data, content.sha)
  print("Backed up to git.")
  return
  
def zip_savedata():
  with ZipFile("backup.zip", "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for root, _, filenames in os.walk("savedata/"):
      for name in filenames:
        name = os.path.join(root, name)
        name = os.path.normpath(name)
        zf.write(name, name)
    zf.close()

def save_savedata_from_github(content=None):
  if content is None:
    token = get_setting("github_token")
    g = Github(token)
    repo_name = get_setting("save_repo")
    repo = g.get_user().get_repo(repo_name)
    contents = repo.get_contents("")
    all_files = []
    while contents:
      file_content = contents.pop(0)
      if file_content.type == "dir":
        contents.extend(repo.get_contents(file_content.path))
      else:
        file = file_content 
        all_files.append(str(file).replace('ContentFile(path="','').replace('")',''))
    content = repo.get_contents(all_files[0])
    
  with open("gitbackup.zip", "wb") as f:
    f.write(content.decoded_content)
  


def are_equivalent(filename1, filename2):
    """Compare two ZipFiles to see if they would expand into the same directory structure
    without actually extracting the files.
    """
  
    if (not zipfile.is_zipfile(filename1)) or (not zipfile.is_zipfile(filename2)):
      print("not valid zip", f"{zipfile.is_zipfile(filename1)}, {zipfile.is_zipfile(filename2)}")
      return False
    
    with ZipFile(filename1, 'r') as zip1, ZipFile(filename2, 'r') as zip2:
      
      # Index items in the ZipFiles by filename. For duplicate filenames, a later
      # item in the ZipFile will overwrite an ealier item; just like a later file
      # will overwrite an earlier file with the same name when extracting.
      zipinfo1 = {info.filename:info for info in zip1.infolist()}
      zipinfo2 = {info.filename:info for info in zip2.infolist()}
      
      # Do some simple checks first
      # Do the ZipFiles contain the same the files?
      if zipinfo1.keys() != zipinfo2.keys():
        return False
      
      # Do the files in the archives have the same CRCs? (This is a 32-bit CRC of the
      # uncompressed item. Is that good enough to confirm the files are the same?)
      if any(zipinfo1[name].CRC != zipinfo2[name].CRC for name in zipinfo1.keys()):
        return False
      
      # Skip/omit this loop if matching names and CRCs is good enough.
      # Open the corresponding files and compare them.
      for name in zipinfo1.keys():
          
        # 'ZipFile.open()' returns a ZipExtFile instance, which has a 'read()' method
        # that accepts a max number of bytes to read. In contrast, 'ZipFile.read()' reads
        # all the bytes at once.
        with zip1.open(zipinfo1[name]) as file1, zip2.open(zipinfo2[name]) as file2:
          
          while True:
            buffer1 = file1.read(BUFSIZE)
            buffer2 = file2.read(BUFSIZE)
            
            if buffer1 != buffer2:
              return False
            
            if not buffer1:
              break
                   
      return True
