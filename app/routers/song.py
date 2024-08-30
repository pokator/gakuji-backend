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


cid ='5edc552c91d8428cbcaf7eb1230a9526'
secret ='9d3113c375c3436abb7caf696dd6e538'
genius_secret = "anr-ZTXEBFL5IiCqeJGAXF5Zz--f2zW0kR_CfIbt5hiJ-Y8_f7MdCyq2YQqSwr4H"

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
genius = Genius(genius_secret)
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

# print(os.listdir())

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
# result = delete_before_line_break(lyrics)[1:]

#clean up common excess data brought in using the API.
def clean_lyrics(lyrics):
    lyrics = delete_before_line_break(lyrics)
    # Remove "You might also like" text only
    lyrics = re.sub(r'You might also like', '', lyrics)
    # Remove "number followed by Embed"
    lyrics = re.sub(r'\d+Embed', '', lyrics)
    return lyrics

#setting up for tokenization
def split_into_lines(lyrics):
    # Split the lyrics into lines
    lines = lyrics.strip().split('\n')
    return lines

#returns two lists: one with the tokenized lyrics and one with the lyrics in hiragana
def tokenize(lines):
    line_list = []
    to_hiragana_list = []
    for line in lines:
        # tagged = tagger(line)
        tagged_line = [word.surface for word in tagger(line)]
        to_hiragana_list.append(conv.do(line))
        line_list.append(tagged_line)
    return line_list, to_hiragana_list

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

# #gets an ID for a particular word in the lyrics.
# def get_word_info(word):
#     result = jam.lookup(word)
#     word_info = []
#     for entry in result.entries[:3]:  # Include up to 3 entries
#         word_info.append(entry.idseq)
#     return word_info

# #getting the word info for all words in the lyrics
# def process_tokenized_lines(lines):
#     word_dict = {}
#     for line in lines:
#         for word in line:
#             word_info = get_word_info(word)
#             if len(word_info) > 0:
#                 word_dict[word] = word_info
#     return word_dict

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
            "defintion": definition
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
async def add_song_spot(spotifyItem: SpotifyAdd = None, user: User = Depends(get_current_user), session = Depends(get_current_session)):
    uri = spotifyItem.uri
    print(uri)
    print(user)
    print(session)
    if uri is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        
        artist, song, image = await get_song_from_spotify(uri)
        in_my_table = supabase.table("Song").select(count="exact").eq("title", song).eq("artist", artist).eq("id", user.id).execute().count
        if in_my_table > 0:
            return {"message": "Song already in database."}
        else:
            in_table = supabase.table("SongData").select(count="exact").eq("title", song).eq("artist", artist).execute().count
            if in_table == 0:
                song_data = genius.search_song(song, artist)
                lyrics = song_data.lyrics
                cleaned_lyrics = clean_lyrics(lyrics)
                lines = split_into_lines(cleaned_lyrics)
                tokenized_lines, hiragana_lines = tokenize(lines)
                kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
                all_kanji_data = get_all_kanji_data(kanji_list)

                
                response = supabase.table("SongData").insert({"title": song, "artist": artist, "lyrics": tokenized_lines, "hiragana_lyrics": hiragana_lines, "word_mapping": None, "kanji_data": all_kanji_data, "image_url": image}).execute()
                # word_mapping = process_tokenized_lines(tokenized_lines)
                
                body = {"song": song, "artist": artist, "word_mapping": tokenized_lines, "access_token": session.access_token, "refresh_token": session.refresh_token}
                print(body)
                
                sqs = aws_session.resource('sqs')
                queue = sqs.Queue(sqs_url)
                queue.send_message(
                    # QueueUrl=sqs_url,
                    MessageBody=json.dumps(body)
                )
            response = supabase.table("Song").insert({"title": song, "artist": artist, "id": user.id}).execute()
            return response
    
#need a route which takes in artist, song and, lyrics, processes the text, and adds the processed song to the database
@router.post("/add-song-manual")
async def add_song_manual(manual: ManualAdd, user: User = Depends(get_current_user), session = Depends(get_current_session)):
    title = manual.title
    artist = manual.artist
    lyrics = manual.lyrics
    if title is None or artist is None or lyrics is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        in_my_table = supabase.table("Song").select(count="exact").eq("title", title).eq("artist", artist).eq("id", user.id).execute().count
        if in_my_table > 0:
            return {"message": "Song already in database."}
        else:
            in_table = supabase.table("SongData").select(count="exact").eq("title", title).eq("artist", artist).execute().count
            if in_table == 0:
                # song not in global database
                image_url = get_image(artist, title)
                cleaned_lyrics = clean_lyrics(lyrics)
                lines = split_into_lines(cleaned_lyrics)
                tokenized_lines, hiragana_lines = tokenize(lines)
                kanji_list = extract_unicode_block(CONST_KANJI, cleaned_lyrics)
                all_kanji_data = get_all_kanji_data(kanji_list)        
                # call long running SQS to process tokenized lines and add it to the database
                response = supabase.table("SongData").insert({"title": title, "artist": artist, "lyrics": tokenized_lines, "hiragana_lyrics": hiragana_lines, "word_mapping": None, "kanji_data": all_kanji_data, "image_url": image_url}).execute()
            #   This is done in the other longrunning function 
                # word_mapping = process_tokenized_lines(tokenized_lines)
                # body = {"song": title, "artist": artist, "word_mapping": tokenized_lines, "uuid": supabase.auth.get_user().user.id}

                # sqs = boto3.client('sqs', region_name='us-east-2')
                # sqs.send_message(
                #     QueueUrl=sqs_url,
                #     MessageBody=body
                # )
                
                body = {"song": title, "artist": artist, "word_mapping": tokenized_lines, "access_token": session.access_token, "refresh_token": session.refresh_token}
                print(body)
                
                sqs = aws_session.resource('sqs')
                queue = sqs.Queue(sqs_url)
                queue.send_message(
                    # QueueUrl=sqs_url,
                    MessageBody=json.dumps(body)
                )
                # response = supabase.table("Song").insert({"title": title, "artist": artist, "lyrics": cleaned_lyrics, "hiragana_lyrics": hiragana_lines, "word_mapping": word_mapping, "kanji_data": all_kanji_data, "uuid": supabase.auth.get_user().user.id, "image_url": image_url}).execute()
                # response = supabase.table("SongData").insert({"title": title, "artist": artist, "lyrics": tokenized_lines, "hiragana_lyrics": hiragana_lines, "word_mapping": word_mapping, "kanji_data": all_kanji_data, "image_url": image_url}).execute()
            response = supabase.table("Song").insert({"title": title, "artist": artist, "id": user.id}).execute()
            return response

#need a route which provides a desired song from the database when requested. provides the lyrics and the mapping of word to idseq and kanji dictionary.
@router.get("/get-song")
async def get_song(title: str = None, artist: str = None, user: User = Depends(get_current_user)):
    if title is None or artist is None or user is None:
        return {"message": "Missing information. Please try again."}
    else:
        # have access to title, artist, uuid
        response = supabase.table("SongData").select("lyrics, hiragana_lyrics, word_mapping").eq("title", title).eq("artist", artist).execute()
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

#need a route which provides a list of songs from the database when requested for the particular user.
@router.get("/get-songs")
async def get_songs(user: User = Depends(get_current_user)):
    response = supabase.table("Song").select("title, artist, SongData(image_url)").eq("id", user.id).execute()
    if not response.data :
        return {"message": "No songs found in database."}
    else:
        return response.data


@router.get("/get-global-songs")
async def get_global_songs(limit: int = 10, offset: int = 0, user: User = Depends(get_current_user)):
    if limit == None or offset == None:
        return {"message": "Missing information. Please try again."}
    else:
        response = supabase.table("Song").select("title, artist, SongData(image_url)").limit(limit).offset(offset).order("created_at", desc=True).execute()
        return response.data




# cleaned_result = clean_lyrics(result)
# print(cleaned_result)

# lines = split_into_lines(cleaned_result)
# print(lines)