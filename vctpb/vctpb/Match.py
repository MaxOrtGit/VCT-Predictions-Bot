from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from sqltypes import JSONList, DECIMAL, MsgMutableList
from sqlalchemy.ext.mutable import MutableList
from sqlaobjs import mapper_registry, Session
from utils import mix_colors, get_date, get_random_hex_color
from roleinterface import get_role
import asyncio

@mapper_registry.mapped
class Match():
  __tablename__ = "match"
  
  code = Column(String(8), primary_key = True, nullable=False)
  vlr_code = Column(Integer)
  t1 = Column(String(50), ForeignKey("team.name"), nullable=False)
  team1 = relationship("Team", foreign_keys=[t1], back_populates="matches_as_t1")
  t2 = Column(String(50), ForeignKey("team.name"), nullable=False)
  team2 = relationship("Team", foreign_keys=[t2], back_populates="matches_as_t2")
  t1o = Column(DECIMAL(5, 3), nullable=False)
  t2o = Column(DECIMAL(5, 3), nullable=False)
  t1oo = Column(DECIMAL(5, 3), nullable=False)
  t2oo = Column(DECIMAL(5, 3), nullable=False)
  tournament_name = Column(String(100), ForeignKey("tournament.name"), nullable=False)
  tournament = relationship("Tournament", back_populates="matches")
  
  creator = relationship("User", back_populates="matches")
  odds_source = Column(String(50), nullable=False)
  winner = Column(Integer, nullable=False)
  color_hex = Column(String(6), nullable=False)
  creator_id = Column(Integer, ForeignKey("user.code"))
  creator = relationship("User", back_populates="matches")
  date_created = Column(DateTime(timezone = True), nullable=False)
  date_winner = Column(DateTime(timezone = True))
  date_closed = Column(DateTime(timezone = True))
  bets = relationship("Bet", back_populates="match", cascade="all, delete")
  message_ids = Column(MsgMutableList.as_mutable(JSONList), nullable=False) #array of int
  alert = Column(Boolean, nullable=False, default=False)
  
  @property
  def has_bets(self):
    return bool(self.bets)
  
  def __init__(self, code, t1, t2, t1o, t2o, t1oo, t2oo, tournament_name, odds_source, color_hex, creator_id, date_created, vlr_code=None):
    self.full__init__(code, t1, t2, t1o, t2o, t1oo, t2oo, tournament_name, 0, odds_source, color_hex, creator_id, date_created, None, None, [], vlr_code)
  
  def full__init__(self, code, t1, t2, t1o, t2o, t1oo, t2oo, tournament_name, winner, odds_source, color_hex, creator_id, date_created, date_winner, date_closed, message_ids, vlr_code=None):
    self.code = code
    self.t1 = t1
    self.t2 = t2
    self.t1o = t1o
    self.t2o = t2o
    self.t1oo = t1oo
    self.t2oo = t2oo
    self.tournament_name = tournament_name
    self.winner = winner
    self.odds_source = odds_source
    self.color_hex = color_hex
    self.creator_id = creator_id
    self.date_created = date_created
    self.date_winner = date_winner
    self.date_closed = date_closed
    self.message_ids = message_ids
    self.vlr_code = vlr_code
  
  
  def __repr__(self):
    return f"<Match {self.code}>"
  
  def user_bet(self, user_id):
    for bet in self.bets:
      if bet.user_id == user_id:
        return bet
    return None
  
  async def send_warning(self, bot, session):
    from dbinterface import get_channel_from_db
    from views import MatchView
    from objembed import create_match_embedded, get_match_title
    from convert import id_to_mention
    self.alert = True
    if (match_channel := await bot.fetch_channel(get_channel_from_db("match", session))) is None:
      return
    
    users = self.tournament.alert_users
    embedd = create_match_embedded(self, f"Last chance for Match")
    pings = f"Last chance for Match: {get_match_title(self)}"
    #role = get_role(match_channel.guild, f"{self.tournament_name} Alert")
    #if role is not None:
    #  pings += f" {role.mention}"
    
    msg = await match_channel.send(content=pings, embed=embedd, view=MatchView(bot, self))
    await self.message_ids.append(msg)
    #await msg.edit(content="")
    
  
  def set_color(self, session=None):
    if session is None:
      with Session.begin() as session:
        return self.set_color(session)

    team1 = self.team1
    team2 = self.team2
    color = mix_colors([(team1.color_hex, 3), (team2.color_hex, 3), (self.tournament.color_hex, 1)])
    if color == self.color_hex:
      return
    self.color_hex = color
    
    for bet in self.bets:
      bet.set_color(session)
  
  def to_string(self):
    date_formatted = self.date_created.strftime("%d/%m/%Y at %H:%M:%S")
    return "Teams: " + str(self.t1) + " vs " + str(self.t2) + ", Odds: " + str(self.t1o) + " / " + str(self.t2o) +  ", Old Odds: " + str(self.t1oo) + " / " + str(self.t2oo) + ", Tournament Name: " + str(self.tournament_name) + ", Odds Source: " + str(self.odds_source) + ", Created On: " + str(date_formatted) + ", Date Closed: " + str(self.date_closed) + ", Winner: " + str(self.winner) + ", Identifyer: " + str(self.code) + ", Message IDs: " + str(self.message_ids)


  def short_to_string(self):
    return "Teams: " + str(self.t1) + " vs " + str(self.t2) + ", Odds: " + str(self.t1o) + " / " + str(self.t2o)

  def winner_name(self):
    if self.winner == 0:
      return "None"
    elif self.winner == 1:
      return self.t1
    else:
      return self.t2

  def basic_to_string(self):
    return f"Match: {self.code}, Teams: {self.t1} vs {self.t2}, Odds: {self.t1o} vs {self.t2o}, Tournament Name: {self.tournament_name}"
  
  async def close(self, bot, session, ctx=None, close_session=True):
    from views import MatchView, BetView
    from objembed import send_bet_list_embedded, create_match_embedded, create_bet_embedded
    from convert import edit_all_messages
    self.date_closed = get_date()
    old_hidden = []
    for bet in self.bets:
      if bet.hidden == True:
        bet.hidden = False
        bet.set_color(session)
        old_hidden.append(bet)
    embedd = create_match_embedded(self, f"Closed Match")
    if ctx is not None:
      msg = await ctx.respond(content=f"{self.t1} vs {self.t2} betting has closed.", embed=embedd)
      await self.message_ids.append(msg)
      await send_bet_list_embedded("Bets", self.bets, bot, ctx, followup=True)
    if close_session:
      session.commit()
      session.close()
    tasks = []
    tasks.append(edit_all_messages(bot, self.message_ids, embedd, view=MatchView(bot, self)))
    for bet in self.bets:
      embedd = create_bet_embedded(bet, "Placeholder")
      tasks.append(edit_all_messages(bot, bet.message_ids, embedd, view=BetView(bot, bet)))
    await asyncio.gather(*tasks)
      
  
  async def open(self, bot, session, ctx=None, close_session=True):
    from views import MatchView
    from objembed import create_match_embedded
    from convert import edit_all_messages
    if self.date_closed == None:
      if ctx is not None:
        await ctx.respond(f"Match {self.t1} vs {self.t2} is already open.", ephemeral=True)
      return
    self.date_closed = None
    embedd = create_match_embedded(self, f"Opened Match")
    if ctx is not None:
      msg = await ctx.respond(f"{self.t1} vs {self.t2} betting has opened.", embed=embedd, view=MatchView(bot, self))
      await self.message_ids.append(msg)
    if close_session:
      session.commit()
      session.close()
    await edit_all_messages(bot, self.message_ids, embedd, view=MatchView(bot, self))
  
  
  async def set_winner(self, team_num, bot, ctx=None, session=None, close_session=True):
    from objembed import create_match_embedded, create_bet_embedded, create_payout_list_embedded
    from dbinterface import get_all_db, get_channel_from_db
    from User import add_balance_user, get_first_place
    from convert import edit_all_messages
    from views import MatchView, BetView
    
    time = get_date()
    
    self.date_winner = time
    if self.date_closed is None:
      self.date_closed = time
      
    if (team_num == 1) or (team_num == "1") or (team_num == self.t1):
      team_num = 1
    elif (team_num == 2) or (team_num == "2") or (team_num == self.t2):
      team_num = 2
    else:
      if ctx is not None:
        await ctx.respond(f"Invalid team name of {team_num} please enter {self.t1} or {self.t2}.", ephemeral = True)
      print(f"Invalid team name of {team_num} please enter {self.t1} or {self.t2}.")
      return
    
    if self.winner != 0:
      if ctx is not None:
        await ctx.respond(f"Winner has already been set to {self.winner_name()}", ephemeral = True)
      print(f"Winner has already been set to {self.winner_name()}")
      return
    
    self.winner = team_num
    m_embedd = create_match_embedded(self, "Placeholder")
    
    odds = 0.0
    #change when autocomplete
    if team_num == 1:
      odds = self.t1o
      winner_msg = f"Winner has been set to {self.t1}."
    else:
      odds = self.t2o
      winner_msg = f"Winner has been set to {self.t2}."

    users = get_all_db("User", session)
    leader = get_first_place(users)
    msg_ids = []
    bet_user_payouts = []
    date = get_date()
    new_users = []
    for bet in self.bets:
      bet.winner = int(self.winner)
      bet.hidden = False
      payout = -bet.amount_bet
      if bet.team_num == team_num:
        payout += bet.amount_bet * odds
      user = bet.user
      new_users.append(user)
      add_balance_user(user, payout, "id_" + str(bet.code), date)
      while user.loan_bal() != 0 and user.get_clean_bal_loan() > 500:
        user.pay_loan(date)
      embedd = create_bet_embedded(bet, "Placeholder")
      msg_ids.append((bet, embedd))
      bet_user_payouts.append((bet, user, payout))

    new_leader = get_first_place(users)

    embedd = create_payout_list_embedded(f"Payouts of {self.t1} vs {self.t2}:", self, bet_user_payouts)
    channel = await bot.fetch_channel(get_channel_from_db("result", session))
    if ctx is not None:
      await ctx.respond(content=winner_msg, embed=embedd)
    else:
      if channel is not None:
        await channel.send(content=winner_msg, embed=embedd)
        
    if new_leader != leader:
      if channel is not None:
        if new_leader == None:
          await channel.send(f"leader is now tied.")
        else:
          await channel.send(f"{new_leader.username} is now the leader.")
        
      if leader != None:
        #print(f"{leader.color_hex} == dbb40c, {leader.has_leader_profile()}")
        if leader.has_leader_profile():
          print("start 2")
          leader.set_color(get_random_hex_color(), session)
    if close_session and session is not None:
      session.commit()
      session.close()
    tasks = []
    tasks.append(edit_all_messages(bot, self.message_ids, m_embedd, view=MatchView(bot, self)))
    [tasks.append(edit_all_messages(bot, tup[0].message_ids, tup[1], view=BetView(bot, tup[0]))) for tup in msg_ids]
    asyncio.gather(*tasks)
  