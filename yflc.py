import fuckit
from YHandler import *
import requests
import xml.etree.ElementTree as ET
import json

class Team(): 
    def __init__(self,players):
        self.players = players

url = "https://query.yahooapis.com/v1/public/yql/vk/vk?diagnostics=true"
        
r = requests.get(url)
print r.text
tree = ET.fromstring(r.text.encode('ascii', 'ignore'))
print tree
