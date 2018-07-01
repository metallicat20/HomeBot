import requests
from config import KODI


def update_library():
    output = requests.post(url='http://%s:%s@%s/jsonrpc' % (KODI['username'],KODI['password'],KODI['ip']),
                           json={"jsonrpc": "2.0", "method": "VideoLibrary.Scan", "id": "1"})
    if output.status_code == 200:
        return True
    else:
        return False


def clean_library():
    output = requests.post(url='http://%s:%s@%s/jsonrpc' % (KODI['username'],KODI['password'],KODI['ip']),
                           json={"jsonrpc": "2.0", "method": "VideoLibrary.Clean", "id": "1"})
    if output.status_code == 200:
        return True
    else:
        return False