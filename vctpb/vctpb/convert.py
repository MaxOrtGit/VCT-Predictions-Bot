
from Match import Match
from Bet import Bet
from User import User
import discord
from dbinterface import get_from_db, get_condition_db
from sqlalchemy import literal
from sqlaobjs import Session


def ambig_to_obj(ambig, prefix, session=None):
  if isinstance(ambig, int) or isinstance(ambig, str):
    obj = get_from_db(prefix, ambig, session)
  elif isinstance(ambig, discord.Member):
    obj = get_from_db(prefix, ambig.id, session)
  elif isinstance(ambig, User) or isinstance(ambig, Match) or isinstance(ambig, Bet):
    obj = ambig
  else:
    obj = None
    print(ambig, type(ambig))
  return obj

def get_user_from_at(id, session=None):
  uid = id.replace("<", "")
  uid = uid.replace(">", "")
  uid = uid.replace("@", "")
  uid = uid.replace("!", "")
  if uid.isdigit():
    return get_user_from_id(int(uid), session)
  else:
    return None

def get_user_from_id(id, session=None):
  return get_from_db("User", id, session)
  

def id_to_metion(id):
  return f"<@!{id}>"


  
async def get_user_from_ctx(ctx, user, session=None):
  if user is None:
    user = ctx.author
  user = get_from_db("User", user.id, session)
  if user is None:
    await ctx.respond("User not found. To create an account do /balance", ephemeral = True)
  return user


async def user_from_autocomplete_tuple(ctx, t_list, text, prefix, session=None):
  
  objs = [t[1] for t in t_list if text == t[0]]
  print(objs)
  if len(objs) >= 2:
    print("More than one of text found", objs)
    if ctx is not None:
      await ctx.respond(f"Error please @pig. Try typing in code instead.")
      #2 with the same name
    return None
  if len(objs) == 0:
    obj = get_from_db(prefix, text, session)
  else:
    obj = objs[0]
    
  if obj == [] or obj is None:
    if ctx is not None:
      await ctx.respond(f"{prefix.capitalize()} ID not found.", ephemeral = True)
    return None
  return obj

async def get_member_from_id(guild, id):
  member = guild.get_member(id)
  if member is None:
    member = await guild.fetch_member(id)
  return member


def get_user_from_username(username, session=None):
  return get_condition_db("User", User.username == username, session)


def usernames_to_users(usernames, session=None):
  return get_condition_db("User", literal(usernames).contains(User.username), session)