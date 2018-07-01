from mss import mss

def get_screenshot():
    with mss() as sct:
        #sct.compression_level = 1
        return sct.shot()