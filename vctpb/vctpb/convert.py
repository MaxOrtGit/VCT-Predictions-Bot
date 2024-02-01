import discord
from dbinterface import get_from_db, get_condition_db, get_all_db
from sqlalchemy import literal
from sqlaobjs import Session
import asyncio

from Match import Match
from Bet import Bet
from User import User
from Tournament import Tournament
from Team import Team

def user_id_ambig(user):
  if isinstance(user, int):
    return user
  elif isinstance(user, User):
    return user.code
  elif isinstance(user, discord.Member):
    return user.id

def t_list_ambig_to_name_objs(ambig, session=None, user=None, naming_type=1):
  if len(ambig) == 0:
    return []
  elif isinstance(ambig[0], Bet):
    return bets_to_name_objs(ambig, session, user)
  elif isinstance(ambig[0], Match):
    return matches_to_name_objs(ambig, naming_type)
  elif isinstance(ambig[0], Tournament):
    return tournaments_to_name_objs(ambig)
  elif isinstance(ambig[0], Team):
    return team_to_name_objs(ambig)
  elif isinstance(ambig[0], tuple):
    return ambig

def names_ambig_to_names(ambig, session=None, user=None, naming_type=1):
  #gets the autocomplete names from the ambig list
  if len(ambig) == 0:
    return []
  elif isinstance(ambig[0], str):
    return ambig
  elif isinstance(ambig[0], Bet):
    return bets_to_names(ambig, session, user)
  elif isinstance(ambig[0], Match):
    return matches_to_names(ambig, naming_type)
  elif isinstance(ambig[0], Tournament):
    return tournaments_to_names(ambig)
  elif isinstance(ambig[0], Team):
    return teams_to_names(ambig)
  elif isinstance(ambig[0], tuple):
    return [a[0] for a in ambig]

def get_user_from_id(user, session):
  if isinstance(user, User):
    return user
  id = user_id_ambig(user)
  return get_from_db("User", id, session)

def get_user_from_at(id, session=None):
  uid = id.replace("<", "")
  uid = uid.replace(">", "")
  uid = uid.replace("@", "")
  uid = uid.replace("!", "")
  if uid.isdigit():
    return get_user_from_id(int(uid), session)
  else:
    return None

def id_to_mention(id):
  if id is None:
    return "Bot"
  return f"<@!{id}>"
  
async def get_user_from_ctx(ctx, user=None, session=None, send=True):
  us = user
  if us is None:
    us = ctx.author
  us = get_from_db("User", us.id, session)
  if us is None and send:
    print("user not found")
    await ctx.respond("User not found. To create an account do /balance", ephemeral = True)
  return us


async def obj_from_autocomplete_tuple(ctx, ambig, text, prefix, session=None, user=None, naming_type=1):
  if len(ambig) == 0:
    if ctx is not None:
      #response when no objs found
      if prefix == "Match":
        plural = "matches"
      else:
        plural = prefix.lower() + "s"
      await ctx.respond(f"no {plural} found.", ephemeral = True)
    return None
  else:
    #if objs found
    t_list = t_list_ambig_to_name_objs(ambig, session, user, naming_type)
    #t_list is a list of tuples (name, obj)
    
  #if text is equal to name
  objs = [t[1] for t in t_list if text == t[0]]
  if len(objs) >= 2:
    print("More than one of text found", objs)
    if ctx is not None:
      await ctx.respond(f"2 with same name found please @pig. Try typing in code instead.")
      #2 with the same name
    return None
  if len(objs) == 0:
    obj = get_from_db(prefix, text, session)
  else:
    obj = objs[0]
  
  if (obj == []) or (obj is None):
    if (len(text) == 8) and text.isdigit():
      obj = get_from_db(prefix, text, session)
      if obj is None:
        if ctx is not None:
          await ctx.respond(f"{prefix.capitalize()} ID not found.", ephemeral = True)
        return None
    else:
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


def filter_names(value, ambig, session=None, user=None, naming_type=1):
  if session is None:
    with Session.begin() as session:
      return filter_names(value, ambig, session, user, naming_type)
    
  if len(ambig) == 0:
    return []
  else:
    #get all names from objs (ambig)
    names = names_ambig_to_names(ambig, session, user, naming_type)
    
  value = value.lower()
  value.replace(",", "")
  value_keywords = value.split(" ")
  if len(value_keywords) == 0:
    return [names]
  new_names = []
  for name in names:
    lower_name = name.lower()
    all_in = True
    for value_keyword in value_keywords:
      if value_keyword not in lower_name:
        all_in = False
        break
    if all_in:
      new_names.append(name)
      if len(new_names) == 25:
        break
  return new_names


def add_time_name_objs(name_objs):
  new_name_objs = []
  names = [name for name, _ in name_objs]
  for name_obj in name_objs:
    if names.count(name_obj[0]) == 2:
      new_name_objs.append((f"{name_obj[0]}, {name_obj[1].date_created.strftime('%m/%d')}", name_obj[1]))
    else:
      new_name_objs.append(name_obj)
  return new_name_objs

#naming_type 1 normal, 2 odds
def shorten_match_name(match, naming_type=1):
  if match.winner != 0:
    prefix = "Finished: "
    shortened_prefix = "Fin: "
  else:
    prefix = ""
    shortened_prefix = ""
  
  if naming_type == 1:
    s = f"{prefix}{match.t1} vs {match.t2}, {match.tournament_name}"
    if len(s) >= 95:
      s = f"{shortened_prefix}{match.t1} vs {match.t2}, {match.tournament_name}"
      if len(s) >= 95:
        s = f"{shortened_prefix}{match.t1}/{match.t2}, {match.tournament_name}"
        if len(s) >= 95:
          tsplit = ":".join(match.tournament_name.split(":")[1:])
          s = f"{shortened_prefix}{match.t1}/{match.t2}, {tsplit}"
          if len(s) >= 95:
            s = s[:95]
  elif naming_type == 2:
    s = f"{prefix}{match.t1} vs {match.t2}, {match.t1o} / {match.t2o}, {match.tournament_name}"
    if len(s) >= 95:
      s = f"{shortened_prefix}{match.t1} vs {match.t2}, {match.t1o} / {match.t2o}, {match.tournament_name}"
      if len(s) >= 95:
        s = f"{shortened_prefix}{match.t1}/{match.t2}, {match.t1o} / {match.t2o}, {match.tournament_name}"
        if len(s) >= 95:
          tsplit = ":".join(match.tournament_name.split(":")[1:])
          s = f"{shortened_prefix}{match.t1}/{match.t2}, {match.t1o} / {match.t2o}, {tsplit}"
          if len(s) >= 95:
            s = s[:95]
  return s

def shorten_bet_name(bet, user_id, session=None):
  if session is None:
    with Session.begin() as session:
      return shorten_bet_name(bet, user_id, session)
  if bet.winner != 0:
    prefix = "Finished: "
    shortened_prefix = "Fin: "
  else:
    prefix = ""
    shortened_prefix = ""
  user = bet.user
  
  if (not bet.hidden) or (user_id is None) or (user_id == bet.user_id):
    #visible
    s = f"{prefix}{user.username}: {bet.amount_bet} on {bet.get_team()}"
    if len(s) >= 100:
      s = f"{shortened_prefix}{user.username}: {bet.amount_bet} on {bet.get_team()}"
      if len(s) >= 100:
        s = f"{prefix}{user.username}: {bet.amount_bet} on {bet.get_team().split(' ')[0]}"
        if len(s) >= 100:
          s = f"{shortened_prefix}{user.username}: {bet.amount_bet} on {bet.get_team().split(' ')[0]}"
          if len(s) >= 100:
            s = s[:100]
  else:
    #hidden
    s = f"{prefix}{user.username}: bet on {bet.t1} vs {bet.t2}"
    if len(s) >= 100:
      s  = f"{shortened_prefix}{user.username}: bet on {bet.t1} vs {bet.t2}"
      if len(s) >= 100:
        s1 = f"{prefix}{user.username}: bet on {bet.t1.split(' ')[0]} vs {bet.t2}"
        s2 = f"{prefix}{user.username}: bet on {bet.t1} vs {bet.t2.split(' ')[0]}"
        if s1 > s2:
          s = s2
        else:
          s = s1
        if len(s) >= 100:
          s = f"{prefix}{user.username}: bet on {bet.t1.split(' ')[0]} vs {bet.t2.split(' ')[0]}"
          if len(s) >= 100:
            s = f"{shortened_prefix}{user.username}: bet on {bet.t1.split(' ')[0]} vs {bet.t2.split(' ')[0]}"
            if len(s) >= 100:
              s = s[:100]
  return s

def shorten_tournament_name(tournament):
  if not tournament.active:
    prefix = "Finished: "
    shortened_prefix = "Fin: "
  else:
    prefix = ""
    shortened_prefix = ""
  s = f"{prefix}{tournament.name}"
  if len(s) >= 95:
    s = f"{shortened_prefix}{tournament.name}"
    if len(s) >= 95:
      s = s[:95]
  return s

def get_all_user_bets(user, session=None):
  return get_condition_db("Bet", Bet.user_id == user_id_ambig(user), session)

def get_open_user_bets(user, session=None):
  if session is None:
    with Session.begin() as session:
      return get_open_user_bets(user, session)
  return [bet for bet in get_condition_db("Bet", Bet.user_id == user_id_ambig(user), session) if bet.match.date_closed is None]

def bets_to_name_objs(bets, session=None, user=None):
  if session is None:
    with Session.begin() as session:
      bets_to_name_objs(bets, session, user)
  user_id = user_id_ambig(user)
  return add_time_name_objs([(shorten_bet_name(bet, user_id, session), bet) for bet in bets])

def matches_to_name_objs(matches, naming_type=1):
  return add_time_name_objs([(shorten_match_name(match, naming_type), match) for match in matches])

def tournaments_to_name_objs(tournaments):
  return [(shorten_tournament_name(tournament), tournament) for tournament in tournaments]

def team_to_name_objs(teams):
  return [(team.name, team) for team in teams]

def bets_to_names(bets, session=None, user=None):
  if session is None:
    with Session.begin() as session:
      bets_to_names(bets, session, user)
  return [no[0] for no in bets_to_name_objs(bets, session, user)]

def matches_to_names(matches, naming_type):
  return [no[0] for no in matches_to_name_objs(matches, naming_type)]

def tournaments_to_names(tournaments):
  return [no[0] for no in tournaments_to_name_objs(tournaments)]

def teams_to_names(teams):
  return [no[0] for no in team_to_name_objs(teams)]

def get_current_bets(session=None):
  return get_condition_db("Bet", Bet.winner == 0, session)

def get_current_visible_bets(session=None):
  return get_condition_db("Bet", (Bet.winner == 0) & (Bet.hidden == False), session)

#ones user can see (below 2)
def get_user_visible_current_bets(user, session=None):
  return get_condition_db("Bet",(Bet.winner == 0) & ((Bet.user_id == user_id_ambig(user)) | ((Bet.user_id != user_id_ambig(user)) & (Bet.hidden == False))), session)

def get_user_visible_bets(user, session=None):
  return list(reversed(get_condition_db("Bet", (Bet.user_id == user_id_ambig(user)) | ((Bet.user_id != user_id_ambig(user)) & (Bet.hidden == False)), session)))

#as in user's
def get_users_visible_current_bets(user, session=None):
  return get_condition_db("Bet", (Bet.winner == 0) & (Bet.user_id == user_id_ambig(user)) & (Bet.hidden == False), session)

def get_users_hidden_current_bets(user, session=None):
  return get_condition_db("Bet", (Bet.winner == 0) & (Bet.user_id == user_id_ambig(user)) & (Bet.hidden == True), session)

def get_users_hidden_match_bets(user, match_code, session=None):
  return get_condition_db("Bet", (Bet.match_id == match_code) & (Bet.user_id == user_id_ambig(user)) & (Bet.hidden == True), session)

def get_users_by_balance(session=None):
  users = get_condition_db("User", User.hidden == False, session)
  users.sort(key=lambda x: x.balances[-1][1], reverse=True)
  return users

def get_top_users(top, session=None):
  users = get_users_by_balance(session)
  top = min(top, len(users))
  return users[:top]

def get_active_users_by_balance(session=None):
  users = get_users_by_balance(session)
  new_users = []
  for user in users:
    bal1_label = user.balances[-1][0]
    if not(bal1_label.startswith("reset_") or bal1_label.startswith("start")):
      new_users.append(user)
  return new_users

def get_top_active_users(top, session=None):
  users = get_active_users_by_balance(session)
  top = min(top, len(users))
  return users[:top]
  

def get_current_matches(session=None):
  return get_condition_db("Match", Match.winner == 0, session)

def get_open_matches(session=None):
  return get_condition_db("Match", Match.date_closed == None, session)

def get_closed_matches(session=None):
  return get_condition_db("Match", (Match.winner == 0) & (Match.date_closed != None), session)

def get_active_tournaments(session=None):
  return get_condition_db("Tournament", Tournament.active == True, session)

def get_inactive_tournaments(session=None):
  tournaments = get_condition_db("Tournament", Tournament.active == False, session)
  tournaments.reverse()
  return tournaments


def get_match_from_vlr_code(vlr_code, session=None):
  matches = get_condition_db("Match", Match.vlr_code == vlr_code, session)
  if len(matches) != 1:
    return None
  return matches[0]

def get_team_from_vlr_code(vlr_code, session=None):
  teams = get_condition_db("Team", Team.vlr_code == vlr_code, session)
  if len(teams) != 1:
    return None
  return teams[0]

def get_tournament_from_vlr_code(vlr_code, session=None):
  tournament =  get_condition_db("Tournament", Tournament.vlr_code == vlr_code, session)
  if len(tournament) != 1:
    return None
  return tournament[0]

async def edit_all_messages(bot, ids, embedd, view : int | discord.ui.View | None = -1):
  async def edit_message(id):
    try:
      channel = await bot.fetch_channel(id[1])
      msg = await channel.fetch_message(id[0])
      title = msg.embeds[0].title.split(":")[0]
      try:
        # split title by : and add all after first :
        new_title = embedd.title.split(":")[1:]
        new_title = ":".join(new_title)
        title = title + ":" + new_title
      except:
        title = msg.embeds[0].title
      embedd.title = title
      args = {}
      args["embed"] = embedd
      if view != -1:
        args["view"] = view
      await msg.edit(**args)
    except Exception:
      print(type(id), id, "no msg found")

  tasks = [edit_message(id) for id in ids]
  await asyncio.gather(*tasks)
      
  