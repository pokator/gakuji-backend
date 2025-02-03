from lyricsgenius import Genius
from geniusdotpy.genius import Genius as GeniusSearch 

genius = Genius("8vBphHXB7yhgAb7l1t6pSgDF4pp8KpTfzSvKiRGSeZ0g3gLel39ZJ21Tyjhw43uC", user_agent="Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.3")

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
        
    # print(lyrics)
    return lyrics

artist = "Yoko Takahashi"
title = "魂のルフラン"

r = get_lyrics(artist, title)
print(r)