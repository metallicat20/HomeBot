import feedparser
import re
from os import listdir
from os.path import isfile, isdir, join
from bot import parse_dirs
from utorrentapi import UTorrentAPI
from config import *

shows = [ item for item in listdir(SERIES_FOLDER) if isdir(join(SERIES_FOLDER, item)) ]
feed = feedparser.parse("https://eztv.ag/ezrss.xml")
apiclient = UTorrentAPI(URL, USER, PASSWORD)


def find_candidate_episodes_for_show(show):
    episodes = []
    for entry in feed.entries:
        if show.lower().replace("'","") in entry.title.lower().replace("'",""):
            episodes.append(entry)
    return episodes


def get_all_candidates(shows):
    candidates = {}
    for show in shows:
        candidates[show] = find_candidate_episodes_for_show(show)
    return candidates


def get_season_from_filename(filename):
    pattern = re.compile("S\d\dE\d\d")
    m = re.search(pattern, filename)
    return m.group(0)[:3]


def get_episode_from_filename(filename):
    pattern = re.compile("S\d\dE\d\d")
    m = re.search(pattern, filename)
    return m.group(0)


def path_to_season(series, show, season):
    return "\\".join([series,show,season])


def get_videos_in_dir(dir):
    videos = []
    files = [f for f in listdir(dir) if isfile(join(dir, f))]
    videos = [file for file in files if file[-3:] in VIDEO_EXTENSIONS]
    return videos


def candidate_exists(show, candidate):
    found = False
    season = get_season_from_filename(candidate.title)
    path = path_to_season(SERIES_FOLDER, show, season)
    videos = get_videos_in_dir(path)
    for video in videos:
        if get_episode_from_filename(video) == get_episode_from_filename(candidate.title):
            found = True
    return found


def create_episode_json(candidate, show):
    episode = {'name': candidate.title,
               'magnet': candidate.torrent_magneturi,
               'filename': candidate.torrent_filename,
               'show': show }
    return episode


def find_new_episodes_for_show(show, candidates):
    new_episodes = {}
    for candidate in candidates[show]:
        episode = get_episode_from_filename(candidate.title)
        if not candidate_exists(show, candidate):
            if not episode in new_episodes:
                new_episodes[episode] = []
            new_episodes[episode].append(create_episode_json(candidate, show))
    return new_episodes


def get_all_new_episodes(shows, candidates):
    all_new_episodes = {}
    for show in shows:
        new_episodes = find_new_episodes_for_show(show, candidates)
        if not new_episodes == {}:
            all_new_episodes[show] = new_episodes
    return all_new_episodes


def find_highest_quality(new_episodes):
    found = False
    for quality in QUALITIES:
        for episode in new_episodes:
            if quality in episode['name']:
                found = True
                return episode
    if not found:
        return new_episodes[0]


def create_list_to_download(all_new_episodes):
    list_to_download = []
    for show in all_new_episodes.keys():
        for episode in all_new_episodes[show].keys():
            list_to_download.append(find_highest_quality(all_new_episodes[show][episode]))
    return list_to_download


def main():
    candidates = get_all_candidates(shows)
    all_new_episodes = get_all_new_episodes(shows, candidates)
    list_to_download = create_list_to_download(all_new_episodes)
    for episode in list_to_download:
        parsed_dirs = parse_dirs(episode['show'])
        if parsed_dirs['found']:
            chosen_dir = parsed_dirs['chosen_dir']
        else:
            chosen_dir = parsed_dirs['SORT_SERIES']
        result = apiclient.add_url_to_dir(episode['magnet'], chosen_dir)
        if result == []:
            print("Failed to add %s, wrong magnet link?" % (episode['name']))
        elif result['build']:
            print("Downloading %s to %s" % (episode['name'],apiclient._get_dirs()[chosen_dir]))
        else:
            print("Unknown error while downloading %s" % (episode['name']))

if __name__ == '__main__':
    main()