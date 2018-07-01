import config
import telebot
import execnet
from uTorrent_Client.app.utorrentapi import UTorrentAPI, TorrentInfo, TorrentListInfo

bot = telebot.TeleBot(config.TOKEN)
apiclient = UTorrentAPI(config.URL, config.USER, config.PASSWORD)

@bot.message_handler(content_types=["text"])
def parse_commands(message):
    return message

