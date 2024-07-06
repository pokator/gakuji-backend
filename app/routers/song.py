from fastapi import Body, Depends, status, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.supabase import create_supabase_client
from app.dbmodels import User
from app.models import Token, CreateUser
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

router = APIRouter(prefix="/song", tags=["song"])
load_dotenv()
stage = os.getenv("STAGE")

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

def load_kanji_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
kanji_data = load_kanji_data('kanji.json')

#gets the song from a given URI, returns artist and song of the track.
def get_song(uri):
    track = sp.track(uri, market="JP")
    artist = track['artists'][0]['name']
    song = track['name']
    return artist, song


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
        tagged_line = [word for word in tagger(line)]
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

#gets an ID for a particular word in the lyrics.
def get_word_info(word):
    result = jam.lookup(word)
    word_info = []
    for entry in result.entries[:3]:  # Include up to 3 entries
        word_info.append(entry.idseq)
    return word_info

#getting the word info for all words in the lyrics
def process_tokenized_lines(lines):
    word_dict = {}
    for line in lines:
        for word in line:
            word_info = get_word_info(word.surface)
            if len(word_info) > 0:
                word_dict[word] = word_info
    return word_dict



#need a route which takes in a spotify uri and adds the processed song to the database.
#need a route which takes in artist, song and, lyrics, processes the text, and adds the processed song to the database
#need a route which provides a desired song from the database when requested. provides the lyrics and the mapping of word to idseq and kanji dictionary.

#need a route which looks up a particular idseq in jamdict.
@router.get("/current-user")
async def get_word(idseq: str = None): #not sure about how to define
    if idseq:
        word_result = jam.lookup("id#"+idseq).to_dict()['entries'][0]
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
            "furigana" : furigana,
            "romaji": romaji,
            "definitions": word_properties
        }
        
        return result
    else:
        return {"message": "No idseq provided"}


#need a route which provides the hiragana for a given song.
#need a route which provides a list of songs from the database when requested for the particular user.



# cleaned_result = clean_lyrics(result)
# print(cleaned_result)

# lines = split_into_lines(cleaned_result)
# print(lines)