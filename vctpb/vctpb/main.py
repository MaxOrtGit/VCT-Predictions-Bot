
import os
# check for settings.ini
if not os.path.exists("settings.ini"):
  print("settings.ini not found")
  exit()

# updates the sql library, if you are too out of date it may not work
if (os.path.exists("savedata/savedata.db")):
  import alembic.config
  alembicArgs = [
      '--raiseerr',
      'upgrade', 'head',
  ]
  alembic.config.main(argv=alembicArgs)

from alembic import command
from alembic.config import Config
# add moddifacation when no on incorrect match creation
# test bet list with and without await
# have it replace by code not by value
# test prefix unique with 1 long in test code

from io import BytesIO
from urllib.request import urlopen

from bs4 import BeautifulSoup, SoupStrainer
import lxml
#import cchardet
import requests
#git clone https://github.com/Pycord-Development/pycord
#cd pycord
#python3 -m pip install -U .[voice]

#pip install git+https://github.com/Pycord-Development/pycord
#poetry add git+https://github.com/Pycord-Development/pycord
import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup
from discord.ext import tasks, commands
import random
import jsonpickle
from Match import Match
from Bet import Bet
from User import User, get_multi_graph_image, all_user_unique_code, get_all_unique_balance_ids, num_of_bal_with_name, get_first_place, add_balance_user
from Team import Team
from Tournament import Tournament
from Channels import Channels
from dbinterface import *
from colorinterface import *
import math
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont
from convert import *
from objembed import *
from savefiles import backup
from savedata import backup_full
import secrets
import atexit
from autocompletes import *
from vlrinterface import get_match_link, odds_labels

from vlrinterface import generate_matches_from_vlr, get_code, generate_tournament, get_match_response
from sqlaobjs import Session, mapper_registry, Engine
from utils import *
from modals import MatchCreateModal, MatchEditModal, BetCreateModal, BetEditModal
from views import *
# issue with Option in command function
# pyright: reportGeneralTypeIssues=false

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

      
def rename_balance_id(user, balance_id, new_balance_id):
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

def print_all_balances(user):
  [print(bal[0], bal[1]) for bal in user.balances]


def create_user(user_id, username, session):
  random.seed()
  color = secrets.token_hex(3)
  user = User(user_id, username, color, get_date())
  print(jsonpickle.encode(user), session)
  add_to_db(user, session)
  return user

def create_db():
  mapper_registry.metadata.create_all(Engine)
  # sets to current version
  alembic_cfg = Config("alembic.ini")
  command.stamp(alembic_cfg, "head")
  with Session.begin() as session:
    # add new row to channels
    add_to_db(Channels(-1, -1, -1), session)
  print("\n\n\n\n\n\n\n-----------Created DB, please rerun bot-----------")
  print("-----------When you rerun the bot set the channels with /assign-----------\n\n\n\n\n\n\n")
  exit()
  

@bot.event
async def on_ready():
  try:
    print("Logged in as {0.user}".format(bot))
    print(bot.guilds)
    
    #if savedata does not exist pull
    if not os.path.exists("savedata"):
      print("savedata folder does not exist")
      os.mkdir("savedata")
    #check if file savedata.db exists
    if not os.path.exists("savedata/savedata.db"):
      print("-----------No Savedata File Found-----------")
      print("-----------Download from Github if you have it-----------")
      while ((inp := input("Do you want to create a new database? (y/n) ")) != "y") and inp != "n":
        print("Invalid input")
      if inp == "y":
        create_db()
      else:
        exit()
      
  except Exception as e:
    print("-----------Bot Failed to Start-----------")
    raise e
  atexit.register(backup_full)
  auto_backup_timer.start()
  print("\n-----------Bot Starting-----------\n")
  auto_generate_matches_from_vlr_timer.start()
  bot.add_view(MatchView(bot, None))
  bot.add_view(BetView(bot, None))
  bot.add_view(MatchListView(bot, None))
  bot.add_view(AvailableMatchListView(bot, None))
  bot.add_view(BetListView(bot))
  print("\n-----------Bot Started-----------\n")


@tasks.loop(hours=1)
async def auto_backup_timer():
  try:
    backup_full()
  except Exception as e:
    print(e)
    print("-----------Backup Failed-----------")

@tasks.loop(minutes=5)
async def auto_generate_matches_from_vlr_timer():
  try:
    #print("-----------Generating Matches-----------")
    with Session.begin() as session:
      await generate_matches_from_vlr(bot, session, reply_if_none=False)
  except Exception as e: 
    print(e)
    print("-----------Generating Matches Failed-----------")
  

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
  
  date = get_date()
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
        abu = add_balance_user(user, amount, bet_id, get_date())
        embedd = create_user_embedded(abu, session)
        if first:
          await ctx.respond(embed=embedd)
          first = False
        else:
          await ctx.interaction.followup.send(embed=embedd)
        while user.loan_bal() != 0 and user.get_clean_bal_loan() > 500:
          user.pay_loan(date)
      return
    else:
      if (user := await get_user_from_ctx(ctx, user, session)) is None: return
      bet_id = "award_" + user.get_unique_bal_code() + "_" + description
      print(bet_id)
      abu = add_balance_user(user, amount, bet_id, get_date())
      if abu is None:
        await ctx.respond("User not found.", ephemeral = True)
      else:
        while user.loan_bal() != 0 and user.get_clean_bal_loan() > 500:
          user.pay_loan(date)
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
    
    await ctx.respond(f"Award {award.split(', ')[0]} reawarded to {amount}.")
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
      await ctx.respond("Match betting has closed, you cannot create the bet.", ephemeral=True)
      return
    
    for bet in user.active_bets:
      if bet.match_id == match.code:
        await ctx.respond("You already have a bet on this match.", ephemeral=True)
        return
    hidden = hide == 1
    bet_modal = BetCreateModal(match, user, hidden, session, title="Create bet", bot=bot)
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
      embedd = create_bet_embedded(bet, f"Cancelled Bet")
    else:
      embedd = create_bet_hidden_embedded(bet, f"Cancelled Bet")
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

    bet_modal = BetEditModal(hide, match, user, bet, session, bot, title="Edit Bet")
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
      embedd = create_bet_embedded(bet, f"Bet")
      inter = await ctx.respond(embed=embedd, ephemeral=bet.hidden, view=BetView(bot, bet))
      if not bet.hidden:
        await bet.message_ids.append(inter)
    else:
      embedd = create_bet_hidden_embedded(bet, f"Bet")
      ephemeral = (bet.hidden and (bet.user_id == ctx.user.id))
      inter = await ctx.respond(embed=embedd, ephemeral=ephemeral, view=BetView(bot, bet))
      if not(bet.hidden and (bet.user_id == ctx.user.id)):
        await bet.message_ids.append(inter)
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
    title = f"Bet"
    embedd = create_bet_hidden_embedded(bet, title, session)
    inter = await ctx.respond(embed=embedd)
    await bet.message_ids.append(inter)
  await edit_all_messages(bot, bet.message_ids, embedd)
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
    title = f"Bet"
    embedd = create_bet_embedded(bet, title)
    view = BetView(bot, bet)
    inter = await ctx.respond(embed=embedd, view=view)
    await bet.message_ids.append(inter)
  await edit_all_messages(bot, bet.message_ids, embedd, view=view)
#bet show end


#bet list start
@betscg.command(name = "list", description = "Sends embed with all undecided bets. If type is full it sends the whole embed of each bet.")
async def bet_list(ctx, type: Option(int, "If type is full it sends the whole embed of each bet.", choices = list_choices, default = 0, required = False), show_hidden: Option(int, "Show your hidden bets? Defualt is Yes.", choices = yes_no_choices, default = 1, required = False)):
  with Session.begin() as session:
    
    hidden_bets = []
    user = None
    if show_hidden == 1:
      if (user := await get_user_from_ctx(ctx, session=session)) is not None:
        hidden_bets = get_users_hidden_current_bets(user, session)
    
    
    if type == 0:
      #short
      await send_bet_list_embedded("Bets", get_current_bets(session), bot, ctx, user=user) 
    
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
            embedd = create_bet_hidden_embedded(bet, f"Bet")
          else:
            embedd = create_bet_embedded(bet, f"Bet")
          view = BetView(bot, bet)
          if i == 0:
            msg = await ctx.respond(embed=embedd, view=view)
          else:
            msg = await ctx.interaction.followup.send(embed=embedd, view=view)
          await bet.message_ids.append(msg)
      if hidden_bets is not None:
        for i, bet in enumerate(hidden_bets):
          user = bet.user
          embedd = create_bet_embedded(bet, f"Hidden Bet")
          view = BetView(bot, bet)
          if i == 0:
            await ctx.respond(embed=embedd, ephemeral=True, view=view)
          else:
            await ctx.interaction.followup.send(embed=embedd, ephemeral=True, view=view)
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
async def color_add(ctx, custom_color_name: Option(str, "Name of color you want to add.", required=False), 
                         hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False), 
                         xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False)):
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
async def profile_color(ctx, xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False),
                             color_name:Option(str, "Name of color you want to add.", autocomplete=color_picker_autocomplete, required=False), 
                             hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, session=session)) is None: return
    if color_name == "First place gold":
      if user.is_in_first_place(get_all_db("User", session)):
        user.set_color(xkcd_colors["xkcd:gold"][1:], session)
        await ctx.respond(f"Profile color is now GOLD.")
      else:
        await ctx.respond("You are not in the first place.", ephemeral=True)
      return
    else:
      if (color := await get_color_from_options(ctx, hex, xkcd_color_name, color_name, session)) is None: return
      user.set_color(color, session)
      if xkcd_color_name is not None:
        title = f"Profile color is now {xkcd_color_name}."
      elif color_name is not None:
        title = f"Profile color is now {color_name}."
      else: #hex
        title = f"Profile color is now #{user.color_hex}."
      embed = discord.Embed(title=title, color=discord.Color.from_rgb(*hex_to_tuple(user.color_hex)))
      await ctx.respond(embed=embed, ephemeral=True)
#profile color end


#profile username start
@profile.command(name = "username", description = "Sets the username for embeds.")
async def profile_username(ctx, username: Option(str, "New username.", required=False, max_length=32)):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, session=session)) is None: return
    if username is None:
      await ctx.respond(f"Your username is {user.username}.", ephemeral = True)
      return
    if is_condition_in_db("User", User.username == username, session):
      await ctx.respond(f"Username {username} is already taken.", ephemeral = True)
      return
    old_username = user.username
    user.username = username
    await ctx.respond(f"Username is now {user.username}.")


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
  type: Option(int, "What type of graph you want to make.", choices = balance_choices, default = 0, required = False), 
  amount: Option(int, "How many you want to look back.", default = None, required = False),
  user: Option(discord.Member, "User you want to get balance of.", default = None, required = False),
  compare: Option(str, "Users you want to compare.", autocomplete=multi_user_list_autocomplete, default = None, required = False),
  compare_top: Option(int, "How many users you want to compare.", default = None, required = False),
  high_quality: Option(int, "Do you want the image to be in a higher quality?", choices = yes_no_choices, default=1, required=False)):
  if high_quality == 1:
    dpi = 200
  else:
    dpi = 100
  
  if (user is not None) and ((compare is not None) or (compare_top is not None)):
    await ctx.respond("You can't use compare and user at the same time.", ephemeral = True)
    return
  
  if (compare is not None) and (compare_top is not None):
    await ctx.respond("You can't use compare and compare_top at the same time.", ephemeral = True)
  
  if (user is None) and (compare is None):
    user = ctx.author
  
  with Session.begin() as session:
    if (compare is None) and (compare_top is None):
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
        gen_msg = await ctx.respond("Generating graph... (this might take a while)")
        image = user.get_graph_image(graph_type, dpi, session)
        if isinstance(image, str):
          await gen_msg.edit_original_response(content = image)
          return
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await gen_msg.edit_original_response(content = "", file=discord.File(fp=image_binary, filename='image.png'))
      return
    
    # multi
    if compare_top is not None:
      if compare_top < 1:
        await ctx.respond("Compare top needs to be higher.", ephemeral = True)
        return
      users = get_top_active_users(compare_top, session)
    else:
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
      gen_msg = await ctx.respond("Generating graph... (this might take a while)")
      image = get_multi_graph_image(users, graph_type, dpi, session)
      if isinstance(image, str):
        await gen_msg.edit_original_response(content = image)
        return
      image.save(image_binary, 'PNG')
      image_binary.seek(0)
      await gen_msg.edit_original_response(content = "", file=discord.File(fp=image_binary, filename='image.png'))
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
    if (user := await get_user_from_ctx(ctx, session=session)) is None: return

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
    if (user := await get_user_from_ctx(ctx, session=session)) is None: return
      
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

#match bets start
@matchscg.command(name = "bets", description = "What bets.")
async def match_bets(ctx, match: Option(str, "Match you want bets of.", autocomplete=match_list_autocomplete), type: Option(int, "If type is full it sends the whole embed of each match.", choices = list_choices, default = 0, required = False), show_hidden: Option(int, "Show your hidden bets? Defualt is Yes.", choices = yes_no_choices, default = 1, required = False)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(None, get_current_matches(session), match, "Match", session)) is None:
      if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None: return
    match = nmatch
    if (user := await get_user_from_ctx(ctx, session=session)) is None: return
    
    hidden_bets = []
    if show_hidden == 1:
      if (user := await get_user_from_ctx(ctx, session=session)) is not None:
        hidden_bets = get_users_hidden_match_bets(user, match.code, session)
    
    
    if type == 0:
      #short
      await send_bet_list_embedded("Bets", get_current_bets(session), bot, ctx, user=user)
          
    
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
            embedd = create_bet_hidden_embedded(bet, f"Bet")
          else:
            embedd = create_bet_embedded(bet, f"Bet")
          view = BetView(bot, bet)
          if i == 0:
            msg = await ctx.respond(embed=embedd, view=view)
          else:
            msg = await ctx.interaction.followup.send(embed=embedd, view=view)
          await bet.message_ids.append(msg)
      if hidden_bets is not None:
        for i, bet in enumerate(hidden_bets):
          user = bet.user
          embedd = create_bet_embedded(bet, f"Hidden Bet")
          view = BetView(bot, bet)
          if i == 0:
            await ctx.respond(embed=embedd, ephemeral=True, view=view)
          else:
            await ctx.interaction.followup.send(embed=embedd, ephemeral=True, view=view)
#match bets end


#match open start
@matchscg.command(name = "open", description = "Open a match.")
async def match_open(ctx, match: Option(str, "Match you want to open.", autocomplete=match_close_list_autocomplete)):
  with Session.begin() as session:
    if (match := await obj_from_autocomplete_tuple(ctx, get_closed_matches(session), match, "Match", session)) is None: return
    await match.open(bot, session, ctx)
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
    await match.close(bot, session, ctx)
#match close end

#match create start
@matchscg.command(name = "create", description = "Create a match.")
async def match_create(ctx):
  with Session.begin() as session:
    match_modal = MatchCreateModal(session, title="Create Match", bot=bot)
    await ctx.interaction.response.send_modal(match_modal)
#match create end


#match generate start
@matchscg.command(name = "generate", description = "Generate a match. (rerun a couple times if it doesn't work)")
async def match_generate(ctx, vlr_link: Option(str, "Link of vlr match."), pull_odds: Option(int, "Pull odds from vlr? Defualt is Yes.", choices = yes_no_choices, default=1, required=False)):
  vlr_code = get_code(vlr_link)
  
  with Session.begin() as session:
    if (match := get_match_from_vlr_code(vlr_code, session)) is not None:
      await ctx.respond(f"Match {match.t1} vs {match.t2} already exists.", ephemeral=True)
      return
    match_link = get_match_link(vlr_code)
    print(match_link)
    time = datetime.now()
    response = await get_match_response(match_link, pull_odds * 4, repeat = 1)
    print(f"time 0: {datetime.now() - time}")
    if response is None:
      await ctx.respond(f"Match {vlr_code} does not exist.", ephemeral=True)
      return
    time = datetime.now()
    print("soup 1")
    strainer = SoupStrainer(['div', 'a'], class_=['match-header-vs', "wf-card mod-dark match-bet-item", "match-header-event"])
    soup = BeautifulSoup(response, 'lxml', parse_only=strainer)
    print(f"time 2: {datetime.now() - time}")
    time = datetime.now()
    if soup is None:
      await ctx.respond(f"Match {vlr_code} does not exist.", ephemeral=True)
      return
    match_modal = MatchCreateModal(session, vlr_code=vlr_code, soup=soup, title="Generate Match", bot=bot)
    await ctx.interaction.response.send_modal(match_modal)
    print(f"time 3: {datetime.now() - time}")
    time = datetime.now()
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
      
    embedd = create_match_embedded(match, f"Deleted Match")
    await ctx.respond(embed=embedd, view=MatchView(bot, match))
      
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
    embedd = create_match_embedded(match, f"Match")
    inter = await ctx.respond(embed=embedd, view=MatchView(bot, match))
    await match.message_ids.append(inter)
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
    match_modal = MatchEditModal(match, (match.date_closed is not None) and match.bets != [], balance_odds, title="Edit Match", bot=bot)
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
      await send_match_list_embedded(f"Matches", matches, bot, ctx)
    elif type == 1:
      #full
      for i, match in enumerate(matches):
        embedd = create_match_embedded(match, f"Match")
        if i == 0:
          msg = await ctx.respond(embed=embedd, view=MatchView(bot, match))
        else:
          msg = await ctx.interaction.followup.send(embed=embedd, view=MatchView(bot, match))
        await match.message_ids.append(msg)
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
      
    m_embedd = create_match_embedded(match, "Placeholder")

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

      embedd = create_bet_embedded(bet, "Placeholder")
      msg_ids.append((bet.message_ids, embedd, bet))
      users.append(user.code)

    no_same_list_user = []
    [no_same_list_user.append(x) for x in users if x not in no_same_list_user]
    for user in no_same_list_user:
      embedd = create_user_embedded(user, session)
      await ctx.respond(embed=embedd)

  tasks = []
  tasks.append(edit_all_messages(bot, match.message_ids, m_embedd, view=MatchView(bot, match)))
  [tasks.append(edit_all_messages(bot, tup[0], tup[1], view=BetView(bot, tup[2]))) for tup in msg_ids]
  await asyncio.gather(*tasks)
#match reset end


#match send_warning start
@matchscg.command(name = "send_warning", description = "Send warning to users who have not bet on a match.")
async def match_send_warning(ctx, match: Option(str, "Match you want to send warning of.", autocomplete=match_list_autocomplete)):
  with Session.begin() as session:
    if (nmatch := await obj_from_autocomplete_tuple(None, get_open_matches(session), match, "Match", session)) is None:
      if (nmatch := await obj_from_autocomplete_tuple(ctx, get_all_db("Match", session), match, "Match", session)) is None: 
        await ctx.respond(f'Match "{match}" not found.', ephemeral = True)
        return
    match = nmatch
    
    await match.send_warning(bot, session)


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
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return
    user.hidden = not user.hidden
    print(user.hidden)

#alert start
alertscg = SlashCommandGroup(
  name = "alert",
  description = "Get alerts for things.",
  guild_ids = gid,
)

async def do_tournament_alert(ctx, tournament):
  with Session.begin() as session:
    if (user := await get_user_from_ctx(ctx, ctx.author, session)) is None: return
    if (ntournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), tournament, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{tournament}" not found.', ephemeral = True)
      return
    tournament = ntournament
    has_alert = await user.toggle_alert(tournament, ctx.guild)
    
    if has_alert:
      await ctx.respond(f"You are added to alerts for {tournament.name}.", ephemeral = True)
    else:
      await ctx.respond(f"You are removed from alerts for {tournament.name}.", ephemeral = True)

#alert tournament start
@alertscg.command(name = "tournament", description = "Toggle alert when a match in tournament is about to close.")
async def alert_tournament(ctx, tournament: Option(str, "Tournament you want to toggle alerts for.", autocomplete = tournament_autocomplete)):
  await do_tournament_alert(ctx, tournament)

bot.add_application_command(alertscg)
#alert end

#tournament start 
tournamentsgc = SlashCommandGroup(
  name = "tournament", 
  description = "Start, color, and rename tournaments.",
  guild_ids = gid,
)

#tournament alert start
@tournamentsgc.command(name = "alert", description = "Get alert when a match in tournament is about to close.")
async def tournament_alert(ctx, tournament: Option(str, "Tournament you want to get alerts for.", autocomplete = tournament_autocomplete)):
  await do_tournament_alert(ctx, tournament)
#tournament alert end

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

#tournament delete start
@tournamentsgc.command(name = "delete", description = "Deletes a tournament.")
async def tournament_delete(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    if (tournament.matches != []):
      await ctx.respond(f'Tournament "{tournament.name}" has matches, you cannot delete it.', ephemeral = True)
      return
    await tournament.deactivate(ctx.guild)
    await delete_from_db(tournament, session=session)
    await ctx.respond(f'Tournament "{tournament.name}" deleted.')

#tournament matches start
@tournamentsgc.command(name = "matches", description = "What matches.")
async def tournament_matches(ctx, tournament: Option(str, "Tournament you want matches of.", autocomplete=tournament_autocomplete), type: Option(int, "If type is full it sends the whole embed of each match.", choices = list_choices, default = 0, required = False)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), tournament, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{tournament}" not found.', ephemeral = True)
      return
    matches = tournament.matches
    if len(matches) == 0:
      await ctx.respond("No matches in tournament.", ephemeral=True)
      return
    
    if type == 0:
      #short
      await send_match_list_embedded(f"Matches in {tournament.name}", matches, bot, ctx)
    elif type == 1:
      #full
      for i, match in enumerate(matches):
        embedd = create_match_embedded(match, f"Match")
        if i == 0:
          msg = await ctx.respond(embed=embedd, view=MatchView(bot, match))
        else:
          msg = await ctx.interaction.followup.send(embed=embedd, view=MatchView(bot, match))
        await match.message_ids.append(msg)
#tournament matches end

#tournament recolor start
@tournamentsgc.command(name = "recolor", description = "Changes the color of a tournament.")
async def tournament_recolor(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete),
                           xkcd_color_name: Option(str, "Name of color you want to add.", autocomplete=xkcd_picker_autocomplete, required=False),
                           color_name:Option(str, "Name of color you want to add.", autocomplete=color_picker_autocomplete, required=False), 
                           hex: Option(str, "Hex color code of new color. The 6 numbers/letters.", required=False)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
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
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
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
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    embedd = create_tournament_embedded(f"Found Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament find end

#tournament activate start
@tournamentsgc.command(name = "activate", description = "Activates a tournament.")
async def tournament_activate(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_inactive_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_inactive_tournaments(session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    if tournament.active:
      await ctx.respond("Tournament already active.", ephemeral = True)
      return
    await tournament.activate(ctx.guild)
    embedd = create_tournament_embedded(f"Activated Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament activate end

#tournament deactivate start
@tournamentsgc.command(name = "deactivate", description = "Deactivates a tournament.")
async def tournament_deactivate(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_active_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_active_tournaments(session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    if not tournament.active:
      await ctx.respond("Tournament already inactive.", ephemeral = True)
      return
    await tournament.deactivate(ctx.guild)
    embedd = create_tournament_embedded(f"Deactivated Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament deactivate end

#tournament link start
@tournamentsgc.command(name = "link", description = "Links a tournament to a vlr code.")
async def tournament_link(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete),
                          vlr_link: Option(str, "VLR link of tournament.")):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found. To start a tournament do /tournament start.', ephemeral = True)
      return
    code = get_code(vlr_link)
    if code is None:
      await ctx.respond("Not a valid team link.", ephemeral = True)
      return
    tournament.vlr_code = code
    embedd = create_tournament_embedded(f"Linked Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)
#tournament link end

#tournament create_role start
@tournamentsgc.command(name = "create_role", description = "Creates a role for a tournament.")
async def tournament_create_role(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    await tournament.create_role(ctx.guild)
    embedd = create_tournament_embedded(f"Created Role for Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)

bot.add_application_command(tournamentsgc)
#tournament create_role end

#tournament delete_role start
@tournamentsgc.command(name = "delete_role", description = "Deletes a role for a tournament.")
async def tournament_delete_role(ctx, name: Option(str, "Name of tournament.", autocomplete=tournament_autocomplete)):
  with Session.begin() as session:
    if (tournament := await obj_from_autocomplete_tuple(ctx, get_all_db("Tournament", session), name, "Tournament", session)) is None:
      await ctx.respond(f'Tournament "{name}" not found.', ephemeral = True)
      return
    await tournament.delete_role(ctx.guild)
    embedd = create_tournament_embedded(f"Deleted Role for Tournament: {tournament.name}", tournament)
    await ctx.respond(embed=embedd)

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
  print(f"check order done by {ctx.author.name} ")
  

#clean db start
@bot.slash_command(name = "clean_db", description = "Do not user command if not Pig, Debugs some stuff.")
async def clean_db(ctx):
  await ctx.respond(f"cleaning db.")
  with Session.begin() as session:
    bets = get_all_db("Bet", session)
    for bet in bets:
      match = bet.match
      bet.t1 = match.t1
      bet.t2 = match.t2
  print(f"clean db done by {ctx.author.name} ")

token = get_setting("discord_token")
#print(f"discord: {token}")
bot.run(token)
