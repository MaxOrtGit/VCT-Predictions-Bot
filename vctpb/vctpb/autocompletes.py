
import discord
from dbinterface import get_all_db, get_condition_db
from User import User
from Color import Color
from convert import *

from sqlaobjs import Session

from utils import *


#color picker autocomplete start
async def color_picker_autocomplete(ctx: discord.AutocompleteContext):
  lower = ctx.value.lower()
  return [color.name.capitalize() for color in get_all_db("Color") if lower in color.name.lower()]
#color picker autocomplete end

#multi user autocomplete start
async def multi_user_list_autocomplete(ctx: discord.AutocompleteContext):
  value = ctx.value.strip()
  users = get_condition_db("User", User.hidden == False)
  usernames_t = [(user.username, user.username.replace(" ", "-_-")) for user in users]
  clean_usernames = [username_t[0] for username_t in usernames_t]
  no_break_usernames = [username_t[1] for username_t in usernames_t]
  for username_t in usernames_t:
    value = value.replace(username_t[0], username_t[1])
  combined_values = value
  values = value.split(" ")
  if len(values) == 0:
    return clean_usernames
  last_value = values[-1]
  all_but = " ".join(values[:-1]).replace("-_-", " ")
  all = " ".join(values).replace("-_-", " ")
  if last_value not in no_break_usernames:
    auto_completes = []
    for username_t in usernames_t:
      if username_t[1] in combined_values:
        continue
      if username_t[1].startswith(last_value):
        auto_completes.append(f"{all_but} {username_t[0]}")
    return auto_completes
  return [f"{all} {username_t[0]}" for username_t in usernames_t if username_t[1] not in combined_values]
#multi user autocomplete end


#user award autocomplete start
async def user_awards_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    if (user := get_from_db("User", ctx.interaction.user.id, session)) is None: return ["No user found."]
    
    award_labels = user.get_award_strings()
    award_labels.reverse()
    
    return [award_label for award_label in award_labels if ctx.value.lower() in award_label.lower()]
#user award autocomplete end  



#new match list autocomplete start
async def new_match_list_odds_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    if (user := get_from_db("User", ctx.interaction.user.id, session)) is None: return ["No user found."]
    return filter_names(ctx.value.lower(), user.open_matches(session), session, naming_type=2)
#new match list autocomplete end


#all bet list autocomplete start
async def all_bet_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_current_bets(session), session, ctx.interaction.user)
#all bet list autocomplete end


#bet list autocomplete start
async def bet_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    lower_value = ctx.value.lower()
    auto_completes = filter_names(lower_value, get_current_bets(session), session, ctx.interaction.user)
    if auto_completes == []:
      auto_completes = filter_names(lower_value, get_user_visible_bets(ctx.interaction.user, session), ctx.interaction.user)
    return auto_completes
#bet list autocomplete end


#user bet list autocomplete start
async def user_open_bet_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_open_user_bets(ctx.interaction.user, session), session)
#user bet list autocomplete end


#user's visible bet list autocomplete start
async def users_visible_bet_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_users_visible_current_bets(ctx.interaction.user, session), session)
#user's visible bet list autocomplete end
  
  
#user's hidden bet list autocomplete start
async def users_hidden_bet_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_users_hidden_current_bets(ctx.interaction.user, session), session)
#user's hidden bet list autocomplete end



#color xkcd autocomplete start
async def xkcd_picker_autocomplete(ctx: discord.AutocompleteContext): 
  val = ctx.value.lower()
  colors = [x[5:].lower() for x in xkcd_colors.keys() if val in x]
  
  colors = colors[::-1]
  same = []
  start = []
  half_start = []
  contain = []
  val_words = val.split(" ")
  for color in colors:
    color_words = color.split(" ")
    if color.startswith(val):
      start.append(color)
    else:
      half = True
      for word in val_words:
        word_in = False
        for color_word in color_words:
          if color_word.startswith(word):
            word_in = True
        if not word_in:
          half = False
          break
      if half:
        half_start.append(color)
      elif color == val:
        same.append(color)
      else:
        contain.append(color)
    
  colors = same + start + half_start + contain
  colors = [color.capitalize() for color in colors]
  return colors
#color xkcd autocomplete end


#color profile autocomplete start
async def color_profile_autocomplete(ctx: discord.AutocompleteContext):  
  with Session.begin() as session:
    if (user := get_from_db("User", ctx.interaction.user.id, session)) is None: return ["No user found."]
    if user.is_in_first_place(get_all_db("User", session)):
      val = ["First place gold"]
    else:
      val = []
    return val + [color.name.capitalize() for color in get_all_db("Color", session) if ctx.value.lower() in color.name.lower()]
#color profile autocomplete end



#match list autocomplete start
async def match_list_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    lower_value = ctx.value.lower()
    auto_completes = filter_names(lower_value, get_current_matches(session), session)
    if auto_completes == []:
      auto_completes = filter_names(lower_value, get_all_db("Match", session), session)
    return auto_completes
#match list autocomplete end

#match current list autocomplete start
async def match_current_list_autocomplete(ctx: discord.AutocompleteContext):
  return filter_names(ctx.value.lower(), get_current_matches())
#match current list autocomplete end
  
  
#match open list autocomplete start
async def match_open_list_autocomplete(ctx: discord.AutocompleteContext):
  return filter_names(ctx.value.lower(), get_open_matches())
#match open list autocomplete end

#match close list autocomplete start
async def match_close_list_autocomplete(ctx: discord.AutocompleteContext):
  return filter_names(ctx.value.lower(), get_closed_matches())
#match close list autocomplete end

  
#match match team autocomplete start
async def match_team_list_autocomplete(ctx: discord.AutocompleteContext):
  if(match := ctx.options["match"]) is None: return []
  with Session.begin() as session:
    if (match := await obj_from_autocomplete_tuple(ctx, get_current_matches(session), match, "Match", session)) is None: return []
    return [match.t1, match.t2]
#match match team autocomplete end

  
#match winner autocomplete start
async def match_reset_winner_list_autocomplete(ctx: discord.AutocompleteContext):
  if(match := ctx.options["match"]) is None: return []
  with Session.begin() as session:
    if (match := await obj_from_autocomplete_tuple(None, get_all_db("Match", session), match, "Match", session)) is None: return []
    
    strin = "None"
    if match.t1 == "None" or match.t2 == "None":
      strin = "Set winner to none"
    return ["Dont do this command", match.t1, match.t2, strin, "This command can break the bot and its save data"]
#match winner autocomplete end

#tournament autocomplete start
async def tournament_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    lower_value = ctx.value.lower()
    auto_completes = filter_names(lower_value, get_active_tournaments(session), session)
    if auto_completes == []:
      auto_completes = filter_names(lower_value, get_all_db("Tournament", session), session)
    return auto_completes
#tournament autocomplete end

#tournament active autocomplete start
async def tournament_active_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_active_tournaments(session), session)
#tournament active autocomplete end

#tournament inactive autocomplete start
async def tournament_inactive_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_inactive_tournaments(session), session)
  #tournament inactive autocomplete end
  
#team autocomplete start
async def team_autocomplete(ctx: discord.AutocompleteContext):
  with Session.begin() as session:
    return filter_names(ctx.value.lower(), get_all_db("Team", session), session)

#season autocomplete start
async def seasons_autocomplete(ctx: discord.AutocompleteContext):
  
  if(user := get_user_from_ctx(ctx, send=False)) is None: return []
  
  reset_labels = user.get_reset_strings()
  reset_labels.reverse()
  
  return [reset_label for reset_label in reset_labels if ctx.value.lower() in reset_label.lower()]
#season autocomplete end  
