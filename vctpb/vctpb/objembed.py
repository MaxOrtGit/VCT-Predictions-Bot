import discord
from dbinterface import get_condition_db
from Bet import Bet
from Match import Match
from User import User, get_active_users
from convert import id_to_mention
from utils import hex_to_tuple
import math
import emoji
from sqlaobjs import Session


async def send_msg(sender, followup=False, **kwargs):
  if isinstance(sender, discord.TextChannel):
    kwargs.pop("ephemeral", None)
    await sender.send(**kwargs)
  elif isinstance(sender, discord.commands.context.ApplicationContext):
    await sender.respond(**kwargs)
  elif isinstance(sender, discord.Interaction):
    if not followup:
      await sender.response.send_message(**kwargs)
    else:
      await sender.followup.send(**kwargs)
  else:
    print("Error: sender is not a valid type", type(sender))

def get_match_title(match:Match):
  return f"{match.t1} vs {match.t2}, Odds: {match.t1o} / {match.t2o}"

def create_match_embedded(match:Match, title):
  title = f"{title}: {get_match_title(match)}"
  embed = discord.Embed(title=title, color=discord.Color.from_rgb(*hex_to_tuple(match.color_hex)))
  embed.add_field(name="Teams:", value=f"{match.t1} vs {match.t2}", inline=True)
  embed.add_field(name="Odds:", value=str(match.t1o) + " / " + str(match.t2o), inline=True)
  embed.add_field(name="Tournament Name:", value=str(match.tournament_name), inline=True)
  embed.add_field(name="Odds Source:", value=str(match.odds_source), inline=True)
  embed.add_field(name="Creator:", value=id_to_mention(match.creator_id), inline=True)
  bet_codes = [bet.code for bet in match.bets]
  bet_str = str(", ".join(bet_codes))
  if bet_str == "":
    bet_str = "None"
  #embed.add_field(name="Bet IDs:", value=bet_str, inline=True)
  #date_formatted = match.date_created.strftime("%m/%d/%Y at %H:%M:%S")
  #embed.add_field(name="Created On:", value=date_formatted, inline=True)
  if match.date_closed is None:
    embed.add_field(name="Betting Open:", value="Yes", inline=True)
  else:
    embed.add_field(name="Betting Open:", value="No", inline=True)

  if match.winner == 0:
    #embed.add_field(name="Winner:", value="None", inline=True)
    pass
  else:
    winner_team = ""
    if match.winner == 1:
      winner_team = match.t1
    else:
      winner_team = match.t2

    embed.add_field(name="Winner:", value=str(winner_team), inline=True)
    
  embed.add_field(name="ID:", value=str(match.code), inline=True)
  return embed

limit = 20
async def send_match_list_embedded(embed_title, matches, bot, sender, followup=False, ephemeral=False, view:int | discord.ui.View=-1, hex=None, content=None):
  from views import MatchListView
  follow = followup
  if len(matches) > limit:
    while len(matches) > 0:
      await send_match_list_embedded(embed_title, matches[:limit], bot, sender, followup=follow, ephemeral=ephemeral)
      follow = True
      matches = matches[limit:]
    return
  if hex is None:
    color = discord.Color.red()
  else:
    color = discord.Color.from_rgb(*hex_to_tuple(hex))
  embed = discord.Embed(title=embed_title, color=color)
  for match in matches:
    embed.add_field(name=f"{match.t1} vs {match.t2}, Odds: {match.t1o} / {match.t2o}, ID: {match.code}", value="", inline=False)
  
  args = {"embed": embed, "ephemeral": ephemeral}
  if view != -1:
    args["view"] = view
  else:
    args["view"] = MatchListView(bot, matches)
  if content is not None:
    args["content"] = content
  await send_msg(sender, follow, **args)
    
async def send_bet_list_embedded(embed_title, bets, bot, sender, followup=False, ephemeral=False, user=None):
  def create_bet_list_embedded(embed_title, match_bets, show_hidden):
    if match_bets is None:
      return None

    embed = discord.Embed(title=embed_title, color=discord.Color.blue())

    for match in match_bets:
      bets = match_bets[match]
      name = f"{match.t1} vs {match.t2}, Odds: {match.t1o} / {match.t2o}"
      bet_text = ""
      for bet in bets:
        if bet.hidden and (show_hidden == False):
          bet_text += f"{bet.user.username}'s Hidden Bet\n"
        else:
          team = bet.get_team()
          pref = ""
          if bet.hidden:
            pref = " Hidden"
          pref = f"{bet.user.username}'s" + pref
          bet_text += f"{pref} Bet Team: {team}, Amount: {bet.amount_bet}, Payout on Win: {int(math.floor(bet.get_payout()))}\n"
      embed.add_field(name=name, value=bet_text, inline=False)
    return embed
  async def send_visible_hidden_bet_list_embedded(show_hidden, embed_title, match_bets, bot, sender, followup=False, ephemeral=False):
    from views import BetListView
    follow = followup
    if len(match_bets) > limit:
      while len(match_bets) > 0:
        await send_bet_list_embedded(embed_title, match_bets[:limit], bot, sender, followup=follow, ephemeral=ephemeral)
        follow = True
        match_bets = match_bets[limit:]
      return  
      
    if len(match_bets) == 0:
      args = {"content": "No undecided bets.", "ephemeral": True}
    else:
      embed = create_bet_list_embedded("Bets:", match_bets, show_hidden)
      args = {"embed": embed, "view": BetListView(bot), "ephemeral": ephemeral}
    
    await send_msg(sender, follow, **args)
  
  bets.sort(key=lambda x: x.user.balances[-1][1], reverse=True)
  bets.sort(key=lambda x: x.hidden)
  bets.sort(key=lambda x: x.match.date_created)
  matches = []
  matches = [bet.match for bet in bets if bet.match not in matches]
  match_bets = { matches: [] for matches in matches }
  [match_bets[bet.match].append(bet) for bet in bets]
  hidden_match_bets = { matches: [] for matches in matches}
  if user is not None:
    for match in match_bets:
      for bet in match_bets[match]:
        if bet.hidden and user.code == bet.user_id:
          hidden_match_bets[match].append(bet)
  
  new_hidden_match_bets = hidden_match_bets.copy()
  for match in hidden_match_bets:
    if len(hidden_match_bets[match]) == 0:
      new_hidden_match_bets.pop(match)
      
  hidden_match_bets = new_hidden_match_bets
  
  await send_visible_hidden_bet_list_embedded(False, embed_title, match_bets, bot, sender, followup=followup, ephemeral=ephemeral)
  if len(hidden_match_bets) > 0:
    await send_visible_hidden_bet_list_embedded(True, embed_title, hidden_match_bets, bot, sender, followup=True, ephemeral=True)


async def old_send_bet_list_embedded(embed_title, bets, bot, sender, followup=False, ephemeral=False, user=None):
  def create_bet_list_embedded(embed_title, match_bets, show_hidden):
    if match_bets is None:
      return None

    embed = discord.Embed(title=embed_title, color=discord.Color.blue())

    last_match_id = None
    for match, bet in match_bets:
      name = ""
      if match.code != last_match_id:
        name = f"{match.t1} vs {match.t2}, Odds: {match.t1o} / {match.t2o}"
        last_match_id = match.code
      if bet.hidden and (show_hidden == False):
        embed.add_field(name=name, value=f"{bet.user.username}'s Hidden Bet", inline=False)
      else:
        team = bet.get_team()
        pref = ""
        if bet.hidden:
          pref = "Hidden"
        pref = f"{bet.user.username}'s " + pref
        embed.add_field(name=name, value=f"{pref} Bet Team: {team}, Amount: {bet.amount_bet}, Payout on Win: {int(math.floor(bet.get_payout()))}", inline=False)
    return embed
  async def send_visible_hidden_bet_list_embedded(show_hidden, embed_title, match_bets, bot, sender, followup=False, ephemeral=False):
    from views import BetListView
    print(match_bets)
    follow = followup
    if len(match_bets) > limit:
      while len(match_bets) > 0:
        await send_bet_list_embedded(embed_title, match_bets[:limit], bot, sender, followup=follow, ephemeral=ephemeral)
        follow = True
        match_bets = match_bets[limit:]
      return  
      
    if len(match_bets) == 0:
      args = {"content": "No undecided bets.", "ephemeral": True}
    else:
      embed = create_bet_list_embedded("Bets:", match_bets, show_hidden)
      args = {"embed": embed, "view": BetListView(bot), "ephemeral": ephemeral}
    
    await send_msg(sender, follow, **args)
  
  bets.sort(key=lambda x: x.user.balances[-1][1], reverse=True)
  bets.sort(key=lambda x: x.hidden)
  bets.sort(key=lambda x: x.match.date_created)
  
  match_bets = [(bet.match, bet) for bet in bets]
  
  hidden_match_bets = []
  if user is not None:
    for match_bet in match_bets:
      if match_bet[1].hidden and user.code == match_bet[1].user_id:
        hidden_match_bets.append(match_bet)
  
  await send_visible_hidden_bet_list_embedded(False, embed_title, match_bets, bot, sender, followup=followup, ephemeral=ephemeral)
  if len(hidden_match_bets) > 0:
    await send_visible_hidden_bet_list_embedded(True, embed_title, hidden_match_bets, bot, sender, followup=True, ephemeral=True)


def create_bet_hidden_embedded(bet, title):
  title = f"{title}: {bet.user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}."
  embed = discord.Embed(title=title, color=discord.Color.from_rgb(*hex_to_tuple(bet.color_hex)))
  #when teams done this has to be diff color
  embed.add_field(name="User:", value=id_to_mention(bet.user_id), inline=True)
  embed.add_field(name="Teams:", value=bet.t1 + " vs " + bet.t2, inline=True)

  if int(bet.winner) == 0:
    #embed.add_field(name="Winner:", value="None", inline=True)
    pass
  else:
    winner_team = ""
    if int(bet.winner) == 1:
      winner_team = bet.t1
    else:
      winner_team = bet.t2

    embed.add_field(name="Winner:", value=winner_team, inline=True)

  #date_formatted = bet.date_created.strftime("%m/%d/%Y at %H:%M:%S")
  #embed.add_field(name="Created On:", value=date_formatted, inline=True)
  #embed.add_field(name="Match ID:", value=bet.match_id, inline=True)
  embed.add_field(name="ID:", value=str(bet.code), inline=True)
  return embed


def create_bet_embedded(bet: Bet, title):
  title = f"{title}: {bet.user.username}, {bet.amount_bet} on {bet.get_team()}."
  embed = discord.Embed(title=title, color=discord.Color.from_rgb(*hex_to_tuple(bet.color_hex)))
  embed.add_field(name="User:", value=id_to_mention(bet.user_id), inline=True)
  embed.add_field(name="Amount Bet:", value=str(bet.amount_bet), inline=True)
  (team, payout) = bet.get_team_and_payout()

  embed.add_field(name="Bet on:", value=team, inline=True)
  embed.add_field(name="Payout On Win:", value=str(math.floor(payout)), inline=True)

  if bet.winner == 0:
    #embed.add_field(name="Winner:", value="None", inline=True)
    pass
  else:
    winner_team = ""
    if bet.winner == 1:
      winner_team = bet.t1
    else:
      winner_team = bet.t2

    embed.add_field(name="Winner:", value=str(winner_team), inline=True)

  #date_formatted = bet.date_created.strftime("%m/%d/%Y at %H:%M:%S")
  #embed.add_field(name="Created On:", value=date_formatted, inline=True)
  #embed.add_field(name="Match ID:", value=bet.match_id, inline=True)
  #embed.add_field(name="Visiblity:", value=("Hidden" if bet.hidden else "Shown"), inline=True)
  embed.add_field(name="ID:", value=str(bet.code), inline=True)
  return embed



def create_user_embedded(user:User, session=None):
  embed = discord.Embed(title=f"{user.username}'s balance:", color=discord.Color.from_rgb(*hex_to_tuple(user.color_hex)))
  embed.add_field(name="Name:", value=id_to_mention(user.code), inline=False)
  embed.add_field(name="Account balance:", value=math.floor(user.balances[-1][1]), inline=True)
  embed.add_field(name="Balance Available:", value=math.floor(user.get_visible_balance(session)), inline=True)
  embed.add_field(name="Loan balance:", value=math.floor(user.loan_bal()), inline=True)
  return embed


def create_leaderboard_embedded(session=None):
  if session is None:
    with Session.begin() as session:
      create_leaderboard_embedded(session)
  users = get_condition_db("User", User.hidden == False, session)
  users = get_active_users(users, session)
  user_rankings = [(user, user.balances[-1][1]) for user in users]
  user_rankings.sort(key=lambda x: x[1], reverse=True)
  embed = discord.Embed(title="Leaderboard:", color=discord.Color.gold())
  medals = [emoji.demojize("🥇"), emoji.demojize("🥈"), emoji.demojize("🥉")]
  rank_num = 1
  for user_rank in user_rankings:
    rank = ""
    if rank_num > len(medals):
      rank = "#" + str(rank_num)
      name = user_rank[0].username
      embed.add_field(name=rank + f": {name}", value=str(math.floor(user_rank[1])), inline=False)
    else:
      rank = emoji.emojize(medals[rank_num - 1])
      name = user_rank[0].username
      embed.add_field(name=rank + f":  {name}", value=str(math.floor(user_rank[1])), inline=False)
    rank_num += 1
  return embed

# TODO: remove later
def create_payout_list_embedded(embed_title, match, bet_user_payouts):
  embed = discord.Embed(title=embed_title, color=discord.Color.from_rgb(*hex_to_tuple(match.color_hex)))
  for bet, user, payout in bet_user_payouts:
    if payout > 0:
      value = f"Won {math.floor(payout)}. Current balance: {math.floor(user.balances[-1][1])}"
    else:
      value = f"Lost {math.floor(payout)}. Current balance: {math.floor(user.balances[-1][1])}"
    embed.add_field(name=f"{user.username} bet {bet.amount_bet} on {bet.get_team()}", value=value, inline=False)

  return embed


def create_award_label_list_embedded(user, award_labels):
  embed = discord.Embed(title=f"{user.username}'s Awards:", color=discord.Color.from_rgb(*hex_to_tuple(user.color_hex)))
  award_labels.reverse()
  award_labels = award_labels[:25]
  for award_label in award_labels:
        
    award_t = award_label.split(", ")

    name = ", ".join(award_t[:-2])

    embed.add_field(name=name, value=f"Balance changed by {award_t[-2]}, {award_t[-1]}", inline=False)
  return embed

def create_tournament_embedded(embed_title, tournament):
  embed = discord.Embed(title=embed_title, color=discord.Color.from_rgb(*hex_to_tuple(tournament.color_hex)))
  embed.add_field(name="Name:", value=tournament.name, inline=True)
  active_str = "No"
  if tournament.active:
    active_str = "Yes"
  embed.add_field(name="Active:", value=active_str, inline=True)
  embed.add_field(name="VLR Code:", value=tournament.vlr_code, inline=True)
  return embed

def create_team_embedded(embed_title, team):
  embed = discord.Embed(title=embed_title, color=discord.Color.from_rgb(*hex_to_tuple(team.color_hex)))
  embed.add_field(name="Name:", value=team.name, inline=True)
  embed.add_field(name="VLR Code:", value=team.vlr_code, inline=True)
  return embed
