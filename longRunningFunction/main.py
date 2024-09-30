from jamdict import Jamdict
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv
import fugashi

AUXILIARIES = {
    'れる': 'passive',          # 食べられる -> to be eaten
    'られる': 'passive',        # 食べられる -> to be eaten
    'せる': 'causative',        # 食べさせる -> to make someone eat
    'させる': 'causative',      # 食べさせる -> to make someone eat
    'た': 'past tense',         # 食べた -> ate
    'ます': 'polite',           # 食べます -> eat (polite)
    'ました': 'polite past',    # 食べました -> ate (polite)
    'たい': 'desire',           # 食べたい -> want to eat
    'たがる': '3rd person desire', # 食べたがる -> (he/she) wants to eat
    'なかった': 'past negative',   # 食べなかった -> didn't eat
    'ない': 'negative',         # 食べない -> not eat
    'ません': 'negative polite',  # 食べません -> do not eat (polite)
    'ぬ': 'negative archaic',   # 食べぬ -> not eat (archaic)
    'ん': 'negative colloquial', # 食べん -> not eat (colloquial)
    'う': 'volitional',         # 食べよう -> let's eat
    'よう': 'volitional',       # 食べよう -> let's eat
    'だろう': 'probability',    # 食べるだろう -> probably eat
    'でしょう': 'probability polite', # 食べるでしょう -> will probably eat (polite)
    'たいです': 'desire polite', # 食べたいです -> want to eat (polite)
    'らしい': 'hearsay',        # 食べるらしい -> seems like (someone) eats
    'はず': 'expectation',      # 食べるはず -> expected to eat
    'べき': 'obligation',       # 食べるべき -> should eat
    'そう': 'appearance',       # 食べそう -> looks like it will be eaten
    'まい': 'negative volitional', # 食べまい -> will not eat
    'える': 'potential',        # 食べられる -> can eat
    'られる': 'potential',      # 食べられる -> can eat
    'おる': 'humble',           # 食べておる -> humbly eating (old/formal)
    'おります': 'humble polite', # 食べております -> humbly eating (polite)
    'くださる': 'honorific',    # 食べてくださる -> graciously eat
    'です': 'copula polite',    # 食べるです -> is eating (polite)
    'でございます': 'formal copula', # 食べるでございます -> (very formal)
    'かもしれない': 'possibility', # 食べるかもしれない -> might eat
    'だ': 'assertion',          # 食べるだ -> will eat (assertive, informal)
    'であった': 'assertion past', # 食べるであった -> was eating (assertive, informal)
    'でいる': 'continuous',     # 食べている -> is eating (continuous)
    'でいた': 'continuous past', # 食べていた -> was eating (continuous)
    'ございます': 'politeness', # Extra politeness (formal)
    'やがる': 'disdain',        # 食べやがる -> eats (with disdain)
    'ちまう': 'completion (casual)', # 食べちまう -> ended up eating (casual)
    'てしまう': 'completion',   # 食べてしまう -> to finish eating or "end up" eating
    # Add more as needed based on specific usage scenarios
}

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
tagger = fugashi.Tagger()

#setting up for tokenization
def split_into_lines(lyrics):
    # Split the lyrics into lines
    lines = lyrics.strip().split('\n')
    return lines

#returns two lists: one with the tokenized lyrics and one with the lyrics in hiragana
def tokenize(lines):
    line_list = []
    to_hiragana_list = []
    lyric_list = []
    for line in lines:
        tagged_line = tagger(line)
        lyric_line = [word.surface for word in tagged_line]
        lyric_list.append(lyric_line)
        to_hiragana_list.append(conv.do(line))
        line_list.append(tagged_line)
    return lyric_list, line_list, to_hiragana_list

def get_word_info(word):
    result = jam.lookup(word)
    word_info = []
    for entry in result.entries[:3]:  # Include up to 3 entries
        idseq = entry.idseq
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
            "idseq": idseq,
            "word": word,
            "furigana": furigana,
            "romaji": romaji,
            "definitions": word_properties
        }
        word_info.append(entry_result)
    return word_info

# def process_tokenized_lines(lines):
#     word_dict = {}
#     for line in lines:
#         for word in line:
#             word_info = get_word_info(word)
#             if len(word_info) > 0:
#                 word_dict[word] = word_info
#     return word_dict

def process_tokenized_lines(lines):
    word_dict = {}
    
    for line in lines:
        combined_word = ""
        combined_lemma = ""
        combined_furigana = ""
        combined_romaji = ""
        definitions_list = []
        aux_meanings = []

        for word in line:
            # Get word information using lemma for definition lookup
            word_info = get_word_info(word.feature.lemma)

            if word.feature.pos1 == '動詞':  # Main verb detection
                # If there's an unfinished verb+auxiliary sequence, store it
                if combined_word:
                    word_dict[combined_word] = {
                        "idseq": word_info.get('idseq'),
                        "word": combined_word,
                        "furigana": combined_furigana,
                        "romaji": combined_romaji,
                        "definitions": modify_definitions(definitions_list, aux_meanings)
                    }
                
                # Reset combined data for the new verb
                combined_word = word.surface
                combined_lemma = word.feature.lemma
                combined_furigana = word.feature.kana
                combined_romaji = word.feature.pronBase
                definitions_list = word_info['definitions']
                aux_meanings = []

            elif word.feature.pos1 == '助動詞':  # Auxiliary verb detection
                # Combine auxiliary verb with main verb
                combined_word += word.surface
                combined_furigana += word.feature.kana
                combined_romaji += word.feature.pronBase

                # Get auxiliary lemma and check for its meaning
                aux_lemma = word.feature.lemma
                aux_meaning = AUXILIARIES.get(aux_lemma)
                if aux_meaning:
                    aux_meanings.append(aux_meaning)

        # Store the final verb+auxiliary sequence after processing the whole line
        if combined_word:
            word_dict[combined_word] = {
                "idseq": word_info.get('idseq'),
                "word": combined_word,
                "furigana": combined_furigana,
                "romaji": combined_romaji,
                "definitions": modify_definitions(definitions_list, aux_meanings)
            }

    return word_dict

def modify_definitions(definitions_list, aux_meanings):
    """
    Modify the definitions to reflect the auxiliary sequence meanings.
    """
    if aux_meanings:
        for i, definition in enumerate(definitions_list):
            aux_str = ", ".join(aux_meanings)
            definitions_list[i] = f"{definition} ({aux_str})"
    return definitions_list


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
            
            cleaned_lyrics = body['cleaned_lyrics']
            artist = body['artist']
            song = body['song']
            access_token = body['access_token']
            refresh_token = body['refresh_token']
            # Perform the long-running task
            lines = split_into_lines(cleaned_lyrics)
            lyrics, tokenized_lines, hiragana_lines = tokenize(lines)
            word_mapping = process_tokenized_lines(tokenized_lines)
            supabase.auth.set_session(access_token, refresh_token)
            response = supabase.table("SongData").update({"lyrics": lyrics, "hiragana_lyrics": hiragana_lines, "word_mapping": word_mapping}).eq("title", song).eq("artist", artist).execute()
            
        return {
            'statusCode': 200,
            'body': json.dumps('Long-running task completed successfully.')
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps('Long-running task failed with error: ' + str(e))
        }
