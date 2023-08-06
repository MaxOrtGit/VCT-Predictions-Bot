from datetime import datetime
from discord.ui import InputText, Modal
from vlrinterface import get_odds_from_match_page, get_tournament_name_and_code_from_match_page, get_teams_from_match_page, get_or_create_team, get_or_create_tournament
import discord
from sqlaobjs import Session
from utils import *
from dbinterface import get_unique_code, add_to_db, get_channel_from_db, get_from_db
from Match import Match
from Bet import Bet
from User import User
from views import MatchView, BetView
from objembed import create_match_embedded, create_bet_embedded, create_bet_hidden_embedded
from convert import edit_all_messages

def get_from_field(embed, field_name):
  for field in embed.fields:
    if field.name == field_name:
      return field.value
  return None

#match create modal start
class MatchCreateModal(Modal):
  def __init__(self, session, balance_odds=1, soup=None, vlr_code=None, bot=None, *args, data_embed=None, **kwargs) -> None:
    #time function
    time = datetime.now()
    
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
    self.bot = bot
    team1 = None
    team2 = None
    if data_embed is not None:
      team1 = get_from_field(data_embed, "Team 1")
      team1 = get_from_db("Team", team1, session)
      team2 = get_from_field(data_embed, "Team 2")
      team2 = get_from_db("Team", team2, session)
      
      t1oo = get_from_field(data_embed, "Team 1 Odds")
      t2oo = get_from_field(data_embed, "Team 2 Odds")
      vlr_code = get_from_field(data_embed, "Match Code")
      tournament_name = get_from_field(data_embed, "Tournament")
      tournament_code = get_from_field(data_embed, "Tournament Code")
    elif (vlr_code is not None) and (soup is not None):
      time2 = datetime.now()
      t1oo, t2oo = get_odds_from_match_page(soup)
      print("time 2.1", datetime.now() - time2)
      time2 = datetime.now()
      team1, team2 = get_teams_from_match_page(soup, session, second_query=False)
      print("time 2.2", datetime.now() - time2)
      time2 = datetime.now()
      tournament_name, tournament_code = get_tournament_name_and_code_from_match_page(soup)
      print("time 2.3", datetime.now() - time2)
      
    print("time 2.5", datetime.now() - time)
    if t1oo is not None:
      odds_source = "VLR.gg"
    
    if team1 is not None and team2 is not None:
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
      wait_msg = await interaction.response.send_message(f"Generating Match.", ephemeral=True)
      if (self.children[0].value is None) or (self.children[1].value is None) or (self.children[2].value is None) or (self.children[3].value is None) or (self.children[4].value is None):
        await wait_msg.edit_original_response(content="Error in match creation, report bug.")
        return
        
      team_one = self.children[0].value.strip()
      team_two = self.children[1].value.strip()
      
      t1_code, t2_code = None, None
      if self.team1_name == team_one:
        t1_code = self.team1_vlr_code
      if self.team2_name == team_two:
        t2_code = self.team2_vlr_code
        
      if (t1_code is None) or (t2_code is None):
        self.vlr_code = None
        
      team1 = get_or_create_team(team_one, t1_code, session)
      team2 = get_or_create_team(team_two, t2_code, session)
      
      odds_combined = self.children[2].value.strip()
      tournament_name = self.children[3].value.strip()
      tournament_code = None
      if self.tournament_name == tournament_name:
        tournament_code = self.tournament_code
      tournament = await get_or_create_tournament(tournament_name, tournament_code, interaction.guild, session, activate_on_create=False)
      betting_site = self.children[4].value.strip()
      
      
      if odds_combined.count(" ") > 1:
        odds_combined.strip(" ")
        
      splits = [" ", "/", "\\", ";", ":", ",", "-", "_", "|"]
      for spliter in splits:
        if odds_combined.count(spliter) == 1:
          team_one_old_odds, team_two_old_odds = "".join(_ for _ in odds_combined if _ in f".1234567890{spliter}").split(spliter)
          break
      else:
        await wait_msg.edit_original_response(content = f"Odds are not valid. Odds must be [odds 1]/[odds 2].")
        return
      
      if (to_float(team_one_old_odds) is None) or (to_float(team_two_old_odds) is None): 
        await wait_msg.edit_original_response(content = f"Odds are not valid. Odds must be [odds 1]/[odds 2].")
        return
      
      team_one_old_odds = to_float(team_one_old_odds)
      team_two_old_odds = to_float(team_two_old_odds)
      
      if team_one_old_odds <= 1 or team_two_old_odds <= 1:
        await wait_msg.edit_original_response(content = f"Odds must be greater than 1.")
        return
      
      if self.balance_odds == 1:
        team_one_odds, team_two_odds = balance_odds(team_one_old_odds, team_two_old_odds)
      else:
        team_one_odds = team_one_old_odds
        team_two_odds = team_two_old_odds
        
      code = get_unique_code("Match", session)
    
      color = mix_colors([(team1.color_hex, 3), (team2.color_hex, 3), (tournament.color_hex, 1)])
      match = Match(code, team_one, team_two, team_one_odds, team_two_odds, team_one_old_odds, team_two_old_odds, tournament_name, betting_site, color, interaction.user.id, get_date(), self.vlr_code)
      
      
      embedd = create_match_embedded(match, f"New Match")
      
      channel = await self.bot.fetch_channel(get_channel_from_db("match", session))
      msg = await channel.send(embed=embedd, view=MatchView(self.bot, match))
      await wait_msg.edit_original_response(content = f"Match created in {channel.mention}.")
      
      await match.message_ids.append(msg)
      add_to_db(match, session)
#match create modal end

#match edit modal start
class MatchEditModal(Modal):
  def __init__(self, match, locked, balance_odds=1, bot=None, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    
    self.match = match
    self.balance_odds = balance_odds
    self.locked = locked
    self.bot = bot
    
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
      
      
      if not odds_locked or odds_combined == "":
        splits = [" ", "/", "\\", ";", ":", ",", "-", "_", "|"]
        for spliter in splits:
          if odds_combined.count(spliter) == 1:
            team_one_old_odds, team_two_old_odds = "".join(_ for _ in odds_combined if _ in f".1234567890{spliter}").split(spliter)
            break
        else:
          await interaction.response.send_message(f"Odds are not valid. Odds must be [odds 1]/[odds 2].", ephemeral=True)
          return
          
        if ((team_one_old_odds := to_float(team_one_old_odds)) is None) or ((team_two_old_odds := to_float(team_two_old_odds) ) is None): 
          await interaction.response.send_message(f"Odds are not valid. Odds must be valid decimal numbers.", ephemeral=True)
          return
        
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
      
      embedd = create_match_embedded(match, "Edited Match")
      
      inter = await interaction.response.send_message(embed=embedd, view=MatchView(self.bot, match))
      ids = match.message_ids
      await match.message_ids.append(inter)
    await edit_all_messages(self.bot, ids, embedd, view=MatchView(self.bot, match))
#match edit modal end


#bet create modal start
class BetCreateModal(Modal):
  
  def __init__(self, match: Match, user: User, hidden, session, error=[None, None], bot=None, team=-1, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.match = match
    self.user = user
    if hidden == -1:
      hidden = 0
    self.hidden = hidden
    self.bot = bot
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
      
    if team == 1:
      team = str(match.t1)
    elif team == 2:
      team = str(match.t2)
    else:
      team = ""
      
    self.add_item(InputText(label=team_label, value=team, placeholder=f'"1" for {match.t1} and "2" for {match.t2}', min_length=1, max_length=100))

    if error[1] is None: 
      amount_label = "Amount you want to bet."
    else:
      amount_label = error[1]
    self.add_item(InputText(label=amount_label, placeholder=f"Your available balance is {math.floor(user.get_balance(session))}", min_length=1, max_length=20))
    
    # is hidden
    if hidden:
      hidden_default = "Yes"
    else:
      hidden_default = "No"
    self.add_item(InputText(label="Hide bet from others", value=hidden_default, placeholder="Yes/No or Y/N", min_length=1, max_length=5, required=False))


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
      
      hidden_string = self.children[2].value.lower()
      if hidden_string == "yes" or hidden_string == "y":
        self.hidden = True
      elif hidden_string == "no" or hidden_string == "n":
        self.hidden = False
      
      bet = Bet(code, match.t1, match.t2, match.tournament_name, int(amount), int(team_num), match.code, user.code, get_date(), self.hidden)
      add_to_db(bet, session)
      
      session.flush([bet])
      session.expire(bet)
      
      if bet.hidden:  
        shown_embedd = create_bet_hidden_embedded(bet, f"New Bet")
      else:
        shown_embedd = create_bet_embedded(bet, f"New Bet")
        
      if (channel := await self.bot.fetch_channel(get_channel_from_db("bet", session))) == interaction.channel:
        msg = await interaction.response.send_message(embed=shown_embedd, view=BetView(self.bot, bet))
      else:
        await interaction.response.send_message(f"Bet created in {channel.mention}.", ephemeral=True)
        msg = await channel.send(embed=shown_embedd, view=BetView(self.bot, bet))
        
      if self.hidden:
        embedd = create_bet_embedded(bet, f"Hidden Bet")
        inter = await interaction.followup.send(embed = embedd, ephemeral = True, view=BetView(self.bot, bet))
      await bet.message_ids.append(msg)
#bet create modal end


#bet edit modal start
class BetEditModal(Modal):
  
  def __init__(self, hide, match: Match, user: User, bet: Bet, session, bot, team=-1, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.match = match
    self.user = user
    self.bet = bet
    if hide == -1:
      hide = bet.hidden
    self.hide = hide
    self.bot = bot
    
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
    
    if team == 1:
      team = str(bet.t1)
    elif team == 2:
      team = str(bet.t2) 
    else:
      team = ""
    
    self.add_item(InputText(label=team_label, value=team, placeholder=bet.get_team(), min_length=1, max_length=100, required=False))

    amount_label = f"Amount to bet. Balance: {math.floor(user.get_balance(session) + bet.amount_bet)}"
    self.add_item(InputText(label=amount_label, placeholder = bet.amount_bet, min_length=1, max_length=20, required=False))
    
    
    if hide == 1:
      hidden_default = "Yes"
    elif hide == 0:
      hidden_default = "No"
    else:
      hidden_default = ""
      
    if hide != -1:
      hide_placeholder = "Yes/No or Y/N"
    else:
      if bet.hidden == 1:
        hide_placeholder = "Yes"
      elif bet.hidden == 0:
        hide_placeholder = "No"
    self.add_item(InputText(label="Hide bet from others", value=hidden_default, placeholder=hide_placeholder, min_length=1, max_length=5, required=False))

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
      
      hidden_string = self.children[2].value.lower()
      if hidden_string == "yes" or hidden_string == "y":
        self.hide = 1
      elif hidden_string == "no" or hidden_string == "n":
        self.hide = 0
      else:
        self.hide = bet.hidden
      bet.hidden = self.hide
      
      embedd = None
      if not bet.hidden:
        title = f"Edit Bet"
        embedd = create_bet_embedded(bet, title)
        msg = await interaction.response.send_message(embed=embedd, view=BetView(self.bot, bet))
        await bet.message_ids.append(msg)
        
      if self.hide:
        embeddd = create_bet_embedded(bet, f"Hidden Bet")
        inter = await interaction.response.send_message(embed = embeddd, ephemeral = True, view=BetView(self.bot, bet))
    if not bet.hidden:
      await edit_all_messages(self.bot, bet.message_ids, embedd, view=BetView(self.bot, bet))
#bet edit modal end