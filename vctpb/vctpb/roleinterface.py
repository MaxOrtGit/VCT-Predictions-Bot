import discord
from colorinterface import hex_to_tuple


def get_role(user, username):
  roles = user.roles
  for role in roles:
    if role.name == f"Prediction {username}":
      return role
  return None

async def create_role(guild, username, hex):
  return await guild.create_role(name = f"Prediction {username}", color=discord.Color.from_rgb(*hex_to_tuple(hex)))
  
async def add_role(user, role):
  await user.add_roles(role)

def delete_role(role):
  role.delete()
  
async def recolor_role(role, hex):
  await role.edit(color=discord.Color.from_rgb(*hex_to_tuple(hex)))

async def set_role(guild, author, username, hex):
  role = get_role(author, username)
  if role is None:
    role = await create_role(guild, username, hex)
    await add_role(author, role)
  else:
    await recolor_role(role, hex)

async def unset_role(author, username):
  role = get_role(author, username)
  if role is not None:
    delete_role(role)
    
async def edit_role(author, username, hex):
  role = get_role(author, username)
  if role is not None:
    await recolor_role(role, hex)
    
  
def has_role(user, username):
  return get_role(user, username) is not None