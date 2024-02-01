from sqlalchemy import Column, String, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlaobjs import mapper_registry, Session
from utils import get_random_hex_color
from User import alert_association_table
from roleinterface import get_role, delete_role, create_role, add_to_role

@mapper_registry.mapped
class Tournament():
  
  __tablename__ = "tournament"
  
  name = Column(String(100), primary_key=True, nullable=False)
  vlr_code = Column(Integer)
  color_name = Column(String(32), ForeignKey("color.name"))
  color = relationship("Color", back_populates="tournaments")
  color_hex = Column(String(6))
  active = Column(Boolean)
  matches = relationship("Match", back_populates="tournament")
  bets = relationship("Bet", back_populates="tournament")
  alert_users = relationship("User", secondary=alert_association_table, back_populates="alert_tournaments")
  
  def __init__(self, name, vlr_code, color):
    self.name = name
    self.vlr_code = vlr_code
    self.set_color(color)
    self.active = vlr_code is not None
    
  def __repr__(self):
    return f"<Tournament {self.name}>"
        
  def set_color(self, color, session=None):
    if color is None:
      self.color = None
      self.color_name = None
      self.color_hex = get_random_hex_color()
    elif isinstance(color, str):
      if self.color_hex == color:
        return
      self.color = None
      self.color_name = None
      self.color_hex = color
    else:
      self.color = color
      self.color_name = color.name
      self.color_hex = color.hex
    
    if session is not None:
      for match in self.matches:
        match.set_color(session)
  
  async def create_role(self, guild):
    role = await create_role(guild, f"{self.name} Alert", self.color_hex)
    for user in self.alert_users:
      member = guild.get_member(user.code)
      if member is not None:
        await add_to_role(member, role)
        
  async def delete_role(self, guild):
    while (role := get_role(guild, f"{self.name} Alert")) is not None:
      if role is not None:
        await delete_role(role)
  
  async def activate(self, guild):
    self.active = True
    self.create_role(guild)
    
  async def deactivate(self, guild):
    self.active = False
    await self.delete_role(guild)
    users = self.alert_users.copy()
    for user in users:
      self.alert_users.remove(user)
      