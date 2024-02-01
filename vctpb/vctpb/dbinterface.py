import jsonpickle

from sqlaobjs import Session 
from sqlalchemy import select, desc

from Match import Match
from User import User
from Bet import Bet
from Team import Team
from Tournament import Tournament
from Color import Color
from Channels import Channels

from configparser import ConfigParser

import random
import secrets
from utils import get_date_string, get_date

async def delete_all_messages(ids, bot):
  for id in ids:
    try:
      channel = await bot.fetch_channel(id[1])
      msg = await channel.fetch_message(id[0])
      await msg.delete()
    except Exception:
      print(id, "no msg found")

def get_all_db(table_name, session=None):
  if session is None:
    with Session.begin() as session:
      return list(reversed(session.scalars(select(eval(table_name))).all()))
  return list(reversed(session.scalars(select(eval(table_name))).all()))
  
  
def get_from_db(table_name, code, session):
  return session.get(eval(table_name), code, populate_existing=True)
    
    
def get_new_db(tabel_name, session=None):
  if session is None:
    with Session.begin() as session:
      return get_new_db(tabel_name, session)
  if tabel_name == "Match":
    order_by = Match.date_created
  if tabel_name == "Bet":
    order_by = Bet.date_created
  return session.scalars(select(eval(tabel_name)).order_by(desc(order_by))).first()
    
    
def get_condition_db(table_name, condition, session=None):
  if session is None:
    with Session.begin() as session:
      return get_condition_db(table_name, condition, session)
  if isinstance(condition, str):
    condition = eval(condition)
  return session.scalars(select(eval(table_name)).where(condition)).all()

    
def get_mult_from_db(table_name, codes, session=None):
  if session is None:
    with Session.begin() as session:
      return get_mult_from_db(table_name, codes, session)
  if table_name == "Color" or table_name == "Team" or table_name == "Tournament":
    return session.scalars(select(Color).where(Color.name.in_(codes))).all()
  else:
    obj = eval(table_name)
    return session.scalars(select(obj).where(obj.code.in_(codes))).all()


async def delete_from_db(ambig, bot=None, table_name=None, session=None):
  #wont update relationships
  if isinstance(ambig, str) or isinstance(ambig, int):
    return await delete_from_db(session.get(eval(table_name), ambig), bot, session=session)
  
  if session is None:
    with Session.begin() as session:
      return await delete_from_db(ambig, bot, session=session)
  
  if bot is not None:
    if isinstance(ambig, Match):
      for bet in ambig.bets:
        await delete_all_messages(bet.message_ids, bot)
      await delete_all_messages(ambig.message_ids, bot)
    elif isinstance(ambig, Bet):
      await delete_all_messages(ambig.message_ids, bot)
      
      
  session.delete(ambig)
  #session.expire_all()
    
    
def add_to_db(obj, session=None):
  #will update relationships
  if session is None:
    with Session.begin() as session:
      return add_to_db(obj, session)
  session.add(obj)
  session.expire_all()


def is_key_in_db(table_name, key, session=None):
  if session is None:
    with Session.begin() as session:
      return is_key_in_db(table_name, key, session)
  return session.get(eval(table_name), key, populate_existing=True) is not None


def is_condition_in_db(table_name, condition, session=None):
  if session is None:
    with Session.begin() as session:
      return is_condition_in_db(table_name, condition, session)
  return session.execute(select(eval(table_name)).where(condition)).first() is not None
      
      
def get_channel_from_db(channel_name, session=None):
  if session is None:
    with Session.begin() as session:
      return get_channel_from_db(channel_name, session)
    
  channels = session.scalars(select(Channels)).one()
  if channels.bet_channel_id == -1 or channels.match_channel_id == -1 or channels.result_channel_id == -1:
    print("\n\n\n\n\n\n\n-----------Set all channels with /assign-----------\n\n\n\n\n\n\n")
    return None
  if channel_name == "bet":
    return channels.bet_channel_id
  elif channel_name == "match":
    return channels.match_channel_id
  elif channel_name == "result":
    return channels.result_channel_id
  else:
    return None
  
def set_channel_in_db(channel_name, channel_value, session=None):
  if session is None:
    with Session.begin() as session:
      return set_channel_in_db(channel_name, channel_value, session)
  channels = session.scalars(select(Channels)).one()
  if channel_name == "bet" or channel_name == "bet_channel_id":
    channels.bet_channel_id = channel_value
  elif channel_name == "match" or channel_name == "match_channel_id":
    channels.match_channel_id = channel_value
  elif channel_name == "result" or channel_name == "result_channel_id":
    channels.result_channel_id = channel_value
                           
                          
def get_setting(setting_name):
  #setting_names: "discord_token", "github_token", "guild_ids", "save_repo"
  try:
    configur = ConfigParser()
    configur.read('settings.ini')
    val = configur.get('settings', setting_name)
    if setting_name == "guild_ids":
      return jsonpickle.decode(val)
    return val
  except:
    return None

def set_setting(setting_name, setting_value):
  configur = ConfigParser()
  configur.read('settings.ini')
  configur.set('settings', setting_name, setting_value)
  with open('settings.ini', 'w') as configfile:
    configur.write(configfile)
    
    
def get_unique_code(prefix, session=None):
  if session is None:
    with Session.begin() as session:
      return get_unique_code(prefix, session)
  all_objs = get_all_db(prefix, session)
  codes = [str(k.code) for k in all_objs]
  code = ""
  copy = True
  while copy:
    copy = False

    random.seed()
    code = str(secrets.token_hex(4))
    for k in codes:
      if k == code:
        copy = True
  return code