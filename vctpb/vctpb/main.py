
# add moddifacation when no on incorrect match creation
# test bet list with and without await
# have it replace by code not by value
# test prefix unique with 1 long in test code

from io import BytesIO
from urllib.request import urlopen

from bs4 import BeautifulSoup
#git clone https://github.com/Pycord-Development/pycord
#cd pycord
#python3 -m pip install -U .[voice]

#pip install git+https://github.com/Pycord-Development/pycord
#poetry add git+https://github.com/Pycord-Development/pycord
import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup
from discord.ui import InputText, Modal
from discord.ext import tasks, commands
import os
import random
import jsonpickle
from Match import Match
from Bet import Bet
from User import User, get_multi_graph_image, all_user_unique_code, get_all_unique_balance_ids, num_of_bal_with_name, get_first_place, add_balance_user
from Team import Team
from Tournament import Tournament
from dbinterface import *
from colorinterface import *
import math
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont
from convert import *
from objembed import *
from savefiles import backup
from savedata import backup_full, save_savedata_from_github, are_equivalent, zip_savedata, pull_from_github
import secrets
import atexit
from roleinterface import set_role, unset_role, edit_role, set_role_name
from autocompletes import *
from vlrinterface import get_odds_from_match_page, get_team_names_from_match_page, get_tournament_name_and_code_from_match_page, get_match_link, get_teams_from_match_page

from vlrinterface import generate_matches_from_vlr, get_code, generate_tournament, get_or_create_team, get_or_create_tournament, generate_team

from sqlaobjs import Session
from utils import *

  


intents = discord.Intents.all()

bot = commands.Bot(intents=intents)

gid = get_setting("guild_ids")


#current is no winner
#open is betting open

def get_users_from_multiuser(compare, session=None):
  usernames_split = compare.split(" ")
  
  users = usernames_to_users(compare, session)

  
  if len(users) == 1:
    return "You need to enter more than one user."

  
  usernames = " ".join([user.username for user in users])

  unknown_words = []
  for username_word in usernames_split:
    if username_word not in usernames:
      unknown_words.append(username_word)
  
  if len(unknown_words) > 0:
    return f"Unknown user(s): {', '.join(unknown_words)}"
      
  return users


def get_last_tournament_name(amount, session=None):
  print("use partitions for effeciency")
  #use partitions for effeciency
  matches = get_all_db("Match", session)
  matches.reverse()
  name_set = set()
  for match in matches:
    name_set.add(match.tournament_name)
    if len(name_set) == amount:
      if amount == 1:
        return list(name_set)[0]
      return list(name_set)

def get_last_odds_source(amount, session=None):
  matches = get_all_db("Match", session)
  matches.reverse()
  name_set = set()
  for match in matches:
    name_set.add(match.odds_source)
    if len(name_set) == amount:
      if amount == 1:
        return list(name_set)[0]
      return list(name_set)

def get_last_tournament_and_odds(session=None):
  match = get_new_db("Match", session)
  return (match.tournament_name, match.odds_source)

      
def rename_balance_id(user_ambig, balance_id, new_balance_id, session=None):
  if session is None:
    with Session.begin() as session:
      return rename_balance_id(user_ambig, balance_id, new_balance_id, session)
  
  user = ambig_to_obj(user_ambig, "User", session)
  if user is None:
    return "User not found"
  indices = [i for i, x in enumerate(user.balances) if x[0] == balance_id]
  if len(indices) > 1:
    return "More than one balance_id found"
  elif len(indices) == 0:
    return "No balance_id found"
  else:
    balat = user.balances[indices[0]]
    user.balances[indices[0]] = (new_balance_id, balat[1], balat[2])



def print_all_balances(user_ambig, session=None):
  user = ambig_to_obj(user_ambig, "User", session)
  if user is None:
    return None

  [print(bal[0], bal[1]) for bal in user.balances]


def create_user(user_id, username, session=None):
  random.seed()
  color = secrets.token_hex(3)
  user = User(user_id, username, color, get_date())
  print(jsonpickle.encode(user), session)
  add_to_db("User", user)
  return user


@bot.event
async def on_ready():
  print("Logged in as {0.user}".format(bot))
  print(bot.guilds)
  
  save_savedata_from_github()
  zip_savedata()
  #if savedata does not exist pull
  if not os.path.exists("savedata"):
    print("savedata folder does not exist")
    print("-----------Pulling Savesdata-----------")
    pull_from_github()
  if (not are_equivalent("backup.zip", "gitbackup.zip")):
    print("savedata not is not synced with github")
    git_savedata = get_setting("git_savedata")
    if git_savedata == "override":
      print("-----------Overriding Savedata-----------")
    elif git_savedata == "pull":
      print("-----------Pulling Savesdata-----------")
      pull_from_github()
    elif git_savedata == "quit":
      print("-----------Missmatch Savedata-----------")
      print("-----------Quitting-----------")
      atexit.unregister(backup_full)
      quit()
    elif git_savedata == "once":
      print("-----------pushing then setting to quit-----------")
      set_setting("git_savedata", "quit")
      
  
  auto_backup_timer.start()
  print("\n-----------Bot Starting-----------\n")
  auto_generate_matches_from_vlr_timer.start()


@tasks.loop(hours=1)
async def auto_backup_timer():
  backup_full()


@tasks.loop(minutes=5)
async def auto_generate_matches_from_vlr_timer():
  print("-----------Generating Matches-----------")
  with Session.begin() as session:
    await generate_matches_from_vlr(bot, session, reply_if_none=False)
  

#choices start
yes_no_choices = [
  OptionChoice(name="yes", value=1),
  OptionChoice(name="no", value=0),
]
list_choices = [
  OptionChoice(name="shortened", value=0),
  OptionChoice(name="full", value=1),
]
open_close_choices = [
  OptionChoice(name="open", value=0),
  OptionChoice(name="close", value=1),
]
#choices end




#assign start
assign = SlashCommandGroup(
  name = "assign", 
  description = "Assigns the discord channel it is put in to that channel type.",
  guild_ids = gid,
)

#assign matches start
@assign.command(name = "matches", description = "Where the end matches show up.")
async def assign_matches(ctx):
  set_channel_in_db("match", ctx.channel.id)
  
  await ctx.respond(f"<#{ctx.channel.id}> is now the match list channel.")
#assign matches end

#assign bets start
@assign.command(name = "bets", description = "Where the end bets show up.")
async def assign_bets(ctx):
  set_channel_in_db("bet", ctx.channel.id)
  await ctx.respond(f"<#{ctx.channel.id}> is now the bet list channel.")
#assign bets end

#assign results start
@assign.command(name = "results", description = "Where the end results show up.")
async def assign_results(ctx):
  set_channel_in_db("result", ctx.channel.id)
  await ctx.respond(f"<#{ctx.channel.id}> is now the result list channel.")
#assign results end

bot.add_application_command(assign)
#assign end


#award start
award = SlashCommandGroup(
  name = "award", 
  description = "Awards the money to someone's account. DON'T USE WITHOUT PERMISSION!",
  guild_ids = gid,
)


#award give start
@award.command(name = "give", description = """Awards the money to someone's account. DON'T USE WITHOUT PERMISSION!""")
async def award_give(ctx, 
  amount: Option(int, "Amount you want to give or take."), description: Option(str, "Unique description of why the award is given."),
  user: Option(discord.Member, "User you wannt to award. (Can't use with users).", default = None, required = False),  
  users: Option(str, "Users you want to award. (Can't use with user).", autocomplete=multi_user_list_autocomplete, default = None, required = False)):
  
  if (user is not None) and (users is not None):
    await ctx.respond("You can't use compare and user at the same time.", ephemeral = True)
    return
  if (user is None) and (users is None):
    await ctx.respond("You must have either compare or user.", ephemeral = True)
    return
  
  with Session.begin() as session:
    if users is not None:
      users = get_users_from_multiuser(users, session)
      if isinstance(users, str):
        await ctx.respond(users, ephemeral = True)
        return
      code = all_user_unique_code("award", users)
      bet_id = f"award_{code}_{description}"
      
      print(bet_id)
      
      first = True
      for user in users:
        abu = add_balance_user(user, amount, bet_id, get_date(), session)
        embedd = create_user_embedded(abu, session)
        if first:
          await ctx.respond(embed=embedd)
          first = False
        else:
          await ctx.interaction.followup.send(embed=embedd)
      return
    
    if (user := await get_user_from_ctx(ctx, user, session)) is None: return
    bet_id = "award_" + user.get_unique_bal_code() + "_" + description
    print(bet_id)
    abu = add_balance_user(user, amount, bet_id, get_date(), session)
    if abu is None:
      await ctx.respond("User not found.", ephemeral = True)
    else:
      embedd = create_user_embedded(user, session)
      await ctx.respond(embed=embedd)
#award give end

#award list start
@award.command(name = "list", description = "Lists all the awards given to a user.")
async def award_list(ctx, user: Option(discord.Member, "User you want to list awards for.")):
  if (user := await get_user_from_ctx(ctx, user)) is None: return
  
  award_labels = user.get_award_strings()
  
  embedd = create_award_label_list_embedded(user, award_labels)
  await ctx.respond(embed=embedd)
  

#award rename start
@award.command(name = "rename", description = """Renames an award.""")
async def award_rename(ctx, user: Option(discord.Member, "User you want to award"), award: Option(str, "Description of award you want to rename.", autocomplete=user_awards_autocomplete), description: Option(str, "Unique description of why the award is given.")):
  
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, user, session)) is None: return
    
    award_labels = user.get_award_strings()
    
    if len(award) == 8:
      if award_label.endswith(award):
        award = award_label
    else:
      for award_label in award_labels:
        if award_label == award:
          award = award_label
          break
      else:
        await ctx.respond("Award not found.", ephemeral = True)
        return
      
    users = get_all_db("User", session)
    
    num = num_of_bal_with_name(award, users)
    
    if num > 1:
      await ctx.respond("There are multiple awards with this name.", ephemeral = True)
      return
    
    if user.change_award_name(award, description, session) is None:
      print(f"change award name not found. {award} {user.code}.")
      await ctx.respond(f"Award not working {description}, {award} {user.code}.", ephemeral = True)
      return
    
    print(award)
    award_t = award.split(", ")[:-2]
    award = ", ".join(award_t)
    
    
    await ctx.respond(f"Award {award} renamed to {description}.")
#award rename end  

#award reaward start
@award.command(name = "reaward", description = """Changes the amount of an award.""")
async def award_rename(ctx, user: Option(discord.Member, "User you want to award"), award: Option(str, "Description of award you want to reaward.", autocomplete=user_awards_autocomplete), amount: Option(str, "New Amount.")):
  with Session.begin() as session:
    amount = to_digit(amount)
    if amount is None:
      await ctx.respond("Amount not valid.", ephemeral = True)
      return
    if (user := await get_user_from_ctx(ctx, user, session)) is None: return
    
    award_labels = user.get_award_strings()
    
    if len(award) == 8:
      if award_label.endswith(award):
        award = award_label
    else:
      for award_label in award_labels:
        if award_label == award:
          award = award_label
          break
      else:
        await ctx.respond("Award not found.", ephemeral = True)
        return
    
    if user.change_award_amount(award, amount, session) is None:
      print(f"change award name not found. {award}  --  {amount}  --  {user.code}.")
      await ctx.respond(f"Award not working {award}, {amount}, {user.code}.", ephemeral = True)
    
    print(award)
    
    await ctx.respond(f"Award {award.split(', ')[0][5:]} reawarded to {amount}.")
#award rename end  

bot.add_application_command(award)
#award end

  

#balance start
@bot.slash_command(name = "balance", description = "Shows the last x amount of balance changes (awards, bets, etc).", aliases=["bal"], guild_ids = gid)
async def balance(ctx, user: Option(discord.Member, "User you want to get balance of.", default = None, required = False)):
  with Session.begin() as session:
    if user is None:
      user = get_from_db("User", ctx.author.id, session)
      if user is None:
        print("creating_user")
        user = create_user(ctx.author.id, ctx.author.display_name, session)
    else:
      if (user := await get_user_from_ctx(ctx, user, session)) is None: return
    embedd = create_user_embedded(user, session)
    if embedd is None:
      await ctx.respond("User not found.")
      return
    await ctx.respond(embed=embedd)
#balance end



#bet start
betscg = SlashCommandGroup(
  name = "bet", 
  description = "Create, edit, and view bets.",
  guild_ids = gid,
)


#bet create modal start
class BetCreateModal(Modal):
  
  def __init__(self, match: Match, user: User, hidden, session, error=[None, None], *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.match = match
    self.user = user
    self.hidden = hidden
    if error[0] is None: 
      team_label = f"{match.t1} vs {match.t2}. Odds: {match.t1o} / {match.t2o}"
      if len(team_label) >= 45:
        team_label = f"{match.t1} vs {match.t2}, {match.t1o} / {match.t2o}"
        if len(team_label) >= 45:
          team_label = f"{match.t1} vs {match.t2}, {match.t1o}/{match.t2o}"
          if len(team_label) >= 45:
            team_label = f"{match.t1}/{match.t2}, {match.t1o}/{match.t2o}"
            if len(team_label) >= 45:
              firstt1w = match.t1.split(" ")[0]
              firstt2w = match.t2.split(" ")[0]
              team_label = f"{firstt1w} vs {firstt2w}. Odds: {match.t1o} / {match.t2o}"
              if len(team_label) >= 45:
                team_label = f"{firstt1w} vs {firstt2w}, {match.t1o} / {match.t2o}"
                if len(team_label) >= 45:
                  team_label = f"{firstt1w} vs {firstt2w}, {match.t1o}/{match.t2o}"
                  if len(team_label) >= 45:
                    team_label = f"{firstt1w}/{firstt2w}, {match.t1o}/{match.t2o}"
                    if len(team_label) >= 45:
                      team_label = f"{firstt1w[:15]}/{firstt2w[:15]}, {match.t1o}/{match.t2o}"
    else:
      team_label = error[0]
      
    self.add_item(InputText(label=team_label, placeholder=f'"1" for {match.t1} and "2" for {match.t2}', min_length=1, max_length=100))

    if error[1] is None: 
      amount_label = "Amount you want to bet."
    else:
      amount_label = error[1]
    self.add_item(InputText(label=amount_label, placeholder=f"Your available balance is {math.floor(user.get_balance(session))}", min_length=1, max_length=20))



  async def callback(self, interaction: discord.Interaction):
    with Session.begin() as session:
      match = self.match
      user = self.user
      team_num = self.children[0].value
      amount = self.children[1].value
      error = [None, None]
      
      if not is_digit(amount):
        print("Amount has to be a positive whole integer.")
        error[1] = "Amount must be a positive whole number."
      else:
        if int(amount) <= 0:
          print("Cant bet negatives.")
          error[1] = "Amount must be a positive whole number."
      
      if not (team_num == "1" or team_num == "2" or team_num.lower() == match.t1.lower() or team_num.lower() == match.t2.lower()):
        print("Team num has to either be 1 or 2.")
        error[0] = f'Team number has to be "1", "2", "{match.t1}", or "{match.t2}".'
      else:
        if team_num.lower() == match.t1.lower():
          team_num = "1"
        elif team_num.lower() == match.t2.lower():
          team_num = "2"

      if not match.date_closed is None:
        await interaction.response.send_message("Betting has closed you cannot make a bet.")

      code = get_unique_code("Bet", session)
      if error[1] is None:
        balance_left = user.get_balance(session) - int(amount)
        if balance_left < 0:
          print("You have bet " + str(math.ceil(-balance_left)) + " more than you have.")
          error[1] = "You have bet " + str(math.ceil(-balance_left)) + " more than you have."
      
      if not error == [None, None]:
        errortext = ""
        if error[0] is not None:
          errortext += error[0]
          if error[1] is not None:
            errortext += "\n"
        if error[1] is not None:
          errortext += error[1]
        await interaction.response.send_message(errortext, ephemeral = True)
        return
      
      bet = Bet(code, match.t1, match.t2, match.tournament_name, int(amount), int(team_num), match.code, user.code, get_date(), self.hidden)
      add_to_db(bet, session)
      
      session.flush([bet])
      session.expire(bet)
      
      if bet.hidden:  
        shown_embedd = create_bet_hidden_embedded(bet, f"New Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}", session)
      else:
        shown_embedd = create_bet_embedded(bet, f"New Bet: {user.username}, {amount} on {bet.get_team()}.", session)
        
      if (channel := await bot.fetch_channel(get_channel_from_db("bet", session))) == interaction.channel:
        inter = await interaction.response.send_message(embed=shown_embedd)
        msg = await inter.original_message()
      else:
        await interaction.response.send_message(f"Bet created in {channel.mention}.", ephemeral=True)
        msg = await channel.send(embed=shown_embedd)
        
      if self.hidden:
        embedd = create_bet_embedded(bet, f"Your Hidden Bet: {amount} on {bet.get_team()}.", session)
        inter = await interaction.followup.send(embed = embedd, ephemeral = True)
      bet.message_ids.append((msg.id, msg.channel.id))
#bet create modal end


#bet edit modal start
class BetEditModal(Modal):
  
  def __init__(self, hide, match: Match, user: User, bet: Bet, session, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.match = match
    self.user = user
    self.bet = bet
    self.hide = hide
    
    team_label = f"{match.t1} vs {match.t2}. Odds: {match.t1o} / {match.t2o}"
    if len(team_label) >= 45:
      team_label = f"{match.t1} vs {match.t2}, {match.t1o} / {match.t2o}"
      if len(team_label) >= 45:
        team_label = f"{match.t1} vs {match.t2}, {match.t1o}/{match.t2o}"
        if len(team_label) >= 45:
          team_label = f"{match.t1}/{match.t2}, {match.t1o}/{match.t2o}"
          if len(team_label) >= 45:
            firstt1w = match.t1.split(" ")[0]
            firstt2w = match.t2.split(" ")[0]
            team_label = f"{firstt1w} vs {firstt2w}. Odds: {match.t1o} / {match.t2o}"
            if len(team_label) >= 45:
              team_label = f"{firstt1w} vs {firstt2w}, {match.t1o} / {match.t2o}"
              if len(team_label) >= 45:
                team_label = f"{firstt1w} vs {firstt2w}, {match.t1o}/{match.t2o}"
                if len(team_label) >= 45:
                  team_label = f"{firstt1w}/{firstt2w}, {match.t1o}/{match.t2o}"
                  if len(team_label) >= 45:
                    team_label = f"{firstt1w[:15]}/{firstt2w[:15]}, {match.t1o}/{match.t2o}"
    
      
    self.add_item(InputText(label=team_label, placeholder=bet.get_team(), min_length=1, max_length=100, required=False))

    amount_label = f"Amount to bet. Balance: {math.floor(user.get_balance(session) + bet.amount_bet)}"
    self.add_item(InputText(label=amount_label, placeholder = bet.amount_bet, min_length=1, max_length=20, required=False))

  async def callback(self, interaction: discord.Interaction):
    with Session.begin() as session:
      match = get_from_db("Match", self.match.code, session)
      user = get_from_db("User", self.user.code, session)
      bet = get_from_db("Bet", self.bet.code, session)

      team_num = self.children[0].value
      if team_num == "":
        team_num = str(bet.team_num)
      amount = self.children[1].value
      if amount == "":
        amount = str(bet.amount_bet)
      error = [None, None]
      
      if not is_digit(amount):
        print("Amount has to be a positive whole integer.")
        error[1] = "Amount must be a positive whole number."
      else:
        if int(amount) <= 0:
          print("Cant bet negatives.")
          error[1] = "Amount must be a positive whole number."

      if not (team_num == "1" or team_num == "2" or team_num.lower() == match.t1.lower() or team_num.lower() == match.t2.lower()):
        print("Team num has to either be 1 or 2.")
        error[0] = f'Team number has to be "1", "2", "{match.t1}", or "{match.t2}".'
      else:
        if team_num.lower() == match.t1.lower():
          team_num = "1"
        elif team_num.lower() == match.t2.lower():
          team_num = "2"
      

      if not match.date_closed is None:
        await interaction.response.send_message("Betting has closed you cannot make a bet.")

      if error[0] is None:
        balance_left = user.get_balance(session) + bet.amount_bet - int(amount)
        if balance_left < 0:
          print("You have bet " + str(math.ceil(-balance_left)) + " more than you have.")
          error[1] = "You have bet " + str(math.ceil(-balance_left)) + " more than you have."

      if not error == [None, None]:
        errortext = ""
        if error[0] is not None:
          errortext += error[0]
          if error[1] is not None:
            errortext += "\n"
        if error[1] is not None:
          errortext += error[1]
        await interaction.response.send_message(errortext)
        return
      
      bet.amount_bet = int(amount)
      bet.team_num = int(team_num)
      if self.hide != -1:
        bet.hidden = self.hide
      
      if bet.hidden:
        title = f"Edit Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}"
        embedd = create_bet_hidden_embedded(bet, title, session)
      else:
        title = f"Edit Bet: {user.username}, {amount} on {bet.get_team()}."
        embedd = create_bet_embedded(bet, title, session)
      
      inter = await interaction.response.send_message(embed=embedd)
      msg = await inter.original_message()
      
      bet.message_ids.append((msg.id, msg.channel.id))
    await edit_all_messages(bot, bet.message_ids, embedd, title)
#bet edit modal end

  
#bet create start
@betscg.command(name = "create", description = "Create a bet.")
async def bet_create(ctx, match: Option(str, "Match you want to bet on.",  autocomplete=new_match_list_odds_autocomplete), hide: Option(int, "Hide bet from other users? Defualt is No.", choices = yes_no_choices, default=0, required=False)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, session=session)) is None:
      user = create_user(ctx.author.id, ctx.author.display_name, session)
    
    if (nmatch := await obj_from_autocomplete_tuple(ctx, user.open_matches(session), match, "Match", session, naming_type=2)) is None:
      await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
      return
    match = nmatch
    
    if match.date_closed is not None:
      await ctx.respond("Betting has closed.", ephemeral=True)
      return
    
    for bet in user.active_bets:
      if bet.match_id == match.code:
        await ctx.respond("You already have a bet on this match.", ephemeral=True)
        return
    hidden = hide == 1
    if hidden:
      title = "Create hidden bet"
    else:
      title = "Create bet"
    bet_modal = BetCreateModal(match, user, hidden, session, title=title)
    await ctx.interaction.response.send_modal(bet_modal)
#bet create end


#bet cancel start
@betscg.command(name = "cancel", description = "Cancels a bet if betting is open on the match.")
async def bet_cancel(ctx, bet: Option(str, "Bet you want to cancel.", autocomplete=user_open_bet_list_autocomplete)):
  with Session.begin() as session:
    if (nbet := await obj_from_autocomplete_tuple(ctx, get_open_user_bets(ctx.interaction.user, session), bet, "Bet", session)) is None:
      await ctx.respond(f'Bet "{bet}" not found,', ephemeral = True)
      return
    bet = nbet
    
    
    match = bet.match
    if (match is None) or (match.date_closed is not None):
      await ctx.respond(content="Match betting has closed, you cannot cancel the bet.", ephemeral=True)
      return
      
    
    user = bet.user
    if bet.hidden == 0:
      embedd = create_bet_embedded(bet, f"Cancelled Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
    else:
      embedd = create_bet_hidden_embedded(bet, f"Cancelled Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}", session)
    await ctx.respond(content="", embed=embedd)
    
    await delete_from_db(bet, bot, session=session)
#bet cancel end


#bet edit start
@betscg.command(name = "edit", description = "Edit a bet.")
async def bet_edit(ctx, bet: Option(str, "Bet you want to edit.", autocomplete=user_open_bet_list_autocomplete), hide: Option(int, "Hide bet from other users? Defualt is No.", choices = yes_no_choices, default=-1, required=False)):
  with Session.begin() as session:
    if (nbet := await obj_from_autocomplete_tuple(ctx, get_open_user_bets(ctx.interaction.user, session), bet, "Bet", session)) is None:
      await ctx.respond(f'Bet "{bet}" not found,', ephemeral = True)
      return
    bet = nbet
    
    
    match = bet.match
    if (match is None) or (match.date_closed is not None):
      await ctx.respond("Match betting has closed, you cannot edit the bet.", ephemeral=True)
      return
    
    user = bet.user

    bet_modal = BetEditModal(hide, match, user, bet, session, title="Edit Bet")
    await ctx.interaction.response.send_modal(bet_modal)
#bet edit end


#bet find start
@betscg.command(name = "find", description = "Sends the embed of the bet.")
async def bet_find(ctx, bet: Option(str, "Bet you get embed of.", autocomplete=bet_list_autocomplete)):
  with Session.begin() as session:
    if (nbet := await obj_from_autocomplete_tuple(None, get_current_bets(session), bet, "Bet", session, ctx.user)) is None: 
      if (nbet := await obj_from_autocomplete_tuple(None, get_user_visible_bets(ctx.user, session), bet, "Bet", session, ctx.user)) is None: 
        await ctx.respond(f'Bet "{bet}" not found,', ephemeral = True)
        return
    bet = nbet
    
    user = bet.user
    if bet.user_id == ctx.user.id or bet.hidden == False:
      embedd = create_bet_embedded(bet, f"Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
      inter = await ctx.respond(embed=embedd, ephemeral=bet.hidden)
      if not bet.hidden:
        msg = await inter.original_message()
        bet.message_ids.append((msg.id, msg.channel.id))
    else:
      embedd = create_bet_hidden_embedded(bet, f"Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}", session)
      
      inter = await ctx.respond(embed=embedd, ephemeral=(bet.hidden and (bet.user_id == ctx.user.id)))
      if not(bet.hidden and (bet.user_id == ctx.user.id)):
        msg = await inter.original_message()
        bet.message_ids.append((msg.id, msg.channel.id))
#bet find end


#bet hide start
@betscg.command(name = "hide", description = "Hide one of your bets.")
async def bet_hide(ctx, bet: Option(str, "Bet you want to hide.", autocomplete=users_visible_bet_list_autocomplete)):
  with Session.begin() as session:
    if (nbet := await obj_from_autocomplete_tuple(ctx, get_users_visible_current_bets(ctx.interaction.user, session), bet, "Bet", session)) is None:
      await ctx.respond(f'Bet "{bet}" not found,', ephemeral = True)
      return
    bet = nbet
    
    match = bet.match
    if (match is None) or (match.date_closed is not None):
      await ctx.respond("Match betting has closed, you cannot hide the bet.", ephemeral=True)
      return
    
    if bet.hidden == True:
      await ctx.respond("Bet is already hidden.", ephemeral=True)
      return
    
    bet.hidden = True
    
    user = bet.user
    title = f"Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}"
    embedd = create_bet_hidden_embedded(bet, title, session)
    inter = await ctx.respond(embed=embedd)
    msg = await inter.original_message()
    bet.message_ids.append((msg.id, msg.channel.id))
  await edit_all_messages(bot, bet.message_ids, embedd, title)
#bet hide end


#bet show start
@betscg.command(name = "show", description = "Show one of your hidden bets.")
async def bet_show(ctx, bet: Option(str, "Bet you want to show.", autocomplete=users_hidden_bet_list_autocomplete)):
  with Session.begin() as session:
    if (nbet := await obj_from_autocomplete_tuple(ctx, get_users_hidden_current_bets(ctx.interaction.user, session), bet, "Bet", session)) is None: 
      await ctx.respond(f'Bet "{bet}" not found,', ephemeral = True)
      return
    bet = nbet
    
    
    match = bet.match
    if (match is None) or (match.date_closed is not None):
      await ctx.respond("Match betting has closed, you cannot show the bet.", ephemeral=True)
      return
    
    if bet.hidden == False:
      await ctx.respond("Bet is already shown.", ephemeral=True)
      return
    
    bet.hidden = False
    
    user = bet.user
    title = f"Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}"
    embedd = create_bet_embedded(bet, title, session)
    inter = await ctx.respond(embed=embedd)
    msg = await inter.original_message()
    bet.message_ids.append((msg.id, msg.channel.id))
  await edit_all_messages(bot, bet.message_ids, embedd, title)
#bet show end


#bet list start
@betscg.command(name = "list", description = "Sends embed with all undecided bets. If type is full it sends the whole embed of each bet.")
async def bet_list(ctx, type: Option(int, "If type is full it sends the whole embed of each bet.", choices = list_choices, default = 0, required = False), show_hidden: Option(int, "Show your hidden bets? Defualt is Yes.", choices = yes_no_choices, default = 1, required = False)):
  with Session.begin() as session:
    #debug: Option(int, "Show debug info? Defualt is No.", choices = yes_no_choices, default = 0, required = False)
    #if debug == 1:
    #  bets = get_current_bets(session)
    #  if (embedd := create_bet_list_embedded("Bets:", bets, True, session)) is not None:
    #    await ctx.respond(embed=embedd)
    #  else:
    #    await ctx.respond("No bets found.")
    #  return
      
    
    
    if show_hidden == 1:
      if (user := await get_user_from_ctx(ctx, session=session)) is not None:
        hidden_bets = get_users_hidden_current_bets(user, session)
    else:
      hidden_bets = []
    
    
    if type == 0:
      #short
      bets = get_current_bets(session)
      if len(bets) == 0:
        await ctx.respond("No undecided bets.", ephemeral=True)
        return
      if (embedd := create_bet_list_embedded("Bets:", bets, False, session)) is not None:
        await ctx.respond(embed=embedd)
      if (hidden_embedd := create_bet_list_embedded("Your Hidden Bets:", hidden_bets, True, session)) is not None:
        await ctx.respond(embed=hidden_embedd, ephemeral=True)
          
    
    elif type == 1:
      #full
      i = 0
      bets = get_current_bets(session)
      if len(bets) == 0:
        await ctx.respond("No undecided bets.", ephemeral=True)
      else:
        for i, bet in enumerate(bets):
          user = bet.user
          if bet.hidden:
            embedd = create_bet_hidden_embedded(bet, f"Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}", session)
          else:
            embedd = create_bet_embedded(bet, f"Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
          if i == 0:
            inter = await ctx.respond(embed=embedd)
            msg = await inter.original_message()
          else:
            msg = await ctx.interaction.followup.send(embed=embedd)
          bet.message_ids.append((msg.id, msg.channel.id))
      if hidden_bets is not None:
        for i, bet in enumerate(hidden_bets):
          user = bet.user
          embedd = create_bet_embedded(bet, f"Hidden Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
          if i == 0:
            await ctx.respond(embed=embedd, ephemeral=True)
          else:
            await ctx.interaction.followup.send(embed=embedd, ephemeral=True)
#bet list end

bot.add_application_command(betscg)
#bet end




#color start
colorscg = SlashCommandGroup(
  name = "color", 
  description = "Add, romove, rename, and recolor colors.",
  guild_ids = gid,
)

  
#color list start
@colorscg.command(name = "list", description = "Lists all colors.")
async def color_list(ctx):
  colors = get_all_db("Color")
  if len(colors) == 0:
    await ctx.respond("No colors found.", ephemeral=True)
    return
  
  font = ImageFont.truetype("fonts/whitneybold.otf", size=40)
  img = Image.new("RGBA", (800, (int((len(colors)+1)/2) * 100)), (255,255,255,0))
  d = ImageDraw.Draw(img)
  for i, color in enumerate(colors):
    x = ((i % 2) * 350) + 50
    y = (int(i / 2) * 100) + 50
    hex = color.hex
    color_tup = hex_to_tuple(hex)
    d.text((x,y), color.name.capitalize(), fill=(*color_tup,255), font=font)
  with BytesIO() as image_binary:
    img.save(image_binary, 'PNG')
    image_binary.seek(0)
    await ctx.respond(content = "", file=discord.File(fp=image_binary, filename='image.png'))
#color list end

  
#color add start
@colorscg.command(name = "add", description = "Adds the color to color list.")
async def color_add(ctx, custom_color_name:Option(str, "Name of color you want to add.", required=False), hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False), xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False)):
  if xkcd_color_name is not None:
    if hex is not None:
      await ctx.respond("You can't add a hex code and a xkcd color name.", ephemeral=True)
      return
    
    hex = get_xkcd_color(xkcd_color_name)
    if hex is None:
      await ctx.respond("Invalid xkcd color.", ephemeral=True)
      return
    
    if custom_color_name is not None:
      xkcd_color_name = custom_color_name
    msg, color = add_color(xkcd_color_name, hex)
    await ctx.respond(msg, ephemeral=(color is None))
    
  elif custom_color_name is not None and hex is not None:
    msg, color = add_color(custom_color_name, hex)
    await ctx.respond(msg, ephemeral=(color is None))
    
  else:
    await ctx.respond("Please enter a name and hex code or a xkcd color.", ephemeral = True)
#color add end

  
#color recolor start
@colorscg.command(name = "recolor", description = "Recolors the color.")
async def color_recolor(ctx, color_name: Option(str, "Name of color you want to replace color of.", autocomplete=color_picker_autocomplete), hex: Option(str, "Hex color code of new color. The 6 numbers/letters.")):
  with Session.begin() as session:
    msg, color = recolor_color(color_name, hex, session)
    await ctx.respond(msg, ephemeral=color is None)
    if color is not None:
      for user in color.users:
        await edit_role(ctx.author, user.username, color.hex)
#color recolor end

  
#color remove start
@colorscg.command(name = "remove", description = "Removes the color from color list.")
async def color_remove(ctx, color_name: Option(str, "Name of color you want to remove.", autocomplete=color_picker_autocomplete)):
  msg, removed = remove_color(color_name)
  await ctx.respond(msg, ephemeral=not removed)
#color remove end

  
#color rename start
@colorscg.command(name = "rename", description = "Renames the color.")
async def color_rename(ctx, old_color_name: Option(str, "Name of color you want to rename.", autocomplete=color_picker_autocomplete), new_color_name: Option(str, "New name of color.")):
  msg, color = rename_color(old_color_name, new_color_name)
  await ctx.respond(msg, ephemeral=color is None)
#color rename end

  
bot.add_application_command(colorscg)
#color end



    
#profile start
profile = SlashCommandGroup(
  name = "profile", 
  description = "Change your settings.",
  guild_ids = gid,
)


#profile color start
# old sync: Option(int, "Changes you discord color to your color.", choices = yes_no_choices, default=None, required=False)
@profile.command(name = "color", description = "Sets the color of embeds sent with your username.")
async def profile_color(ctx, color_name: Option(str, "Name of color you want to set as your profile color.", autocomplete=color_profile_autocomplete)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return
    if color_name == "First place gold":
      if user.is_in_first_place(get_all_db("User", session)):
        user.set_color(xkcd_colors["xkcd:gold"][1:], session)
        await ctx.respond(f"Profile color is now GOLD.")
      else:
        await ctx.respond("You are not in the first place.", ephemeral=True)
        return
    else:
      if (color := get_color(color_name, session)) is None:
        await ctx.respond(f"Color {color_name} not found. You can add a color by using the command /color add", ephemeral = True)
        return
      user.set_color(color, session)
      await ctx.respond(f"Profile color is now {user.color_name}.")
    
    author = ctx.author
    username = user.username
    sync = 0
    if sync == 1:
      await set_role(ctx.interaction.guild, author, username, user.color_hex, bot)
    elif sync == 0:
      await unset_role(author, username)
    else:
      await edit_role(author, username, user.color_hex)
#profile color end


#profile username start
@profile.command(name = "username", description = "Sets the username for embeds.")
async def profile_username(ctx, username: Option(str, "New username.", required=False, max_value=32)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return
    if username is None:
      await ctx.respond(f"Your username is {user.username}.", ephemeral = True)
      return
    if is_condition_in_db("User", User.username == username, session):
      await ctx.respond(f"Username {username} is already taken.", ephemeral = True)
      return
    old_username = user.username
    user.username = username
    await ctx.respond(f"Username is now {user.username}.")
    await set_role_name(ctx.author, old_username, username)


bot.add_application_command(profile)
#profile end



#graph start
graph = SlashCommandGroup(
  name = "graph", 
  description = "Shows an image of a graph to user.",
  guild_ids = gid,
)



#graph balance start
balance_choices = [
  OptionChoice(name="season", value=0),
  OptionChoice(name="all", value=1),
]

@graph.command(name = "balance", description = "Gives a graph of value over time. No value in type gives you the current season.")
async def graph_balances(ctx,
  type: Option(int, "What type of graph you wany to make.", choices = balance_choices, default = 0, required = False), 
  amount: Option(int, "How many you want to look back. For last only.", default = None, required = False),
  user: Option(discord.Member, "User you want to get balance of.", default = None, required = False),
  compare: Option(str, "Users you want to compare. For compare only", autocomplete=multi_user_list_autocomplete, default = None, required = False),
  high_quality: Option(int, "Do you want the image to be in a higher quality?", choices = yes_no_choices, default=1, required=False)):
  if high_quality == 1:
    dpi = 200
  else:
    dpi = 100
  
  if (user is not None) and (compare is not None):
    await ctx.respond("You can't use compare and user at the same time.", ephemeral = True)
    return
  
  if (user is None) and (compare is None):
    user = ctx.author
  
  with Session.begin() as session:
    if compare is None:
      if (user := await get_user_from_ctx(ctx, user, session)) is None: return
      
      if amount is not None:
        if amount > len(user.balances):
          amount = len(user.balances)
        if amount <= 1:
          await ctx.respond("Amount needs to be higher.", ephemeral = True)
        graph_type = amount
      else:
        if type == 0:
          graph_type = "current"
        elif type == 1:
          graph_type = "all"
        else:
          await ctx.respond("Not a valid type.", ephemeral = True)
          return

      with BytesIO() as image_binary:
        gen_msg = await ctx.respond("Generating graph...")
        image = user.get_graph_image(graph_type, dpi, session)
        if isinstance(image, str):
          await gen_msg.edit_original_message(content = image)
          return
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await gen_msg.edit_original_message(content = "", file=discord.File(fp=image_binary, filename='image.png'))
      return
    

    usernames_split = compare.split(" ")
    
    users = usernames_to_users(compare, session)

    
    if len(users) == 1:
      await ctx.respond("You need to compare more than one user.", ephemeral = True)
      return

    
    usernames = " ".join([user.username for user in users])

    for username_word in usernames_split:
      if username_word not in usernames:
        await ctx.respond(f"User {username_word} not found.", ephemeral = True)
        return

    print(users)

    

    if amount is not None:
      highest_length = 0
      highest_length = len(get_all_unique_balance_ids(users))
      if amount > highest_length:
        amount = highest_length
        if amount <= 1:
          await ctx.respond("Amount needs to be higher.", ephemeral = True)
      graph_type = amount
    else:
      if type == 0:
        graph_type = "current"
      elif type == 1:
        graph_type = "all"
      else:
        await ctx.respond("Not a valid type.", ephemeral = True)
        return

    with BytesIO() as image_binary:
      gen_msg = await ctx.respond("Generating graph...")
      image = get_multi_graph_image(users, graph_type, dpi, session)
      if isinstance(image, str):
        await gen_msg.edit_original_message(content = image)
        return
      image.save(image_binary, 'PNG')
      image_binary.seek(0)
      await gen_msg.edit_original_message(content = "", file=discord.File(fp=image_binary, filename='image.png'))
#graph balance end

bot.add_application_command(graph)
#graph end



#leaderboard start
@bot.slash_command(name = "leaderboard", description = "Gives leaderboard of balances.", guild_ids = gid)
async def leaderboard(ctx):
  embedd = create_leaderboard_embedded()
  await ctx.respond(embed=embedd)
#leaderboard end


  
#log start
@bot.slash_command(name = "log", description = "Shows the last x amount of balance changes (awards, bets, etc)", guild_ids = gid)
async def log(ctx, amount: Option(int, "How many balance changes you want to see."), user: Option(discord.Member, "User you want to check log of (defaulted to you).", default = None, required = False)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, user, session)) is None: return
    
    if amount <= 0:
      await ctx.respond("Amount has to be greater than 0.")
      return
      
    gen_msg = await ctx.respond("Generating log...")
    
    embedds = user.get_new_balance_changes_embeds(amount)
    if embedds is None:
      await gen_msg.edit_original_message(content = "No log generated.", ephemeral = True)
      return

    await gen_msg.edit_original_message(content="", embed=embedds[0])
    for embedd in embedds[1:]:
      await ctx.interaction.followup.send(embed=embedd)
#log end



#loan start
loanscg = SlashCommandGroup(
  name = "loan", 
  description = "Create and pay off loans.",
  guild_ids = gid,
)


#loan create start
@loanscg.command(name = "create", description = "Gives you 50 and adds a loan that you have to pay 50 to close you need less that 100 to get a loan.")
async def loan_create(ctx):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return

    if user.get_clean_bal_loan() >= 100:
      await ctx.respond("You must have less than 100 to make a loan", ephemeral = True)
      return
    
    user.loans.append((50, get_date(), None))
    await ctx.respond(f"{user.username} has been loaned 50")
#loan create end

  
#loan count start
@loanscg.command(name = "count", description = "See how many loans you have active.")
async def loan_count(ctx, user: Option(discord.Member, "User you want to get loan count of.", default = None, required = False)):
  if (user := await get_user_from_ctx(ctx, user)) is None: return
  await ctx.respond(f"{user.username} currently has {len(user.get_open_loans())} active loans")
#loan count end

  
#loan pay start
@loanscg.command(name = "pay", description = "See how many loans you have active.")
async def loan_pay(ctx):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return
      
    loan_amount = user.loan_bal()
    if loan_amount == 0:
      await ctx.respond("You currently have no loans")
      return
    anb = user.get_balance(session)
    if(anb < loan_amount):
      await ctx.respond(f"You need {math.ceil(loan_amount - anb)} more to pay off all loans")
      return

    user.pay_loan(get_date())
      
    await ctx.respond(f"You have paid off a loan")
#loan pay end

bot.add_application_command(loanscg)
#loan end

#generate start
generatescg = SlashCommandGroup(
  name = "generate", 
  description = "Generate things.",
  guild_ids = gid,
)

#generate matches start
@generatescg.command(name = "matches", description = "Generates matches for the current tournaments.")
async def generate_matches(ctx):
  with Session.begin() as session:
    if (len(get_active_tournaments(session)) == 0):
      await ctx.respond("There is no current tournament.", ephemeral = True)
      return
    
    await ctx.respond("Matches are being generated.", ephemeral = True)
    
    await generate_matches_from_vlr(bot, session)
#generate matches end

bot.add_application_command(generatescg)
#generate end

#match start
matchscg = SlashCommandGroup(
  name = "match", 
  description = "Create, edit, and view matches.",
  guild_ids = gid,
)

#match create modal start
class MatchCreateModal(Modal):
  def __init__(self, session, balance_odds=1, vlr_code=None, *args, **kwargs) -> None:
    
    super().__init__(*args, **kwargs)
      
    odds_source = None
    t1, t2 = None, None
    t1oo, t2oo = None, None
    self.balance_odds = balance_odds
    tournament_name, tournament_code = None, None
    self.team1_name = None
    self.team2_name = None
    self.team1_vlr_code = None
    self.team2_vlr_code = None
    self.tournament_name = None
    self.tournament_code = None
    team1 = None
    team2 = None
    if vlr_code is not None:
      match_link = get_match_link(vlr_code)
      print(match_link)
      
      html = urlopen(match_link)
      soup = BeautifulSoup(html, 'html.parser')
      
      t1oo, t2oo = get_odds_from_match_page(soup)
      
      team1, team2 = get_teams_from_match_page(soup, session)
      
      tournament_name, tournament_code = get_tournament_name_and_code_from_match_page(soup)
      
    if t1oo is not None:
      odds_source = "VLR.gg"
    
    if team1 is not None:
      t1, t2 = team1.name, team2.name
      self.team1_name = team1.name
      self.team2_name = team2.name
      self.team1_vlr_code = team1.vlr_code
      self.team2_vlr_code = team2.vlr_code
    
    self.add_item(InputText(label="Enter team one name.", value=t1, placeholder='Get from VLR', min_length=1, max_length=50))
    self.add_item(InputText(label="Enter team two name.", value=t2, placeholder='Get from VLR', min_length=1, max_length=50))
    
    odds_value = None
    if (t1oo is not None) and (t2oo is not None):
      odds_value = f"{t1oo} / {t2oo}"
    self.add_item(InputText(label="Enter odds. Team 1 odds/Team 2 odds.", value=odds_value, placeholder='eg: "2.34/1.75" or "1.43 3.34".', min_length=1, max_length=12))
    
    self.tournament_name = tournament_name
    self.tournament_code = tournament_code
    self.add_item(InputText(label="Enter tournament name.", value=tournament_name, placeholder='Same as VLR.', min_length=1, max_length=100))
    
    self.add_item(InputText(label="Enter odds source.", value=odds_source, placeholder='Please be reputable.', min_length=1, max_length=50))
    self.vlr_code = vlr_code

  
  async def callback(self, interaction: discord.Interaction):
    with Session.begin() as session:
      team_one = self.children[0].value.strip()
      team_two = self.children[1].value.strip()
      
      t1_code, t2_code = None, None
      if self.team1_name == team_one:
        t1_code = self.team1_vlr_code;
      if self.team2_name == team_two:
        t2_code = self.team2_vlr_code;
        
      if (t1_code is None) or (t2_code is None):
        self.vlr_code = None
        
      team1 = get_or_create_team(team_one, t1_code, session)
      team2 = get_or_create_team(team_two, t2_code, session)
      
      odds_combined = self.children[2].value.strip()
      tournament_name = self.children[3].value.strip()
      tournament_code = None
      if self.tournament_name == tournament_name:
        tournament_code = self.tournament_code
      tournament = get_or_create_tournament(tournament_name, tournament_code, session, activate_on_create=False)
      betting_site = self.children[4].value.strip()
      
      
      if odds_combined.count(" ") > 1:
        odds_combined.strip(" ")
        
      splits = [" ", "/", "\\", ";", ":", ",", "-", "_", "|"]
      for spliter in splits:
        if odds_combined.count(spliter) == 1:
          team_one_old_odds, team_two_old_odds = "".join(_ for _ in odds_combined if _ in f".1234567890{spliter}").split(spliter)
          break
      else:
        await interaction.response.send_message(f"Odds are not valid. Odds must be [odds 1]/[odds 2].", ephemeral=True)
        return
      
      if (to_float(team_one_old_odds) is None) or (to_float(team_two_old_odds) is None): 
        await interaction.response.send_message(f"Odds are not valid. Odds must be [odds 1]/[odds 2].", ephemeral=True)
        return
      
      team_one_old_odds = to_float(team_one_old_odds)
      team_two_old_odds = to_float(team_two_old_odds)
      
      if team_one_old_odds <= 1 or team_two_old_odds <= 1:
        await interaction.response.send_message(f"Odds must be greater than 1.", ephemeral=True)
        return
      
      if self.balance_odds == 1:
        team_one_odds, team_two_odds = balance_odds(team_one_old_odds, team_two_old_odds)
      else:
        team_one_odds = team_one_old_odds
        team_two_odds = team_two_old_odds
        
      code = get_unique_code("Match", session)
    
      color = mix_colors([(team1.color_hex, 3), (team2.color_hex, 3), (tournament.color_hex, 1)])
      match = Match(code, team_one, team_two, team_one_odds, team_two_odds, team_one_old_odds, team_two_old_odds, tournament_name, betting_site, color, interaction.user.id, get_date(), self.vlr_code)
      
      
      embedd = create_match_embedded(match, f"New Match: {team_one} vs {team_two}, {team_one_odds} / {team_two_odds}.", session)

      if (channel := await bot.fetch_channel(get_channel_from_db("match", session))) == interaction.channel:
        inter = await interaction.response.send_message(embed=embedd)
        msg = await inter.original_message()
      else:
        msg = await channel.send(embed=embedd)
        await interaction.response.send_message(f"Match created in {channel.mention}.", ephemeral = True)
        
      match.message_ids.append((msg.id, msg.channel.id))
      add_to_db(match, session)
#match create modal end

#match edit modal start
class MatchEditModal(Modal):
  
  def __init__(self, match, locked, balance_odds=1, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    
    self.match = match
    self.balance_odds = balance_odds
    self.locked = locked
    
    self.add_item(InputText(label="Enter team one name.", placeholder=match.t1, min_length=1, max_length=100, required=False))
    self.add_item(InputText(label="Enter team two name.", placeholder=match.t2, min_length=1, max_length=100, required=False))
    
    if not locked:
      self.add_item(InputText(label="Enter odds. Team 1 odds/Team 2 odds.", placeholder=f"{match.t1oo}/{match.t2oo}", min_length=1, max_length=12, required=False))
    self.add_item(InputText(label="Enter tournament name.", placeholder=match.tournament_name, min_length=1, max_length=300, required=False))
    
    self.add_item(InputText(label="Enter odds source.", placeholder=match.odds_source, min_length=1, max_length=100, required=False))

  
  async def callback(self, interaction: discord.Interaction):
    with Session.begin() as session:
      match = get_from_db("Match", self.match.code, session)
      vals = [child.value.strip() for child in self.children]
      
      odds_locked = match.has_bets or match.date_closed != None
      
      if odds_locked:
        team_one, team_two, tournament_name, betting_site = vals
      else:
        team_one, team_two, odds_combined, tournament_name, betting_site = vals
        
        if odds_combined.count(" ") > 1:
          odds_combined.strip(" ")
        if odds_combined == "":
          odds_combined = f"{match.t1oo}/{match.t2oo}"
          
      if team_one == "":
        team_one = match.t1
      if team_two == "":
        team_two = match.t2
      if tournament_name == "":
        tournament_name = match.tournament_name
      if betting_site == "":
        betting_site = match.odds_source
      
      if not odds_locked:
        splits = [" ", "/", "\\", ";", ":", ",", "-", "_", "|"]
        for spliter in splits:
          if odds_combined.count(spliter) == 1:
            team_one_old_odds, team_two_old_odds = "".join(_ for _ in odds_combined if _ in f".1234567890{spliter}").split(spliter)
            break
        else:
          await interaction.response.send_message(f"Odds are not valid. Odds must be [odds 1]/[odds 2].", ephemeral=True)
          return
          
        if (to_float(team_one_old_odds) is None) or (to_float(team_two_old_odds) is None): 
          await interaction.response.send_message(f"Odds are not valid. Odds must be valid decimal numbers.", ephemeral=True)
          return
        
        team_one_old_odds = to_float(team_one_old_odds)
        team_two_old_odds = to_float(team_two_old_odds)
        if team_one_old_odds <= 1 or team_two_old_odds <= 1:
          await interaction.response.send_message(f"Odds must be greater than 1.", ephemeral=True)
          return
        if self.balance_odds == 1:
          odds1 = team_one_old_odds - 1
          odds2 = team_two_old_odds - 1
          
          oneflip = 1 / odds1
          
          percentage1 = (math.sqrt(odds2/oneflip))
          
          team_one_odds = roundup(odds1 / percentage1) + 1
          team_two_odds = roundup(odds2 / percentage1) + 1
        else:
          team_one_odds = team_one_old_odds
          team_two_odds = team_two_old_odds
      
      match.t1 = team_one
      match.t2 = team_two
      if not odds_locked:
        match.t1o = team_one_odds
        match.t2o = team_two_odds
        match.t1oo = team_one_old_odds
        match.t2oo = team_two_old_odds
      else:
        team_one_odds = match.t1o
        team_two_odds = match.t2o
      match.tournament_name = tournament_name
      match.odds_source = betting_site

      if odds_locked:
        for bet in match.bets:
          bet.t1 = team_one
          bet.t2 = team_two
          bet.tournament_name = tournament_name
      
      title = f"Edited Match: {team_one} vs {team_two}, {team_one_odds} / {team_two_odds}."
      embedd = create_match_embedded(match, title, session)
      
      inter = await interaction.response.send_message(embed=embedd)
      msg = await inter.original_message()
      await edit_all_messages(bot, match.message_ids, embedd, title)
      match.message_ids.append((msg.id, msg.channel.id))
#match edit modal end



#match bets start
@matchscg.command(name = "bets", description = "What bets.")
async def match_bets(ctx, match: Option(str, "Match you want bets of.", autocomplete=match_list_autocomplete), type: Option(int, "If type is full it sends the whole embed of each match.", choices = list_choices, default = 0, required = False), show_hidden: Option(int, "Show your hidden bets? Defualt is Yes.", choices = yes_no_choices, default = 1, required = False)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(None, get_current_matches(session), match, "Match", session)) is None:
      if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None: return
    match = nmatch
    
    
    if show_hidden == 1:
      if (user := await get_user_from_ctx(ctx, session=session)) is not None:
        hidden_bets = get_users_hidden_match_bets(user, match.code, session)
    else:
      hidden_bets = []
    
    
    if type == 0:
      #short
      bets = match.bets
      if len(bets) == 0:
        await ctx.respond("No undecided bets.", ephemeral=True)
        return
      if (embedd := create_bet_list_embedded("Bets:", bets, False, session)) is not None:
        await ctx.respond(embed=embedd)
      if (hidden_embedd := create_bet_list_embedded("Your Hidden Bets:", hidden_bets, True, session)) is not None:
        await ctx.respond(embed=hidden_embedd, ephemeral=True)
          
    
    elif type == 1:
      #full
      i = 0
      bets = match.bets
      if len(bets) == 0:
        await ctx.respond("No undecided bets.", ephemeral=True)
      else:
        for i, bet in enumerate(bets):
          user = bet.user
          if bet.hidden:
            embedd = create_bet_hidden_embedded(bet, f"Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}", session)
          else:
            embedd = create_bet_embedded(bet, f"Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
          if i == 0:
            inter = await ctx.respond(embed=embedd)
            msg = await inter.original_message()
          else:
            msg = await ctx.interaction.followup.send(embed=embedd)
          bet.message_ids.append((msg.id, msg.channel.id))
      if hidden_bets is not None:
        for i, bet in enumerate(hidden_bets):
          user = bet.user
          embedd = create_bet_embedded(bet, f"Hidden Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.", session)
          if i == 0:
            await ctx.respond(embed=embedd, ephemeral=True)
          else:
            await ctx.interaction.followup.send(embed=embedd, ephemeral=True)
#match bets end


#match open start
@matchscg.command(name = "open", description = "Open a match.")
async def match_open(ctx, match: Option(str, "Match you want to open.", autocomplete=match_close_list_autocomplete)):
  with Session.begin() as session:
    if (match := await obj_from_autocomplete_tuple(ctx, get_closed_matches(session), match, "Match", session)) is None: return
    if match.date_closed == None:
      await ctx.respond(f"Match {match.t1} vs {match.t2} is already open.", ephemeral=True)
      return
    match.date_closed = None
    await ctx.respond(f"{match.t1} vs {match.t2} betting has opened.")
    embedd = create_match_embedded(match, "Placeholder", session)
  await edit_all_messages(bot, match.message_ids, embedd)
#match open end


#match close start
#balance_odds: Option(int, "Balance the odds? Defualt is Yes.", choices = yes_no_choices, default=1, required=False)
@matchscg.command(name = "close", description = "Close a match.")
async def match_close(ctx, match: Option(str, "Match you want to close.", autocomplete=match_open_list_autocomplete)):
  with Session.begin() as session:
    if (match := await obj_from_autocomplete_tuple(ctx, get_open_matches(session), match, "Match", session)) is None: return
    if match.date_closed != None:
      await ctx.respond(f"Match {match.t1} vs {match.t2} is already closed.", ephemeral=True)
      return
    await match.close(bot, ctx, session)
#match close end

#match create start
@matchscg.command(name = "create", description = "Create a match.")
async def match_create(ctx):
  with Session.begin() as session:
    match_modal = MatchCreateModal(session, title="Create Match")
    await ctx.interaction.response.send_modal(match_modal)
#match create end

#match generate start
@matchscg.command(name = "generate", description = "Generate a match.")
async def match_generate(ctx, vlr_link: Option(str, "Link of vlr match.")):
  vlr_code = get_code(vlr_link)
  print(vlr_code)
  with Session.begin() as session:
    if (match := get_match_from_vlr_code(vlr_code, session)) is not None:
      await ctx.respond(f"Match {match.t1} vs {match.t2} already exists.", ephemeral=True)
      return
    
    match_modal = MatchCreateModal(session, vlr_code=vlr_code, title="Generate Match")
    await ctx.interaction.response.send_modal(match_modal)
#match generate end

#match delete start
@matchscg.command(name = "delete", description = "Delete a match. Can only be done if betting is open.")
async def match_delete(ctx, match: Option(str, "Match you want to delete.", autocomplete=match_current_list_autocomplete)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(ctx, get_current_matches(session), match, "Match", session)) is None:
      await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
      return
    match = nmatch
    
    if match.winner != 0:
      await ctx.respond(f"Match winner has already been decided, you cannot delete the match.", ephemeral = True)
      return
      
    embedd = create_match_embedded(match, f"Deleted Match: {match.t1} vs {match.t2}, {match.t1o} / {match.t2o}, and all bets on the match.", session)
    await ctx.respond(content="", embed=embedd)
      
    await delete_from_db(match, bot, session=session)
#match delete end
  

#match find start
@matchscg.command(name = "find", description = "Sends the embed of the match.")
async def match_find(ctx, match: Option(str, "Match you want embed of.", autocomplete=match_list_autocomplete)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(None, get_current_matches(session), match, "Match", session)) is None:
      if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None: 
        await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
        return
    match = nmatch
    embedd = create_match_embedded(match, f"Match: {match.t1} vs {match.t2}, {match.t1o} / {match.t2o}.", session)
    inter = await ctx.respond(embed=embedd)
    msg = await inter.original_message()
    match.message_ids.append((msg.id, msg.channel.id))
#match find end


#match edit start
@matchscg.command(name = "edit", description = "Edit a match.")
async def match_edit(ctx, match: Option(str, "Match you want to edit.", autocomplete=match_list_autocomplete), balance_odds: Option(int, "balance the odds? Defualt is Yes.", choices = yes_no_choices, default=1, required=False)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(None, get_open_matches(session), match, "Match", session)) is None:
      if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None: 
        await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
        return
    match = nmatch
    match_modal = MatchEditModal(match, (match.date_closed is not None) and match.bets != [], balance_odds, title="Edit Match")
    await ctx.interaction.response.send_modal(match_modal)
#match edit end


#match list start
@matchscg.command(name = "list", description = "Sends embed with all matches. If type is full it sends the whole embed of each match.")
async def match_list(ctx, type: Option(int, "If type is full it sends the whole embed of each match.", choices = list_choices, default = 0, required = False)):
  with Session.begin() as session:
    
    matches = get_current_matches(session)
    
    if len(matches) == 0:
      await ctx.respond("No undecided matches.", ephemeral = True)
      return

    if type == 0:
      #short
      await respond_send_match_list_embedded(ctx, "Matches: ", matches, session)
    elif type == 1:
      #full
      for i, match in enumerate(matches):
        embedd = create_match_embedded(match, f"Match: {match.t1} vs {match.t2}, {match.t1o} / {match.t2o}.", session)
        if i == 0:
          inter = await ctx.respond(embed=embedd)
          msg = await inter.original_message()
        else:
          msg = await ctx.interaction.followup.send(embed=embedd)
        match.message_ids.append((msg.id, msg.channel.id))
#match list end
  
  
#match winner start
@matchscg.command(name = "winner", description = "Set winner of match.")
async def match_winner(ctx, match: Option(str, "Match you want to set winner of.", autocomplete=match_current_list_autocomplete), team: Option(str, "Team to set to winner.", autocomplete=match_team_list_autocomplete)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(ctx, get_current_matches(session), match, "Match", session)) is None:
      await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
      return
    match = nmatch
    
    team.strip()
    
    await match.set_winner(team, bot, ctx, session)
#match winner end


#match reset start
@matchscg.command(name = "reset", description = "Change winner or go back to no winner.")
async def match_winner(ctx, match: Option(str, "Match you want to reset winner of."), team: Option(str, "Team to set to winner.", autocomplete=match_reset_winner_list_autocomplete), new_date: Option(int, "Do you want to reset the winner set date?", choices = yes_no_choices)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None:
      await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
      return
    match = nmatch
    
    new_date = new_date == 1
    
    team.strip()
    if (team == "1") or (team == match.t1):
      team = 1
    elif (team == "2") or (team == match.t2):
      team = 2
    elif (team == "0") or (team == "None") or (team == "Set winner to none"):
      team = 0
    else:
      await ctx.respond(f"Invalid team name of {team} please enter {match.t1}, {match.t2}, or None.", ephemeral = True)
      return
    
    if int(match.winner) == team:
      await ctx.respond(f"Winner has already been set to {match.winner_name()}", ephemeral = True)
      return
      
    gen_msg = await ctx.respond("Reseting match...")
    
    match.winner = team
    if new_date:
      match.date_winner = get_date()
      print(get_date(), match.date_winner)
    
    if match.date_closed is None:
      match.date_closed = match.date_winner
      
    m_embedd = create_match_embedded(match, "Placeholder", session)

    for bet in match.bets:
      user = bet.user
      user.remove_balance_id(f"id_{bet.code}", session)

    if match.winner == 0:
      for bet in match.bets:
        bet.winner = 0
      await gen_msg.edit_original_message(content="Winner has been set to None.")
      return
    
    odds = 0.0
    #change when autocomplete
    if team == 1:
      odds = match.t1o
      await gen_msg.edit_original_message(content=f"Winner has been set to {match.t1}.")
    else:
      odds = match.t2o
      await gen_msg.edit_original_message(content=f"Winner has been set to {match.t2}.")

    msg_ids = []
    users = []
    date = match.date_winner
    for bet in match.bets:
      bet.winner = int(match.winner)
      payout = -bet.amount_bet
      if bet.team_num == team:
        payout += bet.amount_bet * odds
      user = bet.user
      add_balance_user(user, payout, "id_" + str(bet.code), date)

      embedd = create_bet_embedded(bet, "Placeholder", session)
      msg_ids.append((bet.message_ids, embedd))
      users.append(user.code)

    no_same_list_user = []
    [no_same_list_user.append(x) for x in users if x not in no_same_list_user]
    for user in no_same_list_user:
      embedd = create_user_embedded(user, session)
      await ctx.respond(embed=embedd)

    await edit_all_messages(bot, match.message_ids, m_embedd)
    [await edit_all_messages(bot, tup[0], tup[1]) for tup in msg_ids]
#match reset end
  
  
bot.add_application_command(matchscg)
#match end


#backup start
@bot.slash_command(name = "backup", description = "Backup the database.")
async def backup(ctx):
  backup_full()
  await ctx.respond("Backup complete.", ephemeral = True)
#backup end

  
#hidden command
@bot.slash_command(name = "hide_from_leaderboard", description = "Do not user command if not Pig, Hides you from alot of interations.")
async def hide_from_leaderboard(ctx):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(None, ctx.author, session)) is None: return
    user.hidden = not user.hidden
    print(user.hidden)

#tournament start
tournamentsgc = SlashCommandGroup(
  name = "tournament", 
  description = "Start, color, and rename tournaments.",
  guild_ids = gid,
)

#tournament start start
@tournamentsgc.command(name = "start", description = "Startes a tournament. Pick one color to fill")
async def tournament_start(ctx, vlr_link: Option(str, "VLR link of tournament.")):
  code = get_code(vlr_link)
  if code is None:
    await ctx.respond("Invalid VLR link.", ephemeral = True)
    return
  
  with Session.begin() as session:
    if (tournament := generate_tournament(code, session)) is None:
      await ctx.respond(f'Tournament already exists.', ephemeral = True)
      return
    
    embedd = create_tournament_embedded(f"New Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament start end

#tournament matches start
@tournamentsgc.command(name = "matches", description = "What matches.")
async def tournament_matches(ctx, tournament: Option(str, "Tournament you want matches of.", autocomplete=tournament_autocomplete), type: Option(int, "If type is full it sends the whole embed of each match.", choices = list_choices, default = 0, required = False)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), tournament, "Tournament", session)) is None: return
    
    matches = tournament.matches
    if len(matches) == 0:
      await ctx.respond("No matches in tournament.", ephemeral=True)
      return
    
    if type == 0:
      #short
      await respond_send_match_list_embedded(ctx, f"Matches in {tournament.name}: ", matches, session)
    elif type == 1:
      #full
      for i, match in enumerate(matches):
        embedd = create_match_embedded(match, f"Match: {match.t1} vs {match.t2}, {match.t1o} / {match.t2o}.", session)
        if i == 0:
          inter = await ctx.respond(embed=embedd)
          msg = await inter.original_message()
        else:
          msg = await ctx.interaction.followup.send(embed=embedd)
          match.message_ids.append((msg.id, msg.channel.id))
#tournament matches end

#tournament recolor start
@tournamentsgc.command(name = "recolor", description = "Changes the color of a tournament.")
async def tournament_recolor(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete),
                           xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False),
                           color_name:Option(str, "Name of color you want to add.", autocomplete=color_picker_autocomplete, required=False), 
                           hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None: return
    color = await get_color_from_options(ctx, hex, xkcd_color_name, color_name, session)
    if color is None:
      return
    
    tournament.set_color(color, session)
    await ctx.respond(f'Tournament "{tournament.name}" color changed.')
    embedd = create_tournament_embedded(f"Recolor Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament recolor end

#tournament rename start
@tournamentsgc.command(name = "rename", description = "Renames a tournament.")
async def tournament_rename(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete),
                            new_name: Option(str, "New name of tournament.")):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None: return
    for match in tournament.matches:
      match.tournament_name = new_name
    for bet in tournament.bets:
      bet.tournament_name = new_name
    tournament.name = new_name
    embedd = create_tournament_embedded(f"Updated Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament rename end

#tournament find start
@tournamentsgc.command(name = "find", description = "Finds a tournament.")
async def tournament_find(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None: return
    embedd = create_tournament_embedded(f"Found Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament find end

#tournament activate start
@tournamentsgc.command(name = "activate", description = "Activates a tournament.")
async def tournament_activate(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_inactive_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_inactive_tournaments(session), name, "Tournament", session)) is None: return
    if tournament.active:
      await ctx.respond("Tournament already active.", ephemeral = True)
      return
    tournament.active = True
    embedd = create_tournament_embedded(f"Activated Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament activate end

#tournament deactivate start
@tournamentsgc.command(name = "deactivate", description = "Deactivates a tournament.")
async def tournament_deactivate(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_active_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_active_tournaments(session), name, "Tournament", session)) is None: return
    if not tournament.active:
      await ctx.respond("Tournament already inactive.", ephemeral = True)
      return
    tournament.active = False
    embedd = create_tournament_embedded(f"Deactivated Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament deactivate end

#tournament link start
@tournamentsgc.command(name = "link", description = "Links a tournament to a vlr code.")
async def tournament_link(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete),
                          vlr_link: Option(str, "VLR link of tournament.")):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None: return
    code = get_code(vlr_link)
    if code is None:
      await ctx.respond("Not a valid team link.", ephemeral = True)
      return
    tournament.vlr_code = code
    embedd = create_tournament_embedded(f"Linked Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament link end

bot.add_application_command(tournamentsgc)
#tournament end

#team start
teamsgc = SlashCommandGroup(
  name = "team", 
  description = "Create and manage teams.",
  guild_ids = gid,
)

#team generate start
@teamsgc.command(name = "generate", description = "Generate a team or updates a prexisting team.")
async def team_generate(ctx, vlr_link: Option(str, "Link of vlr tournament.")):
  code = get_code(vlr_link)
  if code is None:
    await ctx.respond("Not a valid team link.", ephemeral = True)
    return
  with Session.begin() as session:
    team = generate_team(code, session)
    embedd = create_team_embedded(f"Generated Tournament: {team.name}", team)
    await ctx.respond(embed=embedd)
#team generate end

#team update start
@teamsgc.command(name = "update", description = "Updates a team's name and vlr code.")
async def team_generate(ctx, team: Option(str, "Name of team.", autocomplete=team_autocomplete),):
  with Session.begin() as session:
    if (team := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), team, "Team", session)) is None: return
    if team.vlr_code is None:
      await ctx.respond("Team has no vlr code.", ephemeral = True)
      return
    team = generate_team(team.vlr_code, session)
    embedd = create_team_embedded(f"Updated Team: {team.name}", team)
    await ctx.respond(embed=embedd)
#team update end

#team update_all start
@teamsgc.command(name = "update_all", description = "Updates all team colors and names. WILL TAKE A WHILE.")
async def team_generate(ctx):
  await ctx.respond("Updateing all team colors.")
  with Session.begin() as session:
    for team in get_all_db("Team", session):
      if team.vlr_code is None: continue
      team = generate_team(team.vlr_code, session)
      embedd = create_team_embedded("Updated Team:", team)
      await ctx.channel.send(embed=embedd)
#team update_all end

#team merge start
@teamsgc.command(name = "merge", description = "Merge two teams.")
async def team_merge(ctx, new: Option(str, "Team to keep.", autocomplete=team_autocomplete),
                     old: Option(str, "Team to merge into other team.", autocomplete=team_autocomplete)):
  with Session.begin() as session:
    if (t1 := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), new, "Team", session)) is None: return
    if (t2 := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), old, "Team", session)) is None: return
    if t1 == t2:
      await ctx.respond("Teams are the same.", ephemeral = True)
      return
    t1.merge(t2, session)
    embedd = create_team_embedded(f"Merged Team {t2.name} into: {t1.name}", t1)
    await ctx.respond(embed=embedd)
    
  with Session.begin() as session:
    if (t2 := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), old, "Team", session)) is None: return
    session.delete(t2)
#team merge end

#team recolor start
@teamsgc.command(name = "recolor", description = "Changes the color of a team.")
async def team_recolor(ctx, name: Option(str, "Name of team.", autocomplete=team_autocomplete),
                           xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False),
                           color_name: Option(str, "Name of color you want to add.", autocomplete=color_picker_autocomplete, required=False), 
                           hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False)):
  with Session.begin() as session:
    if (team := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), name, "Team", session)) is None: return
    
    if xkcd_color_name == None and color_name == None and hex == None:
      team = generate_team(team.vlr_code, session)
      embedd = create_team_embedded(f"Updated Team: {team.name}", team)
      await ctx.respond(embed=embedd)
      return
    
    color = await get_color_from_options(ctx, hex, xkcd_color_name, color_name, session)
    if color is None:
      return
    
    team.set_color(color, session)
    await ctx.respond(f'Team "{team.name}" color changed.')
    embedd = create_team_embedded(f"Recolored Team: {team.name}", team)
    await ctx.respond(embed=embedd)
#team recolor end

#team find start
@teamsgc.command(name = "find", description = "Find a team.")
async def team_find(ctx, name: Option(str, "Name of team.", autocomplete=team_autocomplete)):
  with Session.begin() as session:
    if (team := await obj_from_autocomplete_tuple(ctx, get_all_db("Team", session), name, "Team", session)) is None: return
    embedd = create_team_embedded(f"Team: {team.name}", team)
    await ctx.respond(embed=embedd)
#team find end


bot.add_application_command(teamsgc)
#team end


#season start
seasonsgc = SlashCommandGroup(
  name = "season", 
  description = "Start and rename season.",
  guild_ids = gid,
)

#season start start
@seasonsgc.command(name = "start", description = "Do not user command if not Pig, Start a new season.")
async def season_start(ctx, name: Option(str, "Name of new season.")):
  # to do make the command also include season name
  with Session.begin() as session:
    users = get_all_db("User", session)

    code = all_user_unique_code("reset_", users)
    date = get_date()
    name = f"reset_{code}_{name}"
    for user in users:
      user.balances.append((name, Decimal(500), date))
      for _ in user.get_open_loans():
        user.pay_loan(date)
    await ctx.respond(f"New season {name} has sarted.")
#season start end


#season rename start
@seasonsgc.command(name = "rename", description = "Rename season.")
async def season_rename(ctx, season: Option(str, "Description of award you want to rename.", autocomplete=seasons_autocomplete), name: Option(str, "Name of new season.")):
  
  with Session.begin() as session:
    found = False
    for user in get_all_db("User", session):
      if user.change_reset_name(season[-8:], name, session) != None:
        found = True
    if found:
      await ctx.respond(f"Season {season.split(',')[0]} has been renamed to {name}.")
    else:
      await ctx.respond(f"Season {season} not found.", ephemeral = True)
#season rename end


bot.add_application_command(seasonsgc)
#season end


#update_bets start
@bot.slash_command(name = "update_bets", description = "Do not user command if not Pig, Debugs some stuff.")
async def update_bets(ctx):
  with Session.begin() as session:
    for bets in get_all_db("Bet", session):
      match = bets.match
      bets.t1 = match.t1
      bets.t2 = match.t1
      bets.tournament_name = match.tournament_name
  await ctx.respond("Set all bets.", ephemeral = True)
#update_bets end


#debug command
@bot.slash_command(name = "check_balance_order", description = "Do not user command if not Pig, Debugs some stuff.")
async def check_balance_order(ctx):
  #check if the order of user balance and the order of time in balances[2] are the same
  users = get_all_db("User")
  for user in users:
    sorted = user.balances.copy()
    sorted.sort(key=lambda x: x[2])
    if sorted != user.balances:
      await ctx.respond(f"{user.code} balance order is wrong", ephemeral = True)
      print(f"{user.code} balance order is wrong")
  await ctx.respond("check order done.", ephemeral = True)
  print("check order done")

token = get_setting("discord_token")
#print(f"discord: {token}")
bot.run(token)
