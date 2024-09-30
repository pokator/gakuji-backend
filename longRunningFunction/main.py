from jamdict import Jamdict
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv
import fugashi

AUXILIARIES = {
    'れる': 'passive', 'られる': 'passive', 'せる': 'causative',
    'させる': 'causative', 'た': 'past tense', 'ます': 'polite',
    'ました': 'polite past', 'たい': 'desire', 'たがる': '3rd person desire',
    'なかった': 'past negative', 'ない': 'negative', 'ません': 'negative polite',
    'ぬ': 'negative archaic', 'ん': 'negative colloquial', 'う': 'volitional',
    'よう': 'volitional', 'だろう': 'probability', 'でしょう': 'probability polite',
    'たいです': 'desire polite', 'らしい': 'hearsay', 'はず': 'expectation',
    'べき': 'obligation', 'そう': 'appearance', 'まい': 'negative volitional',
    'える': 'potential', 'られる': 'potential', 'おる': 'humble',
    'おります': 'humble polite', 'くださる': 'honorific', 'です': 'copula polite',
    'でございます': 'formal copula', 'かもしれない': 'possibility', 'だ': 'assertion',
    'であった': 'assertion past', 'でいる': 'continuous', 'でいた': 'continuous past',
    'ございます': 'politeness', 'やがる': 'disdain', 'ちまう': 'completion (casual)',
    'てしまう': 'completion', # Add more as needed based on specific usage scenarios
}

load_dotenv()

api_url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_API")

def create_supabase_client():
    print("Creating Supabase client.")
    supabase: Client = create_client(api_url, key)
    return supabase

jam = Jamdict(memory_mode=True)
kakasi = pykakasi.kakasi()
kakasi.setMode("J", "H")
kakasi.setMode("K", "H")
conv = kakasi.getConverter()
supabase = create_supabase_client()
tagger = fugashi.Tagger()

def split_into_lines(lyrics):
    print("Splitting lyrics into lines.")
    lines = lyrics.strip().split('\n')
    return lines

def tokenize(lines):
    print("Tokenizing lyrics.")
    line_list = []
    to_hiragana_list = []
    lyric_list = []
    for line in lines:
        print(f"Tokenizing line: {line}")
        tagged_line = tagger(line)
        lyric_line = [word.surface for word in tagged_line]
        lyric_list.append(lyric_line)
        to_hiragana_list.append(conv.do(line))
        line_list.append(tagged_line)
    return lyric_list, line_list, to_hiragana_list

def get_word_info(word):
    print(f"Looking up word: {word}")
    result = jam.lookup(word)
    word_info = []
    for entry in result.entries[:3]:  # Limit to 3 entries
        idseq = entry.idseq
        if entry.kanji_forms:
            word_text = entry.kanji_forms[0].text
        else:
            word_text = entry.kana_forms[0].text

        furigana = entry.kana_forms[0].text
        romaji = kakasi.convert(furigana)[0]["hepburn"]
        word_properties = []
        for sense in entry.senses:
            pos = sense.pos
            definition = [sense_gloss.text for sense_gloss in sense.gloss]
            word_properties.append({
                "pos": pos,
                "definition": definition
            })

        entry_result = {
            "idseq": idseq,
            "word": word_text,
            "furigana": furigana,
            "romaji": romaji,
            "definitions": word_properties
        }
        word_info.append(entry_result)

    print(f"Word info retrieved: {word_info}")
    return word_info

def process_tokenized_lines(lines):
    print("Processing tokenized lines.")
    word_dict = {}
    
    for line in lines:
        combined_word = ""
        combined_lemma = ""
        combined_furigana = ""
        combined_romaji = ""
        definitions_list = []
        aux_meanings = []

        for word in line:
            print(f"Processing word: {word.surface}")
            word_info = get_word_info(word.feature.lemma)

            if word.feature.pos1 == '動詞':  # Main verb detection
                print(f"Detected verb: {word.surface}")
                if combined_word:
                    word_dict[combined_word] = {
                        "word": combined_word,
                        "furigana": combined_furigana,
                        "romaji": combined_romaji,
                        "definitions": modify_definitions(definitions_list, aux_meanings)
                    }
                
                combined_word = word.surface
                combined_lemma = word.feature.lemma
                combined_furigana = word.feature.kana
                combined_romaji = word.feature.pronBase
                definitions_list = word_info[0]['definitions']
                aux_meanings = []

            elif word.feature.pos1 == '助動詞':  # Auxiliary verb detection
                print(f"Detected auxiliary verb: {word.surface}")
                combined_word += word.surface
                combined_furigana += word.feature.kana
                combined_romaji += word.feature.pronBase

                aux_lemma = word.feature.lemma
                aux_meaning = AUXILIARIES.get(aux_lemma)
                if aux_meaning:
                    aux_meanings.append(aux_meaning)

        if combined_word:
            word_dict[combined_word] = {
                "word": combined_word,
                "furigana": combined_furigana,
                "romaji": combined_romaji,
                "definitions": modify_definitions(definitions_list, aux_meanings)
            }

    print(f"Processed word dictionary: {word_dict}")
    return word_dict

def modify_definitions(definitions_list, aux_meanings):
    if aux_meanings:
        for i, definition in enumerate(definitions_list):
            aux_str = ", ".join(aux_meanings)
            definitions_list[i]['definition'] = f"{definition['definition']} ({aux_str})"
    return definitions_list

def lambda_handler(event, context):
    try:
        print("Lambda handler invoked.")
        for record in event['Records']:
            try:
                body = json.loads(record['body'])
                print(f"Processing record: {body}")
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}")
                return {
                    'statusCode': 400,
                    'body': json.dumps(f'JSON decoding error: {e}')
                }

            cleaned_lyrics = body['cleaned_lyrics']
            artist = body['artist']
            song = body['song']
            access_token = body['access_token']
            refresh_token = body['refresh_token']

            lines = split_into_lines(cleaned_lyrics)
            lyrics, tokenized_lines, hiragana_lines = tokenize(lines)
            word_mapping = process_tokenized_lines(tokenized_lines)

            supabase.auth.set_session(access_token, refresh_token)
            print(f"Updating database for song: {song} by {artist}")
            response = supabase.table("SongData").update({
                "lyrics": lyrics, "hiragana_lyrics": hiragana_lines, "word_mapping": word_mapping
            }).eq("title", song).eq("artist", artist).execute()

        return {
            'statusCode': 200,
            'body': json.dumps('Long-running task completed successfully.')
        }
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps(f'Long-running task failed with error: {e}')
        }
