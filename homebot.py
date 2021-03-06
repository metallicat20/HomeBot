import config
import telebot
import re
from kodi import update_library, clean_library
from screenshot import get_screenshot
from utorrentapi import UTorrentAPI, TorrentInfo, TorrentListInfo
from os.path import isfile, isdir
from os import stat, mkdir, remove
from distutils.dir_util import copy_tree
from shutil import copyfile
from imdb import IMDb
from eztv_parse import *
from sys import exc_info

bot = telebot.TeleBot(config.TOKEN)
apiclient = UTorrentAPI(config.URL, config.USER, config.PASSWORD)
ia = IMDb()


@bot.message_handler(content_types=["text"])
def parse_commands(message):
    global chat_id
    chat_id = message.chat.id
    sender_id = message.from_user.id
    sender_username = message.from_user.username
    if sender_id not in config.ALLOWED_USERS:
        bot.send_message(chat_id, "Unauthorized user")
        print(sender_id,sender_username)
    else:
        message_text = message.text
        if message_text == "/list":
            message = list_torrents()
            if message == "":
                bot.send_message(chat_id, "No torrents in progress")
            else:
                bot.send_message(chat_id, message)
        elif message_text.startswith("/magnet"):
            try:
                start_torrent_from_magnet(message_text.split()[1], chat_id)
            except:
                bot.send_message(chat_id, "Enter a magnet link")
        elif message_text == "/update_library":
            output = update_library()
            if output:
                bot.send_message(chat_id, "Updating..")
            else:
                bot.send_message(chat_id, "Unknown error")
        elif message_text == "/clean_library":
            output = clean_library()
            if output:
                bot.send_message(chat_id, "Cleaning complete")
            else:
                bot.send_message(chat_id, "Unknown error")
        elif message_text == "/screenshot":
            sct = get_screenshot()
            bot.send_photo(chat_id, open(sct, 'rb'))
            remove("monitor-1.png")
        elif message_text == "/copy_movies":
            copy_movies()
        elif message_text == "/purge_all_torrents":
            purge_all_torrents()
        elif message_text == "/parse_eztv":
            parse_eztv()
        elif message_text == "/stop_all_torrents":
            stop_all_torrents()
            send_message("All torrents stopped")
        elif message_text == "/remove_all_torrents":
            remove_all_torrents()
            send_message("All torrents removed")


def send_message(message):
    bot.send_message(chat_id, message)


def start_torrent_from_magnet(magnet, chat_id):
    filename, short_filename = name_from_magnet(magnet)
    parsed_dirs = parse_dirs(short_filename)
    if is_series(filename):
        if parsed_dirs['found']:
            chosen_dir = parsed_dirs['chosen_dir']
        else:
            chosen_dir = parsed_dirs['SORT_SERIES']
    else:
        chosen_dir = parsed_dirs['SORT_MOVIES']
    result = apiclient.add_url_to_dir(magnet, chosen_dir)
    if not result:
        bot.send_message(chat_id, "Failed to add, wrong magnet link?")
    elif result['build']:
        bot.send_message(chat_id, "Downloading to %s" % (apiclient.get_dirs()[chosen_dir]))
    else:
        bot.send_message(chat_id, "Unknown error")


def parse_dirs(filename):
    sort_series, sort_movies = None, None
    found = False
    chosen_dir = None
    dirs = apiclient.get_dirs()
    for index, path in enumerate(dirs):
        if filename in path:
            chosen_dir = index
            found = True
        elif "#SORT_SERIES" in path:
            sort_series = index
        elif "#SORT_MOVIES" in path:
            sort_movies = index
    parsed_dirs = {"found": found,
                   "chosen_dir": chosen_dir,
                   "SORT_SERIES": sort_series,
                   "SORT_MOVIES": sort_movies}
    return parsed_dirs


def list_torrents():
    message = ""
    data = apiclient.get_list()
    tor_list = TorrentListInfo(data)
    for tor in tor_list.torrents:
        message += (tor.name + " - " + str(tor.percent_progress/10) + "%\n\n")
    return message


def name_from_magnet(magnet):
    filename = None
    magnet_split = magnet.split("&")
    for x in magnet_split:
        if x.startswith("dn="):
            filename = x[3:]
    if is_series(filename):
        filename_list = filename.split('.')
        if filename_list[0].lower() == "the":
            return [filename, filename_list[1]]
        else:
            return [filename, filename_list[0]]
    else:
        return [filename, filename]


def is_series(filename):
    capitals = re.compile("S\d\dE\d\d")
    lower = re.compile("s\d\de\d\d")
    if re.search(capitals, filename) or re.search(lower, filename):
        return True
    else:
        return False


def _create_list_of_movie_tors():
    data = apiclient.get_list()
    tor_list = TorrentListInfo(data)
    movies = []
    for tor in tor_list.torrents:
        if config.MOVIES_FOLDER in tor.target:
            movies.append(tor)
    return movies


def _is_folder(target):
    if isdir(target):
        return True
    elif isfile(target):
        return False


def search_imdb(movie):
    try:
        movie = ia.search_movie(movie)[0]
    except IndexError:
        return [None, None, None]
    ia.update(movie)
    genres = movie['genres']
    if 'Documentary' in genres and 'Comedy' in genres:
        genre = 'standup'
        year = str(movie['year'])
    else:
        genre = 'movie'
        year = None
    return [str(movie), genre, year]


def create_dir(full_path):
    try:
        stat(full_path)
    except FileNotFoundError:
        mkdir(full_path)


def normalize_movie_name(movie_name):
    if ' - ' in movie_name:
        movie_name = movie_name.split(' - ')[1]
    movie_name = re.split("[19\,20\,(]+", movie_name.replace('.', ' '))[0].strip()
    return movie_name


def copy_movies():
    movie_list = _create_list_of_movie_tors()
    send_message("Found %d movies" % (len(movie_list)))
    for movie in movie_list:
        movie_name = normalize_movie_name(movie.name)
        print(movie_name)
        send_message("Trying to process %s" % movie.name)
        dir_name, genre, year = search_imdb(movie_name)
        if not dir_name:
            send_message("Could not find this movie in IMDb")
            continue
        elif genre == 'movie':
            full_path = "\\".join([config.MOVIES_FOLDER, dir_name])
        elif genre == 'standup':
            comic, show = [x.strip() for x in dir_name.split(':')]
            comic_path = "\\".join([config.STANDUP_FOLDER, comic])
            full_path = "\\".join([config.STANDUP_FOLDER, comic, year + " - " + show])
            create_dir(comic_path)
        send_message('It was identified as a %s named "%s" and it will be copied to %s' % (genre, dir_name, full_path))
        create_dir(full_path)
        if movie.target.endswith(movie.name):
            copy_tree(movie.target, full_path, update=True)
        else:
            copyfile("\\".join([movie.target, movie.name]), '\\'.join([full_path, movie.name]))
        send_message("Copied")
        send_message("========")


def purge_all_torrents():
    torrents = apiclient.get_list()
    tor_list = TorrentListInfo(torrents)
    for torrent in tor_list.torrents:
        apiclient.removedata(torrent.hash)


def stop_all_torrents():
    torrents = apiclient.get_list()
    tor_list = TorrentListInfo(torrents)
    for torrent in tor_list.torrents:
        apiclient.stop(torrent.hash)


def remove_all_torrents():
    torrents = apiclient.get_list()
    tor_list = TorrentListInfo(torrents)
    for torrent in tor_list.torrents:
        apiclient.remove(torrent.hash)


def parse_eztv():
    send_message("Parsing..")
    feed = get_feed()
    candidates = get_all_candidates(feed, shows)
    all_new_episodes = get_all_new_episodes(shows, candidates)
    list_to_download = create_list_to_download(all_new_episodes)
    if not list_to_download:
        send_message("No new episodes found")
    for episode in list_to_download:
        parsed_dirs = parse_dirs(episode['show'])
        if parsed_dirs['found']:
            chosen_dir = parsed_dirs['chosen_dir']
        else:
            chosen_dir = parsed_dirs['SORT_SERIES']
        result = apiclient.add_url_to_dir(episode['magnet'], chosen_dir)
        if not result:
            send_message("Failed to add %s, wrong magnet link?" % (episode['name']))
        elif result['build']:
            send_message("Downloading %s to %s" % (episode['name'], apiclient.get_dirs()[chosen_dir]))
        else:
            send_message("Unknown error while downloading %s" % (episode['name']))


if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except:
        print(exc_info()[0])
        pass
