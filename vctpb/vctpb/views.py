import discord
from discord.ui import View, Button
from dbinterface import get_from_db, delete_from_db
from convert import get_current_matches, get_current_bets
from sqlaobjs import Session
from functools import partial
from objembed import send_match_list_embedded, send_bet_list_embedded, create_match_embedded, create_bet_embedded, create_bet_hidden_embedded

async def show_matches(interaction, session, bot):
  await send_match_list_embedded(f"Matches", get_current_matches(session), bot, interaction, ephemeral=True)
  
async def show_bets(user, interaction, session, bot):
  await send_bet_list_embedded(f"Bets", get_current_bets(session), bot, interaction, user=user, ephemeral=True)

async def show_match_bets(match, user, interaction, bot):
  if match is None: return
  await send_bet_list_embedded("Bets", match.bets, bot, interaction, user=user, ephemeral=True)
    
async def show_match(match, interaction, session, bot):
  if (embedd := create_match_embedded(match, f"Match: {match.t1} vs {match.t2}, {match.t1o} / {match.t2o}.", session)) is not None:
    await interaction.response.send_message(embed=embedd, ephemeral=True, view=MatchView(bot, match))
  else:
    await interaction.response.send_message("Match not found. Report the bug.", ephemeral=True)

async def create_edit_bet(interaction, hide, team, match, session, bot):
    from modals import BetEditModal, BetCreateModal
    user = get_from_db("User", interaction.user.id, session)
    if match.date_closed is None:
      if (bet := match.user_bet(interaction.user.id)) != None:
        bet_modal = BetEditModal(int(hide), match, user, bet, session, bot, title="Edit Bet", team=team)
        await interaction.response.send_modal(bet_modal)
      else:
        bet_modal = BetCreateModal(match, user, int(hide), session, title="Create Bet", bot=bot, team=team)
        await interaction.response.send_modal(bet_modal)
    else:
      await interaction.response.send_message("Betting on this match has closed.", ephemeral=True)
      
class MatchView(View): 
  def __init__(self, bot, match):
    self.bot = bot
    super().__init__(timeout=None)
    if match is not None:
      if match.date_closed is not None:
        self.hide_buttons()
      else:
        self.set_buttons(match)
  
  def hide_buttons(self):
    self.remove_item(self.get_item("match_create_bet_t1")) # type: ignore
    self.remove_item(self.get_item("match_create_bet_t2")) # type: ignore
    self.remove_item(self.get_item("match_create_hidden_bet_t1")) # type: ignore
    self.remove_item(self.get_item("match_create_hidden_bet_t2")) # type: ignore
  
  def set_buttons(self, match):
    self.get_item("match_create_bet_t1").label = f"{match.t1} ({match.t1o})" # type: ignore
    self.get_item("match_create_bet_t2").label = f"{match.t2} ({match.t2o})" # type: ignore
    self.get_item("match_create_hidden_bet_t1").label = f"{match.t1} ({match.t1o})" # type: ignore
    self.get_item("match_create_hidden_bet_t2").label = f"{match.t2} ({match.t2o})" # type: ignore
    
    
  async def get_match(self, interaction, session):
    match = None
    fields = interaction.message.embeds[0].fields
    for field in fields[::-1]:
      if field.name == "ID:":
        match_id = field.value
        match = get_from_db("Match", match_id, session)
        break
    if match is None and interaction is not None:
      await interaction.response.send_message("Match not found. Report the bug.", ephemeral=True)
    return match
  
  @discord.ui.button(label='Create/Edit Bet', custom_id="match_create_bet_t1", style=discord.ButtonStyle.green, row=0)
  async def create_bet_t1_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await create_edit_bet(interaction, False, 1, match, session, self.bot)
      
  @discord.ui.button(label='Create/Edit Bet', custom_id="match_create_bet_t2", style=discord.ButtonStyle.green, row=0)
  async def create_bet_t2_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await create_edit_bet(interaction, False, 2, match, session, self.bot)
    
  @discord.ui.button(label='Create/Edit Hidden Bet', custom_id="match_create_hidden_bet_t1", style=discord.ButtonStyle.secondary, row=1)
  async def create_hidden_bet_t1_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await create_edit_bet(interaction, True, 1, match, session, self.bot)
  
  @discord.ui.button(label='Create/Edit Hidden Bet', custom_id="match_create_hidden_bet_t2", style=discord.ButtonStyle.secondary, row=1)
  async def create_hidden_bet_t2_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await create_edit_bet(interaction, True, 2, match, session, self.bot)
      
  # show all bets
  @discord.ui.button(label='Show Bets', custom_id="match_show_bets", style=discord.ButtonStyle.primary, row=2)
  async def show_bets_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      user = get_from_db("User", interaction.user.id, session)
      await show_match_bets(match, user, interaction, self.bot)
      
  @discord.ui.button(label='Show All Matches', custom_id="match_show_all_matches", style=discord.ButtonStyle.primary, row=3)
  async def show_all_matches_callback(self, button, interaction):
    with Session.begin() as session:
      await show_matches(interaction, session, self.bot)
      
  @discord.ui.button(label='Show All Bets', custom_id="match_show_all_bets", style=discord.ButtonStyle.primary, row=3)
  async def show_all_bets_callback(self, button, interaction):
    with Session.begin() as session:
      user = get_from_db("User", interaction.user.id, session)
      await show_bets(user, interaction, session, self.bot)
  
    
class BetView(View):
  async def get_bet(self, interaction, session):
    bet = None
    fields = interaction.message.embeds[0].fields
    for field in fields[::-1]:
      if field.name == "ID:":
        bet_id = field.value
        bet = get_from_db("Bet", bet_id, session)
        break
    if bet is None and interaction is not None:
      await interaction.response.send_message("Bet not found. Report the bug.", ephemeral=True)
    return bet
  
  async def get_match(self, interaction, session):
    if (bet := await self.get_bet(interaction, session)) is None: return None
    return bet.match
  
  def __init__(self, bot, bet):
    self.bot = bot
    super().__init__(timeout=None)
    if bet is not None:
      match = bet.match
      if match.date_closed is not None:
        self.remove_item(self.get_item("bet_cancel_bet")) # type: ignore
        self.remove_item(self.get_item("bet_edit_bet")) # type: ignore
  
  @discord.ui.button(label="Edit Bet", custom_id="bet_edit_bet", style=discord.ButtonStyle.green, row=0)
  async def edit_bet_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await create_edit_bet(interaction, -1, -1, match, session, self.bot)
  
  @discord.ui.button(label="Cancel Bet", custom_id="bet_cancel_bet", style=discord.ButtonStyle.danger, row=0)
  async def cancel_bet_callback(self, button, interaction):
    with Session.begin() as session:
      if (bet := await self.get_bet(interaction, session)) is None: return
      match = bet.match
      if (match is None) or (match.date_closed is not None):
        await interaction.response.send_message(content="Match betting has closed, you cannot cancel the bet.", ephemeral=True)
        return
        
      user = bet.user
      if bet.hidden == 0:
        embedd = create_bet_embedded(bet, f"Cancelled Bet: {user.username}, {bet.amount_bet} on {bet.get_team()}.")
      else:
        embedd = create_bet_hidden_embedded(bet, f"Cancelled Bet: {user.username}'s Hidden Bet on {bet.t1} vs {bet.t2}")
      await interaction.response.send_message(content="", embed=embedd)
      
      await delete_from_db(bet, self.bot, session=session)
  
  @discord.ui.button(label='Show Match', custom_id="bet_show_match", style=discord.ButtonStyle.primary, row=1)
  async def show_match_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      await show_match(match, interaction, session, self.bot)
      
  @discord.ui.button(label='Show Other Bets', custom_id="bet_show_bets", style=discord.ButtonStyle.primary, row=1)
  async def show_bets_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(interaction, session)) is None: return
      user = get_from_db("User", interaction.user.id, session)
      await show_match_bets(match, user, interaction, self.bot)
  
  @discord.ui.button(label='Show All Matches', custom_id="bet_show_all_matches", style=discord.ButtonStyle.primary, row=2)
  async def show_all_matches_callback(self, button, interaction):
    with Session.begin() as session:
      await show_matches(interaction, session, self.bot)
      
  @discord.ui.button(label='Show All Bets', custom_id="bet_show_all_bets", style=discord.ButtonStyle.primary, row=2)
  async def show_all_bets_callback(self, button, interaction):
    with Session.begin() as session:
      user = get_from_db("User", interaction.user.id, session)
      await show_bets(user, interaction, session, self.bot)
  
  
class MatchListView(View):
  async def get_match(self, button, interaction, session):
    match = None
    fields = interaction.message.embeds[0].fields
    view = self.from_message(interaction.message)
    label = view.get_item(button.custom_id).label # type: ignore
    for field in fields:
      if label in field.name:
        match_id = field.name.split("ID: ")[-1]
        match = get_from_db("Match", match_id, session)
        break
    if match is None and interaction is not None:
      await interaction.response.send_message("Match not found. Report the bug.", ephemeral=True)
    return match
  
  def __init__(self, bot, matches):
    self.bot = bot
    super().__init__(timeout=None)
    
    if matches is not None:
      i = 0
      for match in matches:
        button = Button(label=f"{match.t1} vs {match.t2}", custom_id=f"match_list_{i}", style=discord.ButtonStyle.primary)
        self.add_item(button)
        button.callback = partial(self.match_list_callback, button)
        i += 1
    else:
      for i in range(0, 20):
        button = Button(label=str(i), custom_id=f"match_list_{i}", style=discord.ButtonStyle.primary, disabled=True)
        self.add_item(button)
        button.callback = partial(self.match_list_callback, button)
  
  async def match_list_callback(self, button, interaction):
    with Session.begin() as session:
      if (match := await self.get_match(button, interaction, session)) is None: return
      await show_match(match, interaction, session, self.bot)

  @discord.ui.button(label='Show All Matches', custom_id="match_list_show_all_matches", style=discord.ButtonStyle.primary, row=4)
  async def show_all_matches_callback(self, button, interaction):
    with Session.begin() as session:
      await show_matches(interaction, session, self.bot)
      
  @discord.ui.button(label='Show All Bets', custom_id="match_list_show_all_bets", style=discord.ButtonStyle.primary, row=4)
  async def show_all_bets_callback(self, button, interaction):
    with Session.begin() as session:
      user = get_from_db("User", interaction.user.id, session)
      await show_bets(user, interaction, session, self.bot)
  
class BetListView(View): 
  def __init__(self, bot):
    self.bot = bot
    super().__init__(timeout=None)
    
  @discord.ui.button(label='Show All Matches', custom_id="bet_list_show_all_matches", style=discord.ButtonStyle.primary, row=4)
  async def show_all_matches_callback(self, button, interaction):
    with Session.begin() as session:
      await show_matches(interaction, session, self.bot)
  
  @discord.ui.button(label='Show All Bets', custom_id="bet_list_show_all_bets", style=discord.ButtonStyle.primary, row=4)
  async def show_all_bets_callback(self, button, interaction):
    with Session.begin() as session:
      user = get_from_db("User", interaction.user.id, session)
      await show_bets(user, interaction, session, self.bot)
  
    