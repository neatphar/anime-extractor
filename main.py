import wget
import json 
import requests
import subprocess
import urllib.parse as urlparse
from os import path, system
from bs4 import BeautifulSoup

HOME_URL = "https://www26.gogoanimes.tv/"
DOWNLOAD_URL = "https://gogo-stream.com/"
HEADERS = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.50',
}
VLC_PATHS = [
	'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
	'C:/Program Files (x86)/VLC/vlc.exe',
	'C:/Program Files/VideoLAN/VLC/vlc.exe',
	'C:/Program Files/VLC/vlc.exe',
]
session = requests.Session()

def list_all_anime(page=1, prev_anime_dict=[]):
	response = session.get(f"{HOME_URL}/anime-list.html?page={page}", headers=HEADERS).text
	soup = BeautifulSoup(response, 'html.parser')
	
	anime_list = soup.select("div.anime_list_body ul.listing li a")
	anime_dict = prev_anime_dict
	for anime in anime_list:
		anime_dict.append({"name": anime.text.strip(), "link": anime['href'].replace("category/", "")})
	
	pages_list = soup.select(".anime_name_pagination .pagination-list li")
	if len(pages_list) > 0 and pages_list[-1].get("class") is None:
		anime_dict = list_all_anime(page+1, anime_dict)
	return anime_dict

def search_anime(keyword, page=1, prev_anime_dict=[]):
	keyword = urlparse.quote_plus(keyword)
	response = session.get(f"{HOME_URL}/search.html?keyword={keyword}&page={page}", headers=HEADERS).text
	soup = BeautifulSoup(response, 'html.parser')
	
	anime_list = soup.select("div.last_episodes ul.items li p.name a")
	anime_dict = prev_anime_dict
	for anime in anime_list:
		anime_dict.append({"name": anime.text.strip(), "link": anime['href'].replace("category/", "")})
	
	pages_list = soup.select(".anime_name_pagination .pagination-list li")
	if len(pages_list) > 0 and pages_list[-1].get("class") is None:
		anime_dict = search_anime(keyword, page+1, anime_dict)
	return anime_dict

	
def get_latest_episode(anime):
	response = session.get(f"{HOME_URL}category/{anime['link']}", headers=HEADERS).text
	soup = BeautifulSoup(response, 'html.parser')

	ep_list = soup.select("#episode_page li a")
	if len(ep_list) == 0: return 0
	return int(ep_list[-1]['ep_end'])

def get_episode_id(anime, episode_num):
	response = session.get(f"{HOME_URL}{anime['link']}-episode-{episode_num}", headers=HEADERS).text
	soup = BeautifulSoup(response, 'html.parser')

	anime_vid = soup.select("#load_anime div.play-video iframe")
	if len(anime_vid) == 0: return None
	url_args = urlparse.urlparse(anime_vid[0]['src'])

	return urlparse.parse_qs(url_args.query)['id'][0]

def list_episode_links(episode_id):
	response = session.get(f"{DOWNLOAD_URL}download?id={episode_id}", headers=HEADERS).text
	soup = BeautifulSoup(response, 'html.parser')
	link_list = soup.select("#main div.content_c div.content_c_bg div.mirror_link")[0]
	link_list = link_list.select("div a")

	download_links_list = []
	for link in link_list:
		s = link.text
		s = s[s.find("(")+1 : s.find(")")]
		download_links_list.append({"name": s.replace(" - mp4", ""), "link": link['href']})
	
	return download_links_list

def write_json(data, filename): 
    with open(filename,'w') as f: 
        json.dump(data, f, indent=4) 

def read_json(filename, default=[]): 
	if not path.exists(filename): 
		write_json(default, filename)
		return default
	with open(filename) as json_file: 
		data = json.load(json_file) 
	return data
      
      
def toggle_fav(anime):
	temp = read_json("fav.json")
	if anime in temp:
		temp.remove(anime)
	else:
		temp.append(anime) 
	write_json(temp, 'fav.json')  


def check_the_logs(anime):
	temp = read_json("watched.json", default={})
	if anime['name'] not in temp:
		return []
	return temp[anime['name']]

def add_to_logs(anime, ep_num):
	temp = read_json("watched.json", default={})
	if anime['name'] not in temp:
		temp[anime['name']] = []

	if ep_num in temp[anime['name']]: return
	
	temp[anime['name']].append(ep_num)
	write_json(temp, 'watched.json')

def watch_on_vlc(link):
	for i in VLC_PATHS:
		if path.exists(i): 
			p = subprocess.Popen([i, link['link']])

def download_ep(link):
	saved_filename = urlparse.urlparse(link['link']).path.split("/")[-1]
	filename = wget.download(link['link'], out=saved_filename)
	print()
	input("Downloaded successfully! Press Enter to continue..")
	watch_on_vlc({'link': filename})

def copy_ep_link(link):
	system(f"echo \"{link['link']}\" | clip")

##### UI CODE #####

from consolemenu import *
from consolemenu.items import *
import time

print("""

              .__                                     ___.  ___.                 
_____    ____ |__| _____   ____      ________________ \_ |__\_ |__   ___________ 
\__  \  /    \|  |/     \_/ __ \    / ___\_  __ \__  \ | __ \| __ \_/ __ \_  __ \\
 / __ \|   |  \  |  Y Y  \  ___/   / /_/  >  | \// __ \| \_\ \ \_\ \  ___/|  | \/
(____  /___|  /__|__|_|  /\___  >  \___  /|__|  (____  /___  /___  /\___  >__|   
     \/     \/         \/     \/  /_____/            \/    \/    \/     \/       


								    BY: @neatphar
""")
time.sleep(2.5)

def watch_episode_menu(anime, latest_episode):
	episodes = list(range(1, latest_episode+1))
	for i in check_the_logs(anime):
		episodes[i] = str(episodes[i]) + " - WATCHED."
	episodes_menu = SelectionMenu(episodes, f"Anime Grabber - {anime['name']} Episodes.", exit_option_text="Return to Anime Menu..")
	episodes_menu.show()
	if episodes_menu.selected_option == latest_episode: return None
	ep = episodes_menu.selected_option + 1
	ep_id = get_episode_id(anime, ep)
	links = list_episode_links(ep_id)

	qualities_menu = SelectionMenu([i['name'] for i in links], f"Anime Grabber - {anime['name']} Episode {ep}.", exit_option_text="Return to Anime Menu..")
	qualities_menu.show()
	if qualities_menu.selected_option == len(links): return None
	quality = links[qualities_menu.selected_option]
	add_to_logs(anime, ep)

	watch_menu = ConsoleMenu(f"Anime Grabber - {anime['name']} Episode {ep} {quality['name']}.", exit_option_text="Return to Anime Menu..")
	item1_watch_menu = FunctionItem("Watch on VLC", watch_on_vlc, [quality])
	item2_watch_menu = FunctionItem("Download it and watch on VLC", download_ep, [quality])
	item3_watch_menu = FunctionItem("Copy the download link", copy_ep_link, [quality])
	watch_menu.append_item(item1_watch_menu)
	watch_menu.append_item(item2_watch_menu)
	watch_menu.append_item(item3_watch_menu)
	watch_menu.show()


def anime_menu(anime):
	if anime in read_json("fav.json"):
		is_in_fav = f"Remove {anime['name']} from"
	else:
		is_in_fav = f"Add {anime['name']} to"
	latest_episode = get_latest_episode(anime)
	options = [f"Watch an Episode 1~{latest_episode}", f"{is_in_fav} favourites"]
	anime_menu_obj = SelectionMenu(options, "Anime Grabber - " + anime['name'], exit_option_text="Return to Anime List..")
	anime_menu_obj.show()
	if anime_menu_obj.selected_option == 0: 
		watch_episode_menu(anime, latest_episode)
	elif anime_menu_obj.selected_option == 1: 
		toggle_fav(anime)
	elif anime_menu_obj.selected_option == 2: 
		return None
	anime_menu(anime)


def list_anime_menu(anime_list, title, updatable=False):
	subtitle = "No anime found!" if len(anime_list) == 0 else None
	search_results_menu = SelectionMenu([i['name'] for i in anime_list], f"Anime Grabber - {title}.", subtitle, exit_option_text="Return to Main Menu..")
	search_results_menu.show()
	if search_results_menu.selected_option == len(anime_list): return None
	anime = anime_list[search_results_menu.selected_option]
	anime_menu(anime)
	if updatable: anime_list = read_json("fav.json")
	list_anime_menu(anime_list, title)

def search_anime_menu():
	keyword = input("Enter a keyword: ")
	print("Please wait until the search results is gathered...")
	search_results = search_anime(keyword)
	list_anime_menu(search_results, f"Search Results for ({keyword})")


def list_all_anime_menu():
	print("Please wait until all the anime is gathered...")
	all_results = list_all_anime()
	list_anime_menu(all_results, f"All Anime Available")	

def list_fav_anime_menu():
	all_results = read_json("fav.json")
	list_anime_menu(all_results, f"All Favourite Anime", updatable=True)	

main_menu = ConsoleMenu("Anime Grabber - Main Menu")

search_anime_menu_item = FunctionItem("Search for an Anime", search_anime_menu)
list_fav_anime_menu_item = FunctionItem("List all Favourite Anime", list_fav_anime_menu)
list_all_anime_menu_item = FunctionItem("List all Anime", list_all_anime_menu)


main_menu.append_item(search_anime_menu_item)
main_menu.append_item(list_fav_anime_menu_item)
main_menu.append_item(list_all_anime_menu_item)

main_menu.show()
