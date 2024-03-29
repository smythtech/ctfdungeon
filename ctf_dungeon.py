#!/usr/bin/python3

'''
    CTF Dungeon: A text-based adventure game engine for Capture The Flag (CTF) games.
    Copyright (C) 2022 Dylan Smyth

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
'''

import os
import sys
import html
import json
import random
import datetime
import re

sessions = {}

class Player():

  def __init__(self, name):
    self.id = self.generate_id()
    self.name = ""
    self.points = 0
    self.items = []
    self.current_room = {}

  def generate_id(self):
    return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz1234567890") for _ in range(64))


class Dungeon():

  # Default Constructer
  def __init__(self):
    self.dungeon = {}
    self.players = {} # For future multiplayer
    self.dungeon_filename = ""

  # Load and parse dungeon json file
  def load_dungeon(self, d_file):
    f = open(d_file, 'r')
    json_data = json.loads(f.read())
    self.dungeon = json_data["dungeon"]
    self.dungeon_filename = d_file.split(".json")[0]
    f.close()

  def add_player(self, player):
    player.current_room = self.get_room("start")
    self.players[player.id] = player

  # Return name and desc of current dungeon
  def get_dungeon_desc(self):
    desc = ""
    desc +=  self.dungeon["name"]
    desc += "\n"
    desc += self.dungeon["description"]
    desc += "\n"
    return desc

  # Get data for current room
  def get_room(self, room_id):
    return self.dungeon["rooms"][room_id]

  # Return name and desc of given room
  def get_room_desc(self, room):
    desc = ""
    desc += "You are in the " + room["name"]
    desc += "\n"
    desc += room["description"]
    desc += "\n"
    desc += "\nTo the north " + self.get_direction_desc(room["directions"]["north"])
    desc += "\nTo the south " + self.get_direction_desc(room["directions"]["south"])
    desc += "\nTo the east " + self.get_direction_desc(room["directions"]["east"])
    desc += "\nTo the west " + self.get_direction_desc(room["directions"]["west"])
    desc += "\n"
    return desc

  def get_direction_desc(self, dir):
    s = dir["description"]
    state = "locked" if dir["locked"] else "open"
    return s.replace("$STATE$", state)

  # Return name and desc of given item
  def get_item_desc(self, item):
    desc = ""
    desc +=  item["name"]
    desc += "\n"
    desc += item["description"]
    desc += "\n"
    return desc

  # Get the next endpoint based off the given room and direction
  def get_next_path(self, room, direction):
    if(direction in room["directions"]):
      return room["directions"][direction][leads_to]
    else:
      return self.dungeon["rooms"]["undefined"]

  # Find a custom room action if one exists. Return that action object.
  def get_custom_action(self, action_name, room_actions):
    for act_re in room_actions:
      match = re.search(act_re, action_name)
      if(match):
        return room_actions[act_re]

  # Use pass in json object and list that object appears in to get the name for that object.
  def get_obj_name(self, obj, obj_list):
    obj_desc = obj["description"]
    for o_name in obj_list:
      desc = obj_list[o_name]["description"]
      if(obj_desc == desc):
        return o_name

  def get_matching_feature(self, thing, features):
    for feature_re in features:
      match = re.search(feature_re, thing)
      if(match):
        return (feature_re, features[feature_re])

  # Handle action verb and route to relevant function
  def parse_action(self, player_id, action):
    routes = {
      "go": self.parse_go,
      "examine": self.parse_examine,
      "use": self.parse_use,
    }
    room = self.players[player_id].current_room
    verb = action.split(" ")[0]
    act = self.get_custom_action(action, room["actions"])
    if(act):
      return self.parse_room_action(player_id, act, room)
    elif(verb in routes):
      return routes[verb](player_id, action)

    return "Can't do that..."

   # Parse a go action
  def parse_go(self, player_id, action):
    current_room = self.players[player_id].current_room
    dir = action.replace("go ", "")
    s = ""
    if(dir == ""):
      s = "Go where?"
    elif(dir not in current_room["directions"]):
      s += "Can't go that way..."
    else:
      way = current_room["directions"][dir]
      if(way["locked"]):
        s+= "This way is locked."
      elif(way["leads_to"] == ""):
        s += "That direction doesn't seem to lead anywhere..."
      else:
        s += way["on_enter"]
        self.players[player_id].current_room = self.dungeon["rooms"][way["leads_to"]]
    return s

  # Parse an examine action
  def parse_examine(self, player_id, action):
    thing = action.replace("examine ", "")
    current_room = self.players[player_id].current_room
    room_desc = current_room["description"].replace(".", " ")
    matching_feature = self.get_matching_feature(thing, current_room["features"])
    s = ""
    if(thing == "bag"):
      items = self.players[player_id].items
      if(len(items) == 0):
        s = "There is nothing in your bag."
      else:
        s = "The follow items are in your bag:\n"
        for i in items:
          s += i
          s += "\n"
    elif(thing == "room"):
      s =  self.get_room_desc(current_room)
    elif(thing in self.players[player_id].items):
      s =  self.get_item_desc(self.dungeon["items"][thing])
    elif(matching_feature and matching_feature[1]):
      feature = matching_feature[1]
      s = feature["description"]
      locked = feature["locked"]
      if("$STATE$" in s):
        state = "locked" if locked else "open"
        s = s.replace("$STATE$", state)
      if(locked == False and feature["item"] != ""):
        item_name = self.dungeon["rooms"][current_room["id"]]["features"][thing]["item"]
        s += "\n"
        s += self.dungeon["items"][item_name]["found"]
        s += self.get_rewards(player_id, current_room, feature)
    elif((" " + thing + " ") in self.get_room_desc(current_room)):
      s = "Nothing more to say about it..."
    else:
      s = "Can't examine that..."

    return s


  # Parse a use action
  def parse_use(self, player_id, action):
    s = ""
    current_room = self.players[player_id].current_room
    player_inv = self.players[player_id].items
    if(" on " in action):
      things = action.split(" on ")
      item = things[0].replace("use ", "")
      feature = self.get_matching_feature(thing[1], current_room["features"])[0]
      if(item in player_inv):
        if(feature in current_room["features"]):
          if(item == current_room["features"][feature]["requires"]):
            self.change_feature_lock_state(player_id, current_room, feature)
            s += self.dungeon["items"][item]["use_success"]
          else:
            s += self.dungeon["items"][item]["use_fail"]
        else:
          s = "There is no " + feature + " here that you can interact with..."
      else:
        s = "You do not have a " + item + "."
    else:
      item = action.replace("use", "").strip()
      if(item in player_inv):
        pass
      elif(item.strip() == ""):
        s = "Use what?"
      else:
        s = "You do not have a " + item
    return s

  # Parse special action for room
  def parse_room_action(self, player_id, action, room):

    s = action["description"]

    unlocks_feature = action["unlocks"]
    matching_feature = self.get_matching_feature(action["unlocks"], room["features"])

    print(f'unlocks: {unlocks_feature} ----- matching {matching_feature}')

    if(unlocks_feature != ""):
      if(matching_feature):
        self.change_feature_lock_state(player_id, room, matching_feature[0])
        s += action["action_success"]
      else:
        s += action["action_fail"]
    if(action["item"] != ""):
      item_name = action["item"]
      s += "\n"
      s += self.dungeon["items"][item_name]["found"]

    s += self.get_rewards(player_id, room, action)
    return s

  # Change feature state
  def change_feature_lock_state(self, player_id, current_room, feature):
    self.dungeon["rooms"][current_room["id"]]["features"][feature]["locked"] = False
    self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]
    dir = current_room["features"][feature]["linked_to"]
    if(dir != ""):
      if(dir in current_room["directions"]):
        self.dungeon["rooms"][current_room["id"]]["directions"][dir]["locked"] = False
        self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]


  def get_rewards(self, player_id, current_room, obj):
    item = obj["item"]
    point = obj["points"]

    room_features = self.dungeon["rooms"][current_room["id"]]["features"] # [thing]["item"] = ""
    room_actions = self.dungeon["rooms"][current_room["id"]]["actions"] # [thing]["points"] = 0

    s = ""
    if(item != ""):
      item_obj = self.dungeon["items"][item]
      self.players[player_id].items.append(item)
      s += "<br>You have aquired: " + item_obj["name"]
      if(item_obj["file_action"] == "read"):
        f = open(item_obj["file_path"], 'r')
        s += f.read()
        f.close()
      elif(item_obj["file_action"] == "download"):
        s += "<a href='" + item_obj["file_path"] + "'>Download</a>"
    if(point > 0):
      self.players[player_id].points += point
      s += "<br>You have gained " + str(point) + " point(s)"
      s += "<br>You have " + str(self.players[player_id].points) + " points"
    if(self.players[player_id].points >= self.dungeon["max_points"]):
      s += "<br><br>Congratulations! You have completed " + self.dungeon["name"]

    obj_name = None
    obj_name = self.get_obj_name(obj, room_features)
    if(obj_name == None):
      obj_name = self.get_obj_name(obj, room_actions)

    if(obj_name in room_features):
      room_features[obj_name]["item"] = ""
      room_features[obj_name]["points"] = 0
    elif(obj_name in room_actions):
      room_actions[obj_name]["item"] = ""
      room_actions[obj_name]["points"] = 0

    self.dungeon["rooms"][current_room["id"]]["features"] = room_features
    self.dungeon["rooms"][current_room["id"]]["actions"] = room_actions
    self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]

    return s

# Cookie creator borrowed from https://stackoverflow.com/questions/14107260/set-a-cookie-and-retrieve-it-with-python-and-wsgi
def set_cookie_header(name, value, days=365):
    dt = datetime.datetime.now() + datetime.timedelta(days=days)
    fdt = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
    secs = days * 86400
    return ('Set-Cookie', '{}={}; Expires={}; Max-Age={}; Path=/'.format(name, value, fdt, secs))

def get_page(file):
  f = open("www/" + file + ".html", 'r')
  contents = f.read()
  f.close()
  return contents

def handle_file_download_request(env, path):
  cookies = get_cookies(env)

  if(("session" in cookies) and (cookies["session"] in sessions)):
    item_id = path.split("/")[-1]
    player = sessions[cookies["session"]].players[cookies["session"]]
    dungeon_items = sessions[cookies["session"]].dungeon["items"]

    if((item_id in dungeon_items) and (item_id in player.items)):
      item_file_path = dungeon_items[item_id]["file_path"]
      if(len(item_file_path) > 0):
        f = open(item_file_path, "rb")
        size = os.path.getsize(item_file_path)
        resp_headers = [('Content-Type', 'application/octet-stream'), ('Content-length', str(size)), ('Content-Disposition', 'attachment; filename='+ item_file_path.split("/")[-1])]
        if 'wsgi.file_wrapper' in env:
          file_read =  env['wsgi.file_wrapper'](f, 1024)
        else:
          file_read = iter(lambda: f.read(1024), '')
        f.close()
    else:
      file_read = ""
      resp_headers = [('Content-Type', 'text/html')]
  else:
    file_read = ""
    resp_headers = [('Content-Type', 'text/html')]

  return file_read, resp_headers


def get_scoreboard():
  players = "<table>"
  for p in sessions:
    players += "<tr>"
    players += "<td>"
    players += sessions[p].players[p].name
    players += "</td><td>"
    players += str(sessions[p].players[p].points)
    players += "</td><td>"
    players += sessions[p].players[p].current_room["name"]
    players += "</td></tr>"

  players += "</table>"

  return players

def replace_placeholders(output, env):
  protocol = 'http'
  if 'HTTPS' in env or env['wsgi.url_scheme'] == 'https':
    protocol = 'https'
  output = output.replace("$SERVER_IP$", protocol)
  output = output.replace("$SERVER_PORT$", env['HTTP_HOST'])
  if("$GAMES$" in output):
    output = output.replace("$GAMES$", build_games_table_html())
  return output

def get_games(games_file):
  games_file = "./games/games.json"
  f = open(games_file, 'r')
  games = json.loads(f.read())
  f.close()
  return games["games"]

def build_games_table_html():
  try:
    games = get_games("./games/games.json") # Hardcode for now. Might change later.

    html_output = '<div id="game-select" name="game-select">'
    for i in games:
      html_output += '<div id="game-option" onclick=\'setupGame(\"' + i["id"] + '\");\'>'
      html_output += '<div id="game-option-art" name="game-option-art">'
      if(i["art_type"] == "text"):
        html_output += '<pre>'
        f = open(i["art_file"])
        html_output += f.read()
        f.close()
        html_output += '</pre>'

      html_output += '</div>'
      html_output += '<div id="game-option-name" name="game-option-name">'
      html_output += '<h2>' + i["name"] + '</h2>'
      html_output += '<p>Difficulty: ' + i["difficulty"] + '<br>'
      html_output += 'Length: ' + i["length"] + '</p>'
      html_output += '</div>'
      html_output += '</div><br>'
    html_output += '</div>'

    return html_output
  except Exception as e:
    return "Error getting available games..."

# API endpoint alternitive to the websocket. Easier for deployment on third-party services that use wsgi rather than uwsgi
def handle_player_request(game, env):
  cookies = get_cookies(env)
  resp = ""
  resp_headers = [('Content-Type', 'text/html')]
  dungeon = {}

  content_length = int(env["CONTENT_LENGTH"])
  content = env["wsgi.input"].read(content_length)
  content = content.decode('utf-8')
  action = content.replace("action=", "")
  action = html.escape(action)

  if(("session" not in cookies) or (cookies["session"] not in sessions) or (action == "init")):
    player = Player("player")
    player.name = "Anon"
    games = get_games("./games/games.json")
    dungeon_file_path = ""
    for g in games:
      if(g["id"] == game):
        dungeon_file_path = g["path"]
    if(dungeon_file_path == ""):
      resp = "Dungeon not found"
      return resp, resp_headers

    dungeon = Dungeon()
    dungeon.load_dungeon(dungeon_file_path)
    dungeon.add_player(player)
    sessions[player.id] = dungeon
    resp_headers.append(set_cookie_header("session", player.id))

    resp = "Connected to game<br><br>" + dungeon.get_dungeon_desc()
    resp += "<br/>Start by using the action \"examine room\""
    resp = resp.replace("\n", "<br>")

  else:
    dungeon = sessions[cookies["session"]]
    resp = "<br><b style='color:#FFFFFF'>> " + action + "</b><br>"
    resp += dungeon.parse_action(cookies["session"], action)
    resp = resp.replace("\n", "<br/>") # TODO change this depending on HTTP header values. Will allow support for terminals and browsers

  return resp, resp_headers

def get_cookies(env):
  cookie = {}
  try:
    if("HTTP_COOKIE" in env):
      cookie = {}
      cookies = env["HTTP_COOKIE"].split(";")
      for c in cookies:
        cs = c.split("=")
        cookie[cs[0]] = cs[1]
  except:
    return {}
  return cookie

# uwsgi handler
def application(env, sr):
  global sessions

  resp_code = ""
  resp_headers = []

  # For more routes to be added later
  static_pages = {
    "/": "index",
    "/help": "help"
  }

  dynamic_pages = {
    "/scoreboard": get_scoreboard
  }

  path = env['PATH_INFO']
  path_split = path.split("/")

  try:

    if(env["REQUEST_METHOD"] == "GET"):
      if(path in static_pages):
	# Get contents of file to go with the static page
        output = get_page(static_pages[path])
        output = replace_placeholders(output, env)
        resp_headers = [('Content-Type', 'text/html')]
        resp_code = '200 OK'
      elif(path in dynamic_pages):
	# Call function associated with dymanic page
        output = dynamic_pages[path]()
        output = replace_placeholders(output, env)
        resp_headers = [('Content-Type', 'text/html')]
        resp_code = '200 OK'
      elif("download" in path):
        # File download request
        resp_code = '200 OK'
        output, resp_headers = handle_file_download_request(env, path)
        sr(resp_code, resp_headers)
        return output # Return here as we don't want the file data to be encoded
      else:
        output = get_page("404")
        resp_headers = [('Content-Type', 'text/html')]
        resp_code = '404 NOT FOUND'

    elif(env["REQUEST_METHOD"] == "POST"):
      if(len(path_split) > 2 and path_split[1] == "play"):
        output, resp_headers = handle_player_request(path_split[2], env)
        resp_code = '200 OK'
  except Exception as e:
    resp_code = '200 OK'
    resp_headers = [('Content-Type', 'text/html')]
    output = "An error has occurred."
    output += str(e)

  sr(resp_code, resp_headers)
  return output.encode("utf-8")
