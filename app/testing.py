from lyricsgenius import Genius
from geniusdotpy.genius import Genius as GeniusSearch 
import random


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
]

proxy_list_http = [
    "http://51.222.32.193:3128",
    "http://63.143.57.115:80",
    "http://135.148.149.92:3128",
]

proxy_list_https = [
    "https://191.37.33.38:42999",
    "https://62.60.229.100:3128",
    "https://103.90.234.132:8888"
]
proxy = {
    "http": random.choice(proxy_list_http)
}
genius = Genius("8vBphHXB7yhgAb7l1t6pSgDF4pp8KpTfzSvKiRGSeZ0g3gLel39ZJ21Tyjhw43uC", user_agent=random.choice(USER_AGENTS), proxy=proxy)
genius_search = GeniusSearch(client_access_token="8vBphHXB7yhgAb7l1t6pSgDF4pp8KpTfzSvKiRGSeZ0g3gLel39ZJ21Tyjhw43uC")
genius_search.excluded_terms = ["Romanized", "English", "Translation", "Türkçe", "Português"]



def get_lyrics(artist, title):
    # print("Artist: ", artist)
    # print("Title: ", title)
    songs = genius_search.search(title)
    # print("Songs with this artist and title: ", songs)
    # pipe to a file
    # with open("songs.json", "w") as f:
    #     f.write(str(songs))
    id = None
    for track in songs:
        print("Track: ", track)
        if artist in track.artist.name:
            id = track.id
            url = track.url
            break
    lyrics = None
    if id is not None:
        other_source = genius.search_song(song_id=id)
        # print("Primary source: ", other_source)
        lyrics = other_source.lyrics  
    else:
        #desperate times...
        other_source = genius.search_song(title, artist)
        # print("Other source: ", other_source)
        lyrics = other_source.lyrics
        
    if url is not None:
        other_source = genius.web_page(url)
        print("Web page: ", other_source)
    # print(lyrics)
    return lyrics

artist = "Yoko Takahashi"
title = "魂のルフラン"

r = get_lyrics(artist, title)
print(r)