import discord
from utils import hex_to_tuple


def get_role(guild, name):
  roles = guild.roles
  for role in roles:
    if role.name == name:
      return role
  return None

async def create_role(guild, name, hex):
  role = await guild.create_role(name = name, color=discord.Color.from_rgb(*hex_to_tuple(hex)))
  return role
  
async def add_to_role(member, role):
  await member.add_roles(role)

async def remove_from_role(member, role):
  await member.remove_roles(role)

async def delete_role(role):
  await role.delete()
  
async def recolor_role(role, hex):
  await role.edit(color=discord.Color.from_rgb(*hex_to_tuple(hex)))
  
async def rename_role(role, new_name):
  await role.edit(name=new_name)
  
def has_role(role, member):
  return role in member.roles

async def create_predictions_manager_role(guild):
  if get_role(guild, "Predictions Manager") is None:
    return await create_role(guild, "Predictions Manager", "9950E0")

async def has_pm_role(ctx):
  if has_role(get_role(ctx.guild, "Predictions Manager"), ctx.author):
    return True
  else:
    await ctx.respond("You do not have the Predictions Manager role.", ephemeral=True)
    return False