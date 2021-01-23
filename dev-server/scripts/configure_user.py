#!/usr/bin/python

"""
Configure user
"""

import os
import shutil
import sys
import json
import docker
import bcrypt
import logging
import crypt
import codecs
import typing
import spwd
from pathlib              import Path
from getpass              import getpass
from subprocess           import run, call
#from ansible.modules.user import User


### Adapted from https://github.com/jkpubsrc/python-module-jk-etcpasswd
class PwdRecord(object):

	def __init__(self, userName:str, userID:int, groupID:int, description:str, homeDirPath:str, shellDirPath:str):
		assert isinstance(userName, str)
		assert isinstance(userID, int)
		assert isinstance(groupID, int)
		assert isinstance(description, str)
		assert isinstance(homeDirPath, str)
		assert isinstance(shellDirPath, str)

		self.userName = userName
		self.userID = userID
		self.groupID = groupID
		self.description = description
		self.homeDirPath = homeDirPath
		self.shellDirPath = shellDirPath
		self.secretPwdHash = None
		self.extraShadowData = None

	def toJSON(self) -> dict:
		ret = {
			"userName": self.userName,
			"userID": self.userID,
			"groupID": self.groupID,
			"description": self.description,
			"homeDirPath": self.homeDirPath,
			"shellDirPath": self.shellDirPath,
			"secretPwdHash": self.secretPwdHash,
			"extraShadowData": self.extraShadowData,
		}
		return ret

	@staticmethod
	def createFromJSON(j:dict):
		assert isinstance(j, dict)
		ret = PwdRecord(j["userName"], j["userID"], j["groupID"], j["description"], j["homeDirPath"], j["shellDirPath"]) 
		ret.secretPwdHash = j["secretPwdHash"]
		ret.extraShadowData = j["extraShadowData"]
		return ret


class PwdFile(object):

	def __init__(self, pwdFile:str = "/etc/passwd", shadowFile:str = "/etc/shadow", pwdFileContent:str = None, shadowFileContent:str = None, bTest:bool = False, jsonData:dict = None):
		self.__records = []					# stores PwdRecord objects
		self.__recordsByUserName = {}		# stores str->PwdRecord

		if jsonData is None:
			# regular instantiation
			self.__pwdFilePath = pwdFile
			self.__shadowFilePath = shadowFile

			if pwdFileContent is None:
				with codecs.open(pwdFile, "r", "utf-8") as f:
					pwdFileContent = f.read()

			if shadowFileContent is None:
				with codecs.open(shadowFile, "r", "utf-8") as f:
					shadowFileContent = f.read()

			lineNo = -1
			for line in pwdFileContent.split("\n"):
				lineNo += 1
				if not line:
					continue

				line = line.rstrip("\n")
				items = line.split(":")
				if (len(items) != 7) or (items[1] != 'x'):
					raise Exception("Line " + str(lineNo + 1) + ": Invalid file format: " + pwdFile)
				r = PwdRecord(items[0], int(items[2]), int(items[3]), items[4], items[5], items[6])
				self.__records.append(r)
				self.__recordsByUserName[r.userName] = r

			lineNo = -1
			for line in shadowFileContent.split("\n"):
				lineNo += 1
				if not line:
					continue

				line = line.rstrip("\n")
				items = line.split(":")
				if len(items) != 9:
					raise Exception("Line " + str(lineNo + 1) + ": Invalid file format: " + shadowFile)
				r = self.__recordsByUserName.get(items[0])
				if r is None:
					raise Exception("Line " + str(lineNo + 1) + ": User \"" + items[0] + "\" not found! Invalid file format: " + shadowFile)
				r.secretPwdHash = items[1]
				r.extraShadowData = items[2:]

			if bTest:
				self._compareDataTo(
					pwdFile = pwdFile,
					shadowFile = shadowFile,
					pwdFileContent = pwdFileContent,
					shadowFileContent = shadowFileContent,
				)

		else:
			# deserialization
			assert jsonData["pwdFormat"] == 1

			self.__pwdFilePath = jsonData["pwdFilePath"]
			self.__shadowFilePath = jsonData["pwdShadowFilePath"]

			for jRecord in jsonData["pwdRecords"]:
				r = PwdRecord.createFromJSON(jRecord)
				self.__records.append(r)
				self.__recordsByUserName[r.userName] = r

	def toJSON(self) -> dict:
		ret = {
			"pwdFormat": 1,
			"pwdFilePath": self.__pwdFilePath,
			"pwdShadowFilePath": self.__shadowFilePath,
			"pwdRecords": [ r.toJSON() for r in self.__records ],
		}
		return ret

	@staticmethod
	def createFromJSON(j:dict):
		assert isinstance(j, dict)
		return PwdFile(jsonData=j)

	# This method verifies that the data stored in this object reproduces the exact content of the password files in "/etc".
	# An exception is raised on error.
	def _compareDataTo(self, pwdFile:str = None, shadowFile:str = None, pwdFileContent:str = None, shadowFileContent:str = None):
		if pwdFileContent is None:
			if pwdFile is None:
				pwdFile = self.__pwdFilePath
			with codecs.open(pwdFile, "r", "utf-8") as f:
				pwdFileContent = f.read()

		if shadowFileContent is None:
			if shadowFile is None:
				shadowFile = self.__shadowFilePath
			with codecs.open(shadowFile, "r", "utf-8") as f:
				shadowFileContent = f.read()

		contentPwdFile, contentShadowFile = self.toStringLists()

		lineNo = -1
		for line in pwdFileContent.split("\n"):
			lineNo += 1
			if not line:
				continue

			line = line.rstrip("\n")
			if line != contentPwdFile[lineNo]:
				print("--      Line read: " + repr(line))
				print("-- Line generated: " + repr(contentPwdFile[lineNo]))
				raise Exception("Line " + str(lineNo + 1) + ": Lines differ in file: " + pwdFile)

		lineNo = -1
		for line in shadowFileContent.split("\n"):
			lineNo += 1
			if not line:
				continue

			line = line.rstrip("\n")
			if line != contentShadowFile[lineNo]:
				print("--      Line read: " + repr(line))
				print("-- Line generated: " + repr(contentShadowFile[lineNo]))
				raise Exception("Line " + str(lineNo + 1) + ": Lines differ in file: " + shadowFile)

	# Write the content to the password files in "/etc".
	def store(self, pwdFile:str = None, shadowFile:str = None):
		if pwdFile is None:
			pwdFile = self.__pwdFilePath
		if shadowFile is None:
			shadowFile = self.__shadowFilePath

		contentPwdFile, contentShadowFile = self.toStrings()

		with codecs.open(pwdFile, "w", "utf-8") as f:
			os.fchmod(f.fileno(), 0o644)
			f.write(contentPwdFile)

		with codecs.open(shadowFile, "w", "utf-8") as f:
			os.fchmod(f.fileno(), 0o640)
			f.write(contentShadowFile)

	def toStrings(self) -> typing.Tuple[str,str]:
		contentPwdFile = ""
		contentShadowFile = ""

		for r in self.__records:
			contentPwdFile += r.userName + ":x:" + str(r.userID) + ":" + str(r.groupID) + ":" + r.description + ":" + r.homeDirPath + ":" + r.shellDirPath + "\n"
			contentShadowFile += r.userName + ":" + r.secretPwdHash + ":" + ":".join(r.extraShadowData) + "\n"

		return contentPwdFile, contentShadowFile

	def toStringLists(self) -> typing.Tuple[list,list]:
		contentPwdFile = []
		contentShadowFile = []

		for r in self.__records:
			contentPwdFile.append(r.userName + ":x:" + str(r.userID) + ":" + str(r.groupID) + ":" + r.description + ":" + r.homeDirPath + ":" + r.shellDirPath)
			contentShadowFile.append(r.userName + ":" + r.secretPwdHash + ":" + ":".join(r.extraShadowData))

		return contentPwdFile, contentShadowFile

	def get(self, userNameOrID:typing.Union[str,int]) -> typing.Union[PwdRecord,None]:
		if isinstance(userNameOrID, str):
			return self.__recordsByUserName.get(userNameOrID, None)
		elif isinstance(userNameOrID, int):
			for r in self.__records:
				if r.userID == userNameOrID:
					return r
			return None
		else:
			raise Exception("Invalid data specified for argument 'userNameOrID': " + repr(userNameOrID))

def check_user_exists(username):
     exists = str()
     user_records = PwdFile().toJSON().get("pwdRecords")

     for user in user_records:
          if user.get("userName") == username:
               print(json.dumps(user, indent = 4))
               exists = "yes"
               break
          else:
               exists = "no"
     return exists

def run_pass_change(username, hash):
     log.info(f"new password hash: '{hash}'")
     cmd = ['usermod', '-p', hash, username]
     return_code = call(cmd)

     if return_code == 0:
          log.info('password change: success')
          return 'success'
     else:
          log.info('password change: error')
          return 'error'


def check_current_pass(username):
     current_password_hash = spwd.getspnam(username).sp_pwdp
     if current_password_hash == '':
          log.info("current password: empty")
          return 'empty'
     if not current_password_hash == '':
          log.info("current password: set")
          return 'set'
     else:
          log.info("current password: unknown error")
          return 'error'

def check_old_pass(username, password):
     current_password_hash = spwd.getspnam(username).sp_pwdp
     old_password_hash = crypt.crypt(password, current_password_hash)

     if current_password_hash == old_password_hash:
          log.info(f"old password '{password}': valid")
          return 'valid'
     elif not current_password_hash == old_password_hash:
          log.info(f"old password '{password}': invalid")
          return 'invalid'
     else:
          log.info("old password: unknown error")
          return 'error'

def change_pass(username, old_password, new_password):
     user_exists = check_user_exists(username)
     if user_exists == 'yes':
          current_password_hash = spwd.getspnam(username).sp_pwdp
          log.info(f"current password hash: '{current_password_hash}'")
          log.info(f"new password: '{new_password}'")
          current_pass = check_current_pass(username)

          if current_pass  == 'empty':
               salt = crypt.mksalt(crypt.METHOD_SHA512)
               new_password_hash = crypt.crypt(new_password, salt)
               run_pass_change(username, new_password_hash)

     elif current_pass == 'set':
          old_pass = check_old_pass(username, old_password)
          if old_pass == 'valid':
               new_password_hash = crypt.crypt(new_password, current_password_hash)
               if new_password_hash == current_password_hash:
                    log.info("new password same as current")
               else:
                    run_pass_change(username, new_password_hash)
          elif old_pass == 'invalid':
               return 1
          elif old_pass == 'error':
               return 126
     elif old_pass == 'error':
          return 126
     elif user_exists == 'no':
          log.info(f"user: '{username}' does not exist")
          return 1
     else:
          log.info("unknown error")

# add user function 
#def add_user(): 

#def add_user(): 
  
     # Ask for the input 
#     username = input("Enter Username ")  
  
     # Asking for users password 
#     password = getpass()
         
#     try: 
         # executing useradd command using subprocess module 
#         run(['useradd', '-p', password, username ])       
#     except: 
#         print(f"Failed to add user.")                      
#         sys.exit(1)


### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Read system envs
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
#ENV_USER = os.getenv("USER", "coder")
ENV_USER = os.getenv("SUDO_USER", "coder")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")

### Clean up envs
application = "config_user"
host_fqdn = ENV_HOSTNAME


#@TODO: add this later to enable proxy's base url
#clients = docker.from_env()
#host_container = clients.containers.get(ENV_HOSTNAME)
#host = host_container.name

### Set config and data paths
config_dir = os.path.join("/etc", application)
storage = os.path.join(config_dir, "storage")
if not os.path.exists(config_dir): os.mkdir(config_dir)
if not os.path.exists(storage): os.mkdir(storage)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)

### Generate password hash
password = ENV_WORKSPACE_AUTH_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
#log.info(f"{application} password: '{ENV_WORKSPACE_AUTH_PASSWORD}'")
#log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password


change_pass(ENV_USER, "password", ENV_WORKSPACE_AUTH_PASSWORD)

### Write config file
#config_path = os.path.join(config_dir, f"{application}.json")
#config_json = json.dumps(config_file, indent = 4)

#with open(config_path, "w") as f: 
#    f.write(config_json)

#log.info(f"{application} config:")
#log.info(subprocess.run(["cat", config_path]))