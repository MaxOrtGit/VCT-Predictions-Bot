#import libraries
import re
from bs4 import BeautifulSoup
import bs4
import lxml
#import cchardet
from urllib.request import urlopen
from PIL import Image
from collections import Counter
import requests

from sqlaobjs import Session
from convert import get_active_tournaments

from Tournament import Tournament
from Team import Team
from Match import Match
from objembed import send_match_list_embedded
from dbinterface import get_channel_from_db, get_from_db, add_to_db, get_unique_code
from autocompletes import get_team_from_vlr_code, get_match_from_vlr_code, get_tournament_from_vlr_code
from utils import get_random_hex_color, balance_odds, mix_colors, get_date, to_float, to_digit, tuple_to_hex
import sys

try:
  #import webdriver, WebDriverWait, By, and EC
  from selenium import webdriver
  from selenium.webdriver.support.ui import WebDriverWait
  from selenium.webdriver.common.by import By
  from selenium.webdriver.support import expected_conditions as EC
  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_argument("headless")
  driver = webdriver.Chrome(options=chrome_options)
  wait = WebDriverWait(driver, 10)
except Exception as e:
  print(e)
  print("selenium not installed properly, using requests instead (no odds)")
  driver = None
  wait = None
  
#for alternative to selenium
from requests_html import HTMLSession, AsyncHTMLSession
import nest_asyncio

t1_odds_labels = ["match-bet-item-odds mod-1", "match-bet-item-odds mod- mod-1"]
t2_odds_labels = ["match-bet-item-odds mod-2", "match-bet-item-odds mod- mod-2"]
odds_labels = t1_odds_labels + t2_odds_labels

async def get_match_response(match_link, odds_timeout=10):
  if driver is not None:
    driver.get(match_link)
    if odds_timeout != 0:
      print(match_link)
      try:
        WebDriverWait(driver, odds_timeout).until(EC.element_to_be_clickable((By.CLASS_NAME, "match-bet-item-odds")))
      except:
        print("odds not found")
    return driver.page_source
  
  if odds_timeout < 5:
    web_session = requests.Session()
    response = web_session.get(match_link).text
    return response
  
  try:
    nest_asyncio.apply()
    s = AsyncHTMLSession()
    response = await s.get(match_link)
    await response.html.arender(wait=3, sleep=3)
    return response.html.html
  except Exception as e:
    print(e)
    web_session = requests.Session()
    response = web_session.get(match_link).text
    return response

def get_code(link):
  split_link = link.split("/")
  if len(split_link) == 0:
    return None
  if len(split_link) >= 2:
    if (code := to_digit(split_link[-2])) is not None:
      return code
  for part in split_link:
    if (code := to_digit(part)) is not None:
      return code

def get_tournament_link(code):
  link = "https://www.vlr.gg/event/matches/" + str(code) + "/?group=all&series_id=all"
  return link

def get_match_link(code):
  link = "https://www.vlr.gg/" + str(code)
  return link

def get_team_link(code):
  link = "https://www.vlr.gg/team/" + str(code)
  return link


def load_img(img_link):
  response = requests.get(img_link, stream=True)
  img = Image.open(response.raw)
  return img.convert("RGBA")

def get_color_count(img):
  pixels = [p[:3] for p in img.getdata() if p[3] < 255]
  counts = Counter(pixels)
  return counts

#finds the most common pixel in the image image is a link to the image
#clears colorless pixels
def get_most_common_color(img_link):
  if img_link is None:
    return None
  
  #percent of pixels that can be colorless for the image to be considered colorless
  threshold = 0.95
  
  img = load_img(img_link)
  
  # Get a list of all the non-transparent pixel values in the image
  pixels = [p[:3] for p in img.getdata() if p[3] > 25]
      
  # Get the total number of pixels in the image
  total_pixels = len(pixels)
  
  # Get the number of "colored" pixels (i.e. pixels where the RGB values are all not within 40 of each other)
  colored_pixels = [p for p in pixels if max(p) - min(p) > 30]
  colored_count = len(colored_pixels)
  print(colored_count, total_pixels, colored_count / total_pixels, 1 - threshold)

  
  if colored_count / total_pixels > 1 - threshold:
    pixels = colored_pixels

  # Recount the frequency of each pixel value
  counts = Counter(pixels)

  # Get the most common pixel value (which will be a tuple of RGB values)
  most_common = counts.most_common(1)[0][0]

  return most_common
  
def get_team_logo_img(soup, team_name):
  img = soup.find("img", alt=f"{team_name} team logo")
  if img is None:
    return None
  return "http:" + img.get("src")

def get_team_color_from_vlr_page(soup, team_name):
  try:
    img_link = get_team_logo_img(soup, team_name)
    color = get_most_common_color(img_link)
    print(f"{team_name}'s new color: {color}")
    return tuple_to_hex(color)
  except:
    return get_random_hex_color()

def get_tournament_logo_img(soup, tournament_name):
  img = soup.find("img",  alt=tournament_name)
  if img is None:
    return None
  return "http:" + img.get("src")

def get_tournament_color_from_vlr_page(soup, tournament_name, tournament_code = None):
  if soup is None and tournament_code is None:
    return get_random_hex_color()
  
  if soup is None:
    web_session = requests.Session()
    response = web_session.get(get_tournament_link(tournament_code)).text
    print("soup 2")
    soup = BeautifulSoup(response, 'lxml')
  try:
    img_link = get_tournament_logo_img(soup, tournament_name)
    color = get_most_common_color(img_link)
    print(f"{tournament_name}'s color: {color}")
    return tuple_to_hex(color)
  except:
    return get_random_hex_color()

def get_team_name_from_team_vlr(soup):
  team_name = soup.find("h1", class_="wf-title")
  if team_name is None:
    return None
  return team_name.get_text().strip()


def update_team_with_vlr_code(team, team_vlr_code, soup = None, session = None, force_color_update = False, do_query_site = True):
  updated_vlr_code = False
  if team.vlr_code is None:
    if team_vlr_code is None:
      return
    updated_vlr_code = True
    team.vlr_code = team_vlr_code
    #can move code here to the end of the function to always recolor
  else:
    team_vlr_code = team.vlr_code
    
  if do_query_site:
    if team_vlr_code is not None:
      if soup is None:
        web_session = requests.Session()
        response = web_session.get(get_team_link(team_vlr_code)).text
        print("soup 3")
        soup = BeautifulSoup(response, 'lxml')
        name = get_team_name_from_team_vlr(soup)
        if name is not None:
          team.set_name(name, session)
      if updated_vlr_code or force_color_update:
        print("updating color")
        team.set_color(get_team_color_from_vlr_page(soup, team.name), session)
  

async def vlr_get_today_matches(bot, tournament_code, session) -> list:
  if tournament_code is None:
    return []
  if session is None:
    with Session.begin() as session:
      return await vlr_get_today_matches(bot, tournament_code, session)
    
  tournament_link = get_tournament_link(tournament_code)
  web_session = requests.Session()
  response = web_session.get(tournament_link).text
  #print("soup 4")
  soup = BeautifulSoup(response, 'lxml')
  
  col = soup.find("div", class_="col mod-1")
  #date_labels = col.find_all("div", class_="wf-label mod-large")
  if type(col) is not bs4.element.Tag:
    print("col not Tag")
    raise Exception("col not Tag")
  
  # top is not a matches card
  day_matches_cards = col.find_all("div", class_="wf-card")
  
  if len(day_matches_cards) == 0:
    return []
  
  # if buffer_active is true, all matches within a day will be generated
  # activates if match within 12 hours is found
  continuos_buffer = 12
  
  match_codes = []
  for day_matches_card in day_matches_cards:
    for match_card in day_matches_card.find_all("a", class_="wf-module-item"):
      #get match code
      match_link = match_card.get("href")
      if match_link is None:
        print(f"match link is None {match_card}")
        continue
      match_code = get_code(match_link)
      
      # for each match card in day group
      # get status
      status_label = match_card.find("div", class_="ml-status")
      if status_label is None:
        print(f"status label for {match_code} is None")
        continue
      status = status_label.get_text().lower()
      
      # continue if status is TBD
      if status.__contains__("tbd"):
        continue
      
      # if live match close and continue
      if status.__contains__("live"):
        # check if match is already closed
        #print(f"{match_code} status: {status}")
        if (match := get_match_from_vlr_code(match_code, session)) is None:
          print(f"live match with code {match_code} not found")
          continue
        if match.date_closed is None:
          # close match
          print(f"closing match {match_code}")
          await match.close(bot, session)
        continue
      
      # completed and upcoming matches
      # get eta to match
      eta_label = match_card.find("div", class_="ml-eta")
      if eta_label is None:
        print(f"eta label for {match_code} is None for status {status}")
        continue
      eta = eta_label.get_text().lower()
      
      # continue if eta ends with "mo"
      if eta.endswith("mo"):
        continue
      # continue if eta ends with "y"
      if eta.endswith("y"):
        continue
      
      # minute not there when day is
      if not eta.__contains__("m"):
        continue
      # if hours in eta is more than 12, continue (if not matches_for_day)
      if eta.__contains__("h"):
        eta_groups = eta.split(" ")
        continue_out = False
        for eta_group in eta_groups:
          if eta_group.__contains__("h"):
            eta_group = eta_group.replace("h", "")
            hours = to_digit(eta_group)
            if hours is None:
              print(f"hours for {match_code} is None, eta: {eta}")
              continue_out = True
              break
            # if time until match is greater than both 12 and continuos_buffer dont make matches
            if hours > 11 and hours > continuos_buffer:
              continue_out = True
            else:
              if status.__contains__("upcoming"):
                continuos_buffer = hours + 4
            break
        if continue_out:
          continue
      else:
        if (match := get_match_from_vlr_code(match_code, session)) is None:
          print(f"Cant send warning for {match_code} because match is None")
        else:
          if (not match.alert) and match.date_closed is None:
            await match.send_warning(bot, session)
        
      #print(f"acting on {match_code}, status: {status}, eta: {eta}")
      
      #if completed check if match has a winner then set winner
      if status.__contains__("completed"):
        if (match := get_match_from_vlr_code(match_code, session)) is None:
          print(f"completed match with code {match_code} not found")
          continue
        # check if match has a winner
        if match.winner == 0:
          # get teams cards
          teams_cards = match_card.find_all("div", class_="match-item-vs-team")
          if len(teams_cards) != 2:
            print("can't find teams")
            continue
          
          # check which team has the "mod-winner" class and set winner
          winner = 0
          if teams_cards[0].get("class").__contains__("mod-winner"):
            winner = 1
          else:
            winner = 2
          print(f"setting winner for match {match_code} to {winner}")
          await match.set_winner(winner, bot, session=session)
          print(match.winner_name())
        continue
      
      
      if status.__contains__("upcoming"):
        match_codes.append(match_code)
  
  return match_codes

def get_or_create_team(team_name, team_vlr_code, session=None, team_soup=None, match_soup=None, second_query=True):
  if session is None:
    with Session.begin() as session:
      get_or_create_team(team_name, team_vlr_code, session, team_soup, match_soup, second_query)
  
  team = get_from_db("Team", team_name, session)
  if team is not None:
    update_team_with_vlr_code(team, team_vlr_code, team_soup, session, do_query_site=second_query)
    return team
  
  if team_vlr_code is not None:
    team = get_team_from_vlr_code(team_vlr_code, session)
    if team is not None:
      team.set_name(team_name, session)
      return team
    if team_soup is None:
      if match_soup is None:
        if second_query:
          web_session = requests.Session()
          response = web_session.get(get_team_link(team_vlr_code)).text
          print("soup 5")
          team_soup = BeautifulSoup(response, 'lxml')
      else:
        team_soup = match_soup
    if team_soup is not None:
      color = get_team_color_from_vlr_page(team_soup, team_name)
    else:
      color = get_random_hex_color()
  else:
    color = get_random_hex_color()
  
  team = Team(team_name, team_vlr_code, color)
  add_to_db(team, session)
  return team


def get_team_codes_from_match_page(soup):
  t1_link_div = soup.find("a", class_="match-header-link wf-link-hover mod-1")
  t2_link_div = soup.find("a", class_="match-header-link wf-link-hover mod-2")
  if t1_link_div is None or t2_link_div is None:
    print(f"team link not found")
    return None, None
  
  t1_vlr_code = t1_link_div.get("href").split("/")[2]
  t2_vlr_code = t2_link_div.get("href").split("/")[2]
  return t1_vlr_code, t2_vlr_code

def get_odds_from_match_page(soup):
  found_odds = False
  for i in range(len(t1_odds_labels)):
    t1_vlr_odds_label = soup.find("span", class_=t1_odds_labels[i])
    t2_vlr_odds_label = soup.find("span", class_=t2_odds_labels[i])
    
    if ((t1_vlr_odds_label is None) or (t2_vlr_odds_label is None)):
      t1_vlr_odds_label = None
      t2_vlr_odds_label = None
      continue
    
      
    t1oo = to_float(t1_vlr_odds_label.get_text().strip())
    t2oo = to_float(t2_vlr_odds_label.get_text().strip())
    found_odds = True
    if (t1oo is None) or (t2oo is None):
      t1oo = None
      t2oo = None
      continue
    
    if t1oo <= 1 or t2oo <= 1:
      t1oo = None
      t2oo = None
      continue
  
  if not found_odds:
    print(f"label not found odds not found")
    return None, None
  
  if t1oo is None or t2oo is None:
    print(f"not valid number odds not found")
    return None, None
  
  return t1oo, t2oo

def get_team_names_from_match_page(soup):
  names = soup.find_all("span", class_="match-bet-item-team")
  if len(names) != 2:
    names = soup.find_all("div", class_="wf-title-med")
    if len(names) != 2:
      names = soup.find_all("div", class_="wf-title-med ")
      if len(names) != 2:
        names = soup.find_all("div", class_="wf-title-med mod-single")
        if len(names) != 2:
          print(f"team names not found, names: {names}")
          return None, None
  
  t1_name = names[0].get_text().strip()
  t2_name = names[1].get_text().strip()
  
  return t1_name, t2_name

def get_teams_from_match_page(soup, session, second_query=True):
  t1_vlr_code, t2_vlr_code = get_team_codes_from_match_page(soup)
  t1_name, t2_name = get_team_names_from_match_page(soup)
  if t1_vlr_code is None or t1_name is None:
    return None, None
  team1 = get_or_create_team(t1_name, t1_vlr_code, session, match_soup=soup, second_query=second_query)
  team2 = get_or_create_team(t2_name, t2_vlr_code, session, match_soup=soup, second_query=second_query)
  return team1, team2

def get_tournament_name_and_code_from_match_page(soup):
  match_header = soup.find("a", class_="match-header-event")
  if match_header is None:
    print(f"match header not found")
    return None, None
  code = get_code(match_header.get("href"))
  tournament_div = match_header.find("div", attrs={'style': 'font-weight: 700;'})
  if tournament_div is None:
    print(f"tournament not found")
    return None, None
  return tournament_div.get_text().strip(), code
  
  
async def vlr_create_match(match_code, tournament, bot, session=None):
  if session is None:
    with Session.begin() as session:
      return await vlr_create_match(match_code, tournament, bot, session)
  
  if (match := get_match_from_vlr_code(match_code, session)) is not None:
    if match.has_bets or match.date_closed is not None:
      #if match.date_closed is not None:
      #  print(f"match {match_code} already closed")
      #else:
      #  print(f"match {match_code} already has bets")
      return None
    
  match_link = get_match_link(match_code)
  response = await get_match_response(match_link)
  #print("soup 6")
  soup = BeautifulSoup(response, 'lxml')
  
  t1oo, t2oo = get_odds_from_match_page(soup)
  if t1oo is None:
    return None
  t1o, t2o = balance_odds(t1oo, t2oo)
  
  if match is not None:
    from convert import edit_all_messages
    from objembed import create_match_embedded
    from views import MatchView
    #print("updating odds")
    match.t1oo = t1oo
    match.t2oo = t2oo
    
    match.t1o = t1o
    match.t2o = t2o
    embedd = create_match_embedded(match, "Placeholder")
    # works because updating is never time sensitive
    await edit_all_messages(bot, match.message_ids, embedd, view=MatchView(bot, match))
    return None
  
  team1, team2 = get_teams_from_match_page(soup, session)
  if team1 is None or team2 is None:
    return None
  
  t1 = team1.name
  t2 = team2.name
  
  odds_source = "VLR.gg"
  color_hex = mix_colors([(team1.color_hex, 3), (team2.color_hex, 3), (tournament.color_hex, 1)])
  date_created = get_date()
  code = get_unique_code("Match", session)
    
  return Match(code, t1, t2, t1o, t2o, t1oo, t2oo, tournament.name, odds_source, color_hex, None, date_created, match_code)


async def generate_matches_from_vlr(bot, session=None, reply_if_none=True):
  if session is None:
    with Session.begin() as session:
      return await generate_matches_from_vlr(bot, session, reply_if_none)
  from objembed import create_match_embedded
  from views import MatchView
  
  tournaments = get_active_tournaments(session)
  
  matches = []
  
  match_channel = await bot.fetch_channel(get_channel_from_db("match", session))
  
  for tournament in tournaments:
    match_codes = await vlr_get_today_matches(bot, tournament.vlr_code, session)
    #print(f"generating matches with codes: {match_codes}")
    for match_code in match_codes:
      match = await vlr_create_match(match_code, tournament, bot, session)
      if match is None:
        continue
      add_to_db(match, session)
      
      if match_channel is not None:
        embedd = create_match_embedded(match, f"New Match")
        msg = await match_channel.send(embed=embedd, view=MatchView(bot, match))
        await match.message_ids.append(msg)
      matches.append(match)
  
  if match_channel is not None:
    if len(matches) != 1 and (reply_if_none or len(matches) != 0):
      await send_match_list_embedded(f"Generated Matches", matches, bot, match_channel)


async def get_or_create_tournament(tournament_name, tournament_vlr_code, guild, session, activate_on_create=True):
      
  tournament = get_from_db("Tournament", tournament_name, session)
  if tournament is not None:
    if tournament.vlr_code is not None:
      return tournament
    tournament.vlr_code = tournament_vlr_code
    return tournament
  
  if tournament_vlr_code is not None:
    tournament = get_tournament_from_vlr_code(tournament_vlr_code, session)
    if tournament is not None:
      return tournament
    
  color = get_tournament_color_from_vlr_page(None, tournament_name, tournament_vlr_code)
  
  tournament = Tournament(tournament_name, tournament_vlr_code, color)
  if activate_on_create:
    await tournament.activate(guild)
  else:
    await tournament.deactivate(guild)
  add_to_db(tournament, session)
  return tournament
  
def generate_tournament(vlr_code, session=None):
  if session is None:
    # if the session is not provided, create a session with a context manager
    with Session.begin() as session:
      generate_tournament(vlr_code, session)
      
  # check if the tournament already exists
  if get_tournament_from_vlr_code(vlr_code, session) is not None:
    return None
  
  # get the tournament page from the vlr code
  tournament_link = get_tournament_link(vlr_code)
  web_session = requests.Session()
  response = web_session.get(tournament_link).text
  print("soup 7")
  soup = BeautifulSoup(response, 'lxml')
  print(f"generating tournament from link: {tournament_link}")
  
  # get the tournament name and color from the page
  tournament_text = soup.find("h1", class_="wf-title")
  if tournament_text is None:
    print("tournament text is none")
    return None
  tournament_name = tournament_text.get_text().strip()
  tournament_color = get_tournament_color_from_vlr_page(soup, tournament_name)
  
  # create the tournament object
  tournament = Tournament(tournament_name, vlr_code, tournament_color)
  
  # add the tournament to the database
  add_to_db(tournament, session)
  return tournament

def generate_team(vlr_code, session=None):
  # if no session is passed in, create one and pass it to itself
  if session is None:
    with Session.begin() as session:
      generate_team(vlr_code, session)
      
  # if team already exists, return it
  if (team := get_team_from_vlr_code(vlr_code, session)) is not None:
    update_team_with_vlr_code(team, vlr_code, None, session, True)
    return team
  
  # get team link from vlr code
  team_link = get_team_link(vlr_code)
  print(f"generating team from link: {team_link}")
  # open team link
  web_session = requests.Session()
  response = web_session.get(team_link).text
  print("soup 8")
  team_soup = BeautifulSoup(response, 'lxml')
  # get team name from team link
  team_name = get_team_name_from_team_vlr(team_soup)
  
  # if team already exists, return it
  if (team := get_from_db("Team", team_name, session)) is not None:
    update_team_with_vlr_code(team, vlr_code, team_soup, session, True)
    return team
  
  # if team does not exist, create it
  team_color = get_team_color_from_vlr_page(team_soup, team_name)
  team = Team(team_name, vlr_code, team_color)
  add_to_db(team, session)
  return team