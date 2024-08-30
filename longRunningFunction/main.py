from jamdict import Jamdict
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv

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
        if entry.kanji_forms:
            word = entry.kanji_forms[0].text
        else:
            word = entry.kana_forms[0].text

        furigana = entry.kana_forms[0].text
        romaji = kakasi.convert(furigana)[0]["hepburn"]
        word_properties = []
        for sense in entry.senses:
            pos = sense.pos  # part of speech(es), LIST
            definition = []  # isolating the definitions, LIST
            for sense_gloss in sense.gloss:
                definition.append(sense_gloss.text)
            word_property = {
                "pos": pos,
                "definition": definition
            }
            word_properties.append(word_property)
        
        entry_result = {
            "word": word,
            "furigana": furigana,
            "romaji": romaji,
            "definitions": word_properties
        }
        word_info.append(entry_result)
    return word_info

def process_tokenized_lines(lines):
    word_dict = {}
    for line in lines:
        for word in line:
            word_info = get_word_info(word)
            if len(word_info) > 0:
                word_dict[word] = word_info
    return word_dict

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            try:
                body = json.loads(record['body'])
            except json.JSONDecodeError as e:
                return {
                    'statusCode': 400,
                    'body': json.dumps('JSON decoding error: ' + str(e))
                }
            
            tokenized_lines = body['word_mapping']
            artist = body['artist']
            song = body['song']
            access_token = body['access_token']
            refresh_token = body['refresh_token']
            # Perform the long-running task
            word_mapping = process_tokenized_lines(tokenized_lines)
            supabase.auth.set_session(access_token, refresh_token)
            response = supabase.table("SongData").update({"word_mapping": word_mapping}).eq("title", song).eq("artist", artist).execute()
            
        return {
            'statusCode': 200,
            'body': json.dumps('Long-running task completed successfully.')
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps('Long-running task failed with error: ' + str(e))
        }
