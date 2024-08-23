# regular function
from jamdict import Jamdict
import jamdict_data
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv
from functools import wraps


load_dotenv()

api_url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_API")

def create_supabase_client():
    supabase: Client = create_client(api_url, key)
    return supabase

jam = Jamdict(memory_mode=True)
kakasi = pykakasi.kakasi()
kakasi.setMode("J", "H")
kakasi.setMode("K", "H")
conv = kakasi.getConverter()
supabase = create_supabase_client()

def get_word_info(word):
    result = jam.lookup(word)
    word_info = []
    for entry in result.entries[:3]:  # Include up to 3 entries
        # word_info.append(entry.idseq)
        word = result['kanji'][0]['text']
        furigana = result['kana'][0]['text']
        romaji = kakasi.convert(furigana)[0]["hepburn"]
        word_properties = []
        # all definitions availabile for this ID
        for sense in result['senses']:
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
        word_info.append(result)
    return word_info


def process_tokenized_lines(lines):
    word_dict = {}
    for line in lines:
        for word in line:
            word_info = get_word_info(word)
            if len(word_info) > 0:
                word_dict[word] = word_info
    return word_dict

def process_lines(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        tokenized_lines = body['word_mapping']
        artist = body['artist']
        song = body['song']
        token = body['token']
        # Perform the long-running task
        # Update the database
        word_mapping = process_tokenized_lines(tokenized_lines)
        supabase: Client = create_client(api_url, key)
        supabase.auth.set_session(token)
        response = supabase.table("SongData").update({"word_mapping": word_mapping}).eq("title", song).eq("artist", artist).execute()
        
    return {
        'statusCode': 200,
        'body': json.dumps('Long-running task completed successfully.')
    }
    
    #upon completion update the database with the word_mapping
    
# def create_word_return(idseq):
# word_result = jam.lookup("id#"+idseq).to_dict()['entries'][0]
# word = word_result['kanji'][0]['text']
# furigana = word_result['kana'][0]['text']
# romaji = kakasi.convert(furigana)[0]["hepburn"]
# word_properties = []
# # all definitions availabile for this ID
# for sense in word_result['senses']:
#     pos = sense['pos'] #part of speech(es), LIST
#     definition = [] #isolating the defintions, LIST
#     for sense_gloss in sense["SenseGloss"]:
#         definition.append(sense_gloss["text"])
#     word_property = {
#         "pos": pos,
#         "defintion": definition
#     }
#     word_properties.append(word_property)
    
# result = {
#     "word": word,
#     "furigana" : furigana,
#     "romaji": romaji,
#     "definitions": word_properties
# }

# return result