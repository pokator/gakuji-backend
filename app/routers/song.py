from fastapi import Body, Depends, status, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.supabase import create_supabase_client
from app.dbmodels import User
from app.models import Token, CreateUser, SpotifyAdd, ManualAdd
from dotenv import load_dotenv
import os
from typing import Union
from lyricsgenius import Genius
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

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
genius = Genius(genius_token)
jam = Jamdict(memory_mode=True)
tagger = fugashi.Tagger()
kakasi = pykakasi.kakasi()
kakasi.setMode("J", "H")
kakasi.setMode("K", "H")
conv = kakasi.getConverter()
CONST_KANJI = r'[㐀-䶵一-鿋豈-頻]'
aws_session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_SERVER_PUBLIC_KEY"),
    aws_secret_access_key=os.getenv("AWS_SERVER_SECRET_KEY"),
    region_name="us-east-2"
)

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

def get_image(artist, title):
    query = f"track:{title} artist:{artist}"
    track = sp.search(q=query, limit=1, offset=0, type="track", market="JP")
    return track['tracks']['items'][0]['album']['images'][0]['url']


# artist, song = get_song("https://open.spotify.com/track/3kUWZiVYJ4YQOl0u7Y1Og8?si=66716aec7c7447e0")

def delete_before_line_break(s):
    index = s.find('\n')  # Find the position of the first line break
    if index != -1:  # If a line break is found
        return s[index + 2:]  # Slice the string from the position after the line break, and roll over to the next line
    else:
        return s  # If no line break is found, return the original string

#clean up common excess data brought in using the API.
def clean_lyrics(lyrics):
    lyrics = delete_before_line_break(lyrics)
    # Remove "You might also like" text only
    lyrics = re.sub(r'You might also like', '', lyrics)
    # Remove "number followed by Embed"
    lyrics = re.sub(r'\d+Embed', '', lyrics)
    lyrics = re.sub(r'Embed', '', lyrics)
    return lyrics


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
    in_my_table = supabase.table("Song").select(count="exact").eq("title", song).eq("artist", artist).eq("id", user.id).execute().count
    if in_my_table:
        return {"message": "Song already in database for this user."}

    # Check if the song exists in the global SongData table
    in_table = supabase.table("SongData").select(count="exact").eq("title", song).eq("artist", artist).execute().count
    if not in_table:
        # Retrieve song data if it exists
        song_data = genius.search_song(song, artist)
        lyrics = song_data.lyrics

        # Preparing for SQS send and getting Kanji
        cleaned_lyrics = clean_lyrics(lyrics)
        kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
        all_kanji_data = get_all_kanji_data(kanji_list)

        # Insert the song data into the global database only if it doesn't already exist
        response = supabase.table("SongData").insert({
            "title": song, 
            "artist": artist, 
            "lyrics": None, 
            "hiragana_lyrics": None, 
            "word_mapping": None, 
            "kanji_data": all_kanji_data, 
            "image_url": image
        }).execute()
        
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
    print(response)
    return response
   
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
        image_url = get_image(artist, title)
        cleaned_lyrics = clean_lyrics(lyrics)
        kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
        all_kanji_data = get_all_kanji_data(kanji_list)
        
        response = supabase.table("SongData").insert({
            "title": title, 
            "artist": artist, 
            "lyrics": None, 
            "hiragana_lyrics": None, 
            "word_mapping": None, 
            "kanji_data": all_kanji_data, 
            "image_url": image_url
        }).execute()
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