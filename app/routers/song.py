from fastapi import Body, Depends, status, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer
from db.supabase import create_supabase_client
from app.dbmodels import User
from app.models import SpotifyAdd, ManualAdd, SearchAdd
from dotenv import load_dotenv
import os
from lyricsgenius import Genius
from geniusdotpy.genius import Genius as GeniusSearch 
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from jamdict import Jamdict
import jamdict_data
import re
import fugashi
import pykakasi
import json
from app.routers.auth import get_current_user, get_current_session
import boto3
import random

router = APIRouter(prefix="/song", tags=["song"])
load_dotenv()
stage = os.getenv("STAGE")
sqs_url = os.getenv("QUEUE_URL")
oauth2_scheme = (
    OAuth2PasswordBearer(tokenUrl="/auth/token")
    if stage == "local"
    else OAuth2PasswordBearer(tokenUrl="/dev/auth/token")
)


cid = os.getenv("SPOTIFY_CLIENT_ID")
secret = os.getenv("SPOTIFY_CLIENT_SECRET")
genius_token = os.getenv("GENIUS_ACCESS_TOKEN")

#initialize genius related objects
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
]

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
genius = Genius(genius_token, user_agent=random.choice(USER_AGENTS))
genius_search = GeniusSearch(client_access_token=genius_token)
genius_search.excluded_terms = ["Romanized", "English", "Translation", "Türkçe", "Português"]

#initialize tokenizing/japanese processing objects
jam = Jamdict(memory_mode=True)
tagger = fugashi.Tagger()
kakasi = pykakasi.kakasi()
kakasi.setMode("J", "H")
kakasi.setMode("K", "H")
conv = kakasi.getConverter()

CONST_KANJI = r'[㐀-䶵一-鿋豈-頻]'
HIRAGANA_FULL = r'[ぁ-ゟ]'
KATAKANA_FULL = r'[゠-ヿ]'
ALL_JAPANESE = f'{CONST_KANJI}|{HIRAGANA_FULL}|{KATAKANA_FULL}'

#initialize AWS objects
aws_session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_SERVER_PUBLIC_KEY"),
    aws_secret_access_key=os.getenv("AWS_SERVER_SECRET_KEY"),
    region_name="us-east-2"
)

#load kanji data
def load_kanji_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
kanji_data = load_kanji_data('kanji.json')
supabase = create_supabase_client()

#gets the song from a given URI, returns artist and song of the track.
async def get_song_from_spotify(uri):
    track = sp.track(uri, market="JP")
    artist = track['artists'][0]['name']
    song = track['name']
    image = track['album']['images'][0]['url']
    return artist, song, image

def get_image_from_spotify(artist, title):
    # print("Artist: ", artist)
    # print("Title: ", title)
    query = f"track:{title} artist:{artist}"
    track = sp.search(q=query, limit=1, offset=0, type="track", market="JP")
    return track['tracks']['items'][0]['album']['images'][0]['url']

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

def delete_before_line_break(s, artist):
    # Extract Japanese characters from artist name
    artist_japanese = ''.join(re.findall(ALL_JAPANESE, artist))
    
    # Find the position of the first and second line breaks
    first_break = s.find('\n')
    if first_break != -1:
        first_line = s[:first_break]  # Get the first line to check
        
        # Check if 'lyrics' appears in the first line and remove up to 'lyrics'
        lyrics_pos = first_line.lower().find('lyrics')
        if lyrics_pos != -1:
            s = s[lyrics_pos + len('lyrics'):]  # Remove text up to and including 'lyrics'
            first_break = s.find('\n')  # Recalculate first line break after 'lyrics' removal
        
        # If artist's Japanese name is in the first line, proceed to remove it
        elif artist_japanese in first_line:
            second_break = s.find('\n', first_break + 1)
            if second_break != -1:
                return s[second_break + 1:]
    return s  # If conditions aren't met, return the original string


#clean up common excess data brought in using the API.
def clean_lyrics(lyrics, artist):
    lyrics = delete_before_line_break(lyrics, artist)
    # Remove "You might also like" text only
    lyrics = re.sub(r'You might also like', '', lyrics)
    # Remove "number followed by Embed"
    lyrics = re.sub(r'\d+Embed', '', lyrics)
    lyrics = re.sub(r'Embed', '', lyrics)
    if bool(re.search(ALL_JAPANESE, lyrics)):
        # print("Cleaned lyrics", lyrics)
        return lyrics
    else:
        return None


#specifically used to return the list of kanji in the lyrics
def extract_unicode_block(unicode_block, string):
	''' extracts and returns all texts from a unicode block from string argument.
		Note that you must use the unicode blocks defined above, or patterns of similar form '''
	return re.findall( unicode_block, string)

#gets the desired data about a particular kanji contained in the lyrics.
def get_kanji_data(kanji):
    if kanji in kanji_data:
        data = kanji_data[kanji]
        radicals = jam.krad[kanji]
        sending_data = {
            "jlpt_new": data["jlpt_new"],
            "meanings": data["meanings"],
            "readings_on": data["readings_on"],
            "readings_kun": data["readings_kun"],
            "radicals": radicals
        }
        return sending_data
    else:
        return None
    
# gets the data for all kanji in the lyrics
def get_all_kanji_data(kanji_list):
    all_kanji_data = {}
    for kanji in kanji_list:
        data = get_kanji_data(kanji)
        all_kanji_data[kanji] = data
    return all_kanji_data


def create_word_return(idseq):
    word_result = jam.lookup("id#"+idseq).to_dict()['entries'][0]
    word = word_result['kanji'][0]['text']
    furigana = word_result['kana'][0]['text']
    romaji = kakasi.convert(furigana)[0]["hepburn"]
    word_properties = []
    # all definitions availabile for this ID
    for sense in word_result['senses']:
        pos = sense['pos'] #part of speech(es), LIST
        definition = [] #isolating the defintions, LIST
        for sense_gloss in sense["SenseGloss"]:
            definition.append(sense_gloss["text"])
        word_property = {
            "pos": pos,
            "definition": definition
        }
        word_properties.append(word_property)
        
    result = {
        "word": word,
        "furigana" : furigana,
        "romaji": romaji,
        "definitions": word_properties
    }
    
    return result
    

#need a route which takes in a spotify uri and adds the processed song to the database.
@router.post("/add-song-spot")
async def add_song_spot(spotifyItem: SpotifyAdd = None, user: User = Depends(get_current_user)):
    uri = spotifyItem.uri
    refresh_token = spotifyItem.refresh_token
    access_token = spotifyItem.access_token
    if spotifyItem is None or user is None:
        return {"message": "Missing information. Please try again."}
    artist, song, image = await get_song_from_spotify(uri)
    # Check if the song already exists in the user's personal song table
    temp_artist = '%'+artist+'%'
    temp_song = '%'+song+'%'
    in_my_table = supabase.table("Song").select(count="exact").eq("title", song).eq("artist", artist).eq("id", user.id).execute().count
    if in_my_table:
        return {"message": "Song already in database for this user."}

    # Check if the song exists in the global SongData table
    # in_table = supabase.table("SongData").select(count="exact").eq("title", song).eq("artist", artist).execute().count
    
    in_table = supabase.table("SongData").select(count="exact").ilike("title", temp_song).ilike("artist", temp_artist).execute()
    # print("Artist", artist)
    # print("Song", song)
    # print("In table", in_table)
    if not in_table.count:
        # Retrieve song data if it exists
        lyrics = get_lyrics(artist, song)
        
        if lyrics is None:
            return {"message": "No lyrics found for this song."}

        # Preparing for SQS send and getting Kanji
        cleaned_lyrics = clean_lyrics(lyrics, artist)
        if cleaned_lyrics is None:
            return {"message": "No Japanese lyrics found for this song. Try searching for the song manually."}
        kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
        if not kanji_list:
            return {"message": "Error! Seems like we can't get the lyrics from the link. Try searching for the song manually."}
        all_kanji_data = get_all_kanji_data(kanji_list)

        # Insert the song data into the global database only if it doesn't already exist
        try:
            response = supabase.table("SongData").insert({
            "title": song, 
            "artist": artist, 
            "lyrics": None, 
            "hiragana_lyrics": None, 
            "word_mapping": None, 
            "kanji_data": all_kanji_data, 
            "image_url": image
            }).execute()
        except Exception as e:
            return {"message": f"An error occurred while inserting the song data: {str(e)}"}
        
        # send to SQS
        body = {
            "song": song,
            "artist": artist,
            "cleaned_lyrics": cleaned_lyrics,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        sqs = aws_session.resource('sqs')
        queue = sqs.Queue(sqs_url)
        queue.send_message(
            MessageBody=json.dumps(body)
        )

    # Song has been successfully added to the global database, now add for the specific user
    response = supabase.table("Song").insert({"title": song, "artist": artist, "id": user.id}).execute()
    # print(response)
    return {"message": "Song added successfully.", "status": "success"}


#need a route which takes in artist and title, searches, and adds the processed song to the database.
@router.post("/add-song-search")
async def add_song_search(searchItem: SearchAdd = None, user: User = Depends(get_current_user)):
    refresh_token = searchItem.refresh_token
    access_token = searchItem.access_token
    artist = searchItem.artist
    title = searchItem.title
    if searchItem is None or user is None:
        return {"message": "Missing information. Please try again."}
    # Check if the song already exists in the user's personal song table
    in_my_table = supabase.table("Song").select(count="exact").eq("title", title).eq("artist", artist).eq("id", user.id).execute().count
    if in_my_table:
        return {"message": "Song already in database for this user."}

    # Check if the song exists in the global SongData table
    in_table = supabase.table("SongData").select(count="exact").eq("title", title).eq("artist", artist).execute().count
    if not in_table:
        # Retrieve song data if it exists
        lyrics = get_lyrics(artist, title)
        
        if lyrics is None:
            return {"message": "No lyrics found for this song."}
        
        image_url = get_image_from_spotify(artist, title)

        # Preparing for SQS send and getting Kanji
        cleaned_lyrics = clean_lyrics(lyrics, artist)
        if cleaned_lyrics is None:
            return {"message": "No Japanese lyrics found for this song. Paste the lyrics in."}
        kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
        if not kanji_list:
            return {"message": "Error! Seems like we can't get the lyrics from the search. Paste the lyrics in."}
        all_kanji_data = get_all_kanji_data(kanji_list)

        # Insert the song data into the global database only if it doesn't already exist        
        try:
            response = supabase.table("SongData").insert({
            "title": title, 
            "artist": artist, 
            "lyrics": None, 
            "hiragana_lyrics": None, 
            "word_mapping": None, 
            "kanji_data": all_kanji_data, 
            "image_url": image_url
            }).execute()
        except Exception as e:
            return {"message": f"An error occurred while inserting the song data: {str(e)}"}
        
        # send to SQS
        body = {
            "song": title,
            "artist": artist,
            "cleaned_lyrics": cleaned_lyrics,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        sqs = aws_session.resource('sqs')
        queue = sqs.Queue(sqs_url)
        queue.send_message(
            MessageBody=json.dumps(body)
        )

    # Song has been successfully added to the global database, now add for the specific user
    response = supabase.table("Song").insert({"title": title, "artist": artist, "id": user.id}).execute()
    # print(response)
    return {"message": "Song added successfully.", "status": "success"}
  
    
   
#need a route which takes in artist, song and, lyrics, processes the text, and adds the processed song to the database
@router.post("/add-song-manual")
async def add_song_manual(manual: ManualAdd, user: User = Depends(get_current_user)):
    title = manual.title
    artist = manual.artist
    lyrics = manual.lyrics
    refresh_token = manual.refresh_token
    access_token = manual.access_token
    if manual is None or user is None:
        return {"message": "Missing information. Please try again."}
    in_my_table = supabase.table("Song").select(count="exact").eq("title", title).eq("artist", artist).eq("id", user.id).execute().count
    if in_my_table > 0:
        return {"message": "Song already in database."}
    
    in_table = supabase.table("SongData").select(count="exact").eq("title", title).eq("artist", artist).execute().count
    if not in_table:
        # song not in global database
        image_url = get_image_from_spotify(artist, title)
        cleaned_lyrics = clean_lyrics(lyrics, artist)
        if cleaned_lyrics is None:
            return {"message": "No Japanese lyrics found here. Check your input."}
        kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
        if not kanji_list:
            return {"message": "Error! Check your input. No Japanese found in the lyrics."}
        all_kanji_data = get_all_kanji_data(kanji_list)
        
        try:
            response = supabase.table("SongData").insert({
            "title": title, 
            "artist": artist, 
            "lyrics": None, 
            "hiragana_lyrics": None, 
            "word_mapping": None, 
            "kanji_data": all_kanji_data, 
            "image_url": image_url
            }).execute()
        except Exception as e:
            return {"message": f"An error occurred while inserting the song data: {str(e)}"}
        
        # call long running SQS to process tokenized lines and add it to the database
        # send to SQS
        body = {
            "song": title,
            "artist": artist,
            "cleaned_lyrics": cleaned_lyrics,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        sqs = aws_session.resource('sqs')
        queue = sqs.Queue(sqs_url)
        queue.send_message(
            MessageBody=json.dumps(body)
        )
    response = supabase.table("Song").insert({"title": title, "artist": artist, "id": user.id}).execute()
    return response

#need a route which provides a desired song from the database when requested. provides the lyrics and the mapping of word to idseq and kanji dictionary.
@router.get("/get-song")
async def get_song(title: str = None, artist: str = None, user: User = Depends(get_current_user)):
    if title is None or artist is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        # have access to title, artist, uuid
        response = supabase.table("SongData").select("lyrics, hiragana_lyrics, word_mapping, kanji_data").eq("title", title).eq("artist", artist).execute()
        if response.count == 0:
            return {"message": "Song not found in database."}
        else:
            return response.data[0]

#need a route which looks up a particular idseq in jamdict.
@router.get("/get-word")
async def get_word(idseq: str = None, user: User = Depends(get_current_user)): #not sure about how to define
    if user is None or idseq is None:
        return {"message": "User not found."}
    if idseq:
        result = create_word_return(idseq)
        
        return result
    else:
        return {"message": "No idseq provided"}
    
#need a route which provides the hiragana for a given song. MAYBE NOT
@router.get("/get-hiragana")
async def get_hiragana(title: str = None, artist: str = None, user: User = Depends(get_current_user)):
    if title is None or artist is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        response = supabase.table("SongData").select("hiragana_lyrics").eq("title", title).eq("artist", artist).execute()
        if response.count == 0:
            return {"message": "Song not found in database."}
        else:
            return response.data[0]

#need a route which provides a list of songs from the database when requested for the particular user.
@router.get("/get-songs")
async def get_songs(user: User = Depends(get_current_user)):
    response = supabase.table("Song").select("title, artist, SongData(image_url)").eq("id", user.id).execute()
    if not response.data :
        return {"message": "No songs found in database."}
    else:
        return response.data


@router.get("/get-global-songs")
async def get_global_songs(limit: int = 50, offset: int = 0, user: User = Depends(get_current_user)):
    if limit == None or offset == None:
        return {"message": "Missing information. Please try again."}
    else:
        response = supabase.table("Song").select("title, artist, SongData(image_url)").limit(limit).offset(offset).order("created_at", desc=True).execute()
        return response.data
    
#TODO: add a get image url function that takes title and artist and distinctly returns an image url.
@router.get("/get-image")
async def get_image(title: str = None, artist: str = None, user: User = Depends(get_current_user)):
    if title is None or artist is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        response = supabase.table("SongData").select("image_url").eq("title", title).eq("artist", artist).limit(1).execute()
        if response.count == 0:
            return {"message": "Song not found in database."}
        else:
            return response.data[0]