#!/usr/bin/python3

import sys
import html
import json
import random
import datetime

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
    self.players = {}

  # Load and parse dungeon json file
  def load_dungeon(self, d_file):
    f = open(d_file, 'r')
    json_data = json.loads(f.read())
    self.dungeon = json_data["dungeon"]
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

  # Handle action verb and route to relevant function
  def parse_action(self, player_id, action):
    routes = {
      "go": self.parse_go,
      "examine": self.parse_examine,
      "use": self.parse_use,
    }
    room = self.players[player_id].current_room
    verb = action.split(" ")[0]
    if(verb in routes):
      return routes[verb](player_id, action)
    elif(action in room["actions"]):
      return self.parse_room_action(player_id, action, room["actions"])
    else:
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
    elif(thing in current_room["features"]):
      feature = current_room["features"][thing]
      s = feature["description"]
      locked = feature["locked"]
      if("$STATE$" in s):
        state = "locked" if locked else "open"
        s = s.replace("$STATE$", state)
      if(locked == False and feature["item"] != ""):
        item_name = self.dungeon["rooms"][current_room["id"]]["features"][thing]["item"]
        s += "\n"
        s += self.dungeon["items"][item_name]["found"]
        s += self.get_rewards(player_id, feature)
        self.dungeon["rooms"][current_room["id"]]["features"][thing]["item"] = ""
        self.dungeon["rooms"][current_room["id"]]["features"][thing]["points"] = 0
        self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]
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
      feature = things[1]
      if(item in player_inv):
        if(feature in current_room["features"]):
          if(item == current_room["features"][feature]["requires"]):
            self.dungeon["rooms"][current_room["id"]]["features"][feature]["locked"] = False
            self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]
            dir = current_room["features"][feature]["linked_to"]
            if(dir != ""):
               if(dir in current_room["directions"]):
                 self.dungeon["rooms"][current_room["id"]]["directions"][dir]["locked"] = False
                 self.players[player_id].current_room = self.dungeon["rooms"][current_room["id"]]
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
  def parse_room_action(self, player_id, action, actions):
    s = actions[action]["description"]
    s += self.get_rewards(player_id, actions[action])
    return s

  def get_rewards(self, player_id, obj):
    item = obj["item"]
    point = obj["points"]
    s = ""
    if(item != ""):
      self.players[player_id].items.append(item)
      s += "<br>You have aquired: " + self.dungeon["items"][item]["name"]
    if(point > 0):
      self.players[player_id].points += point
      s += "<br>You have gained " + str(point) + " point(s)"
      s += "<br>You have " + str(self.players[player_id].points) + " points"
    if(self.players[player_id].points >= self.dungeon["max_points"]):
      s += "<br><br>Congratulations! You have completed " + self.dungeon["name"]
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

def replace_placeholders(output, env):
  protocol = 'http'
  if 'HTTPS' in env or env['wsgi.url_scheme'] == 'https':
    protocol = 'https'
  output = output.replace("$SERVER_IP$", protocol)
  output = output.replace("$SERVER_PORT$", env['HTTP_HOST'])
  if("$GAMES$" in output):
    output = output.replace("$GAMES$", build_games_table_html())
  return output

def build_games_table_html():
  try:
    games_file = "./games/games.json"
    f = open(games_file, 'r')
    games = json.loads(f.read())
    f.close()
    html_output = '<div id="game-select" name="game-select">'
    for i in games["games"]:
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
      html_output += '<p>' + i["name"] + '</p>'
      html_output += '<p>Difficulty: ' + i["difficulty"] + '<br>'
      html_output += 'Length: ' + i["length"] + '</p>'
      html_output += '</div>'
      html_output += '</div>'
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

  if("session" not in cookies):
    player = Player("player")
    dungeon_file_path = "./games/" + game + "/" + game + ".json"
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
    content_length = int(env["CONTENT_LENGTH"])
    content = env["wsgi.input"].read(content_length)
    content = content.decode('utf-8')
    action = content.replace("action=", "")
    action = html.escape(action)
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
    pass
  return cookie

# uwsgi handler
def application(env, sr):
  global sessions

  resp_code = ""
  resp_headers = []

  # For more routes to be added later
  pages = {
    "/": "index"
  }

  path = env['PATH_INFO']
  path_split = path.split("/")

  try:

    if(env["REQUEST_METHOD"] == "GET"):
      if(path in pages):
        output = get_page(pages[path])
        output = replace_placeholders(output, env)
        resp_headers = [('Content-Type', 'text/html')]
        resp_code = '200 OK'
      else:
        output = get_page("404")
        resp_headers = [('Content-Type', 'text/html')]
        resp_code = '404 NOT FOUND'
      resp_headers.append(('Set-Cookie', '{}={}; Expires={}; Max-Age={}; Path=/'.format("session", "", 0, 0)))
    elif(env["REQUEST_METHOD"] == "POST"):
      if(len(path_split) > 2 and path_split[1] == "play"):
        output, resp_headers = handle_player_request(path_split[2], env)
        resp_code = '200 OK'
  except Exception as e:
    resp_code = '200 OK'
    resp_headers = [('Content-Type', 'text/html')]
    output = "An error has occurred."

  sr(resp_code, resp_headers)
  return output.encode("utf-8")
