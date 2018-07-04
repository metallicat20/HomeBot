import config
import telebot
import re
from kodi import update_library, clean_library
from screenshot import get_screenshot
from utorrentapi import UTorrentAPI, TorrentInfo, TorrentListInfo

bot = telebot.TeleBot(config.TOKEN)
apiclient = UTorrentAPI(config.URL, config.USER, config.PASSWORD)

@bot.message_handler(content_types=["text"])
def parse_commands(message):
    chat_id = message.chat.id
    sender_id = message.from_user.id
    sender_username = message.from_user.username
    if sender_id not in config.ALLOWED_USERS:
        bot.send_message(chat_id, "Unauthorized user")
        print(sender_id,sender_username)
    else:
        message_text = message.text
        if message_text == ("/list"):
            message = list_torrents(chat_id)
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
                bot.send_message(chat_id, "Cleaning..")
            else:
                bot.send_message(chat_id, "Unknown error")
        elif message_text == "/screenshot":
            sct = get_screenshot()
            bot.send_photo(chat_id, open(sct, 'rb'))


def start_torrent_from_magnet(magnet, chat_id):
    filename,short_filename = name_from_magnet(magnet)
    parsed_dirs = parse_dirs(short_filename)
    if is_series(filename):
        if parsed_dirs['found']:
            chosen_dir = parsed_dirs['chosen_dir']
        else:
            chosen_dir = parsed_dirs['SORT_SERIES']
    else:
        chosen_dir = parsed_dirs['SORT_MOVIES']
    result = apiclient.add_url_to_dir(magnet, chosen_dir)
    if result == []:
        bot.send_message(chat_id, "Failed to add, wrong magnet link?")
    elif result['build']:
        bot.send_message(chat_id, "Downloading to %s" % (apiclient._get_dirs()[chosen_dir]))
    else:
        bot.send_message(chat_id, "Unknown error")


def parse_dirs(filename):
    found = False
    chosen_dir = None
    dirs = apiclient._get_dirs()
    for index, dir in enumerate(dirs):
        if filename in dir:
            chosen_dir = index
            found = True
        elif "#SORT_SERIES" in dir:
            SORT_SERIES = index
        elif "#SORT_MOVIES" in dir:
            SORT_MOVIES = index
    parsed_dirs = { "found": found,
                   "chosen_dir": chosen_dir,
                   "SORT_SERIES": SORT_SERIES,
                   "SORT_MOVIES": SORT_MOVIES }
    return parsed_dirs


def list_torrents(chat_id):
    message = ""
    tor_list_text = []
    data = apiclient.get_list()
    tor_list = TorrentListInfo(data)
    message = ""
    for tor in tor_list.torrents:
        message+=(tor.name + " - " + str(tor.percent_progress/10) + "%\n\n")
    return message



def name_from_magnet(magnet):
    magnet_split = magnet.split("&")
    for x in magnet_split:
        if x.startswith("dn="):
            filename = x[3:]
    if is_series(filename):
        filename_list = filename.split('.')
        if filename_list[0].lower() == "the":
            return [filename,filename_list[1]]
        else:
            return [filename,filename_list[0]]
    else:
        return [filename,filename]

def is_series(filename):
    capitals = re.compile("S\d\dE\d\d")
    lower = re.compile("s\d\de\d\d")
    if re.search(capitals, filename) or re.search(lower, filename):
        return True
    else:
        return False


if __name__ == '__main__':
    bot.polling(none_stop=True)