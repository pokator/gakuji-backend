from jamdict import Jamdict
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv
import fugashi
import re
from copy import deepcopy

#TODO: ensure these meanings are accurate.
AUXILIARIES = {
    'れる': 'passive',
    'られる': 'passive/potential',
    'せる': 'causative',
    'させる': 'causative',
    'た': 'past tense',
    'ます': 'polite',
    'ました': 'polite past',
    'たい': 'desire',
    'たがる': '3rd person desire',
    'なかった': 'past negative',
    'ない': 'negative',
    'ません': 'negative polite',
    'ぬ': 'negative archaic',
    'ん': 'negative colloquial',
    'う': 'volitional',
    'よう': 'volitional',
    'だろう': 'probability',
    'でしょう': 'probability polite',
    'たいです': 'desire polite',
    'らしい': 'hearsay',
    'はず': 'expectation',
    'べき': 'obligation',
    'そう': 'appearance',
    'まい': 'negative volitional',
    'える': 'potential',
    'おる': 'humble',
    'おります': 'humble polite',
    'くださる': 'honorific',
    'です': 'copula polite',
    'でございます': 'formal copula',
    'かもしれない': 'possibility',
    'だ': 'assertion',
    'であった': 'assertion past',
    'でいる': 'continuous',
    'でいた': 'continuous past',
    'ございます': 'politeness',
    'やがる': 'disdain',
    'ちまう': 'completion (casual)',
    'てしまう': 'completion',
    'て': 'indicates continuing action​',
    'で': 'indicates continuing action​',
    'とく': 'do in advance (informal)',
    'ちゃう': 'casual completion (from てしまう)',
    'じゃう': 'casual completion (from でしまう)',
    'ず': 'negative (classical/formal)',
    'ずに': 'without doing (negative)',
    'けり': 'classical past/realization',
    'な': 'imperative negative',
    'なさい': 'polite imperative (request)',
    'さ': 'informal volitional/command',
    'であろう': 'formal probability',
    'のだ': 'explanatory/assertive tone',
    'んだ': 'casual explanatory tone (from のだ)',
    'か': 'question marker',
    'かい': 'informal question (masculine)',
    'だっけ': 'recollection/uncertainty',
    'たっけ': 'casual past question',
    'なければならない': 'must/obligation',
    'なくてもいい': 'optional (doesn’t have to)',
    'つもり': 'intention',
    'べし': 'strong obligation (classical)',
    'き': 'past experience (classical)',
    'まじ': 'negative intent/conjecture (classical)',
    'がる': 'shows feelings/desire (3rd person)',
    'そうだ': 'hearsay',
    'だって': 'even if/after all/because',
    'ければ': 'conditional (if)',
    'たら': 'conditional (if/when)',
    'なら': 'hypothetical/conditional',
    'とけ': 'command form of ておけ (in advance)',
    'うち': 'within a period of time (while)',
    'ように': 'so that (wish or command)',
    'べく': 'in order to (formal)',
    'まま': 'as it is/unchanged',
    'とも': 'even if',
    'すぎる': 'excessive/too much',
    'がち': 'tend to/prone to',
    'がたい': 'difficult to do',
    'らしいです': 'polite hearsay',
    'すれば': 'if done',
    'けど': 'but/although',
    'ながら': 'while doing',
    'ところ': 'about to do/just did',
    'しなければならない': 'must do',
    'てもいい': 'it’s okay to do',
    'つづける': 'to continue doing',
    'ばかり': 'just done (recently)',
    'ことがある': 'there are times when',
    'にくい': 'difficult to do (emotionally)',
    'やすい': 'easy to do',
    'おわる': 'to finish doing',
    'はじまる': 'to begin doing',
    'でしかない': 'nothing but/only',
    'だっ': 'casual past form of です',
    'な': 'adjectival ending',
    'の': 'nominalizer',
    'てる': 'ている, informal',
    'ちゃ': 'てしまう, casual',
    'せる': 'causative',
    'せ': 'causative',
}

SUFFIX_DICT = {
    "的": "suffix used to form adjectives, indicating 'like' or 'of'",
    "ら": "suffix used to indicate plurality, often for people",
    "たち": "suffix indicating a group or plural form, often for people",
    "君": "suffix used to address someone in a friendly or familiar manner, often for younger people",
    "様": "suffix used to indicate respect, often used for customers or clients",
    "性": "suffix indicating 'nature' or 'characteristics', used in nouns to denote quality",
    "者": "suffix meaning 'person', often used in titles or to describe someone",
    "用": "suffix indicating 'use' or 'for the purpose of', used in nouns",
    "風": "suffix meaning 'style' or 'manner', often used to denote a particular way of doing something",
    "体": "suffix indicating 'body' or 'form', used in nouns related to physical structures or states",
    "学": "suffix indicating 'study' or 'science', used in nouns related to fields of study",
    "所": "suffix meaning 'place' or 'location', often used in nouns to denote a specific location",
    "式": "suffix meaning 'style' or 'system', used in nouns to denote a particular method or system",
}

load_dotenv()

api_url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_API")

def create_supabase_client():
    # print("Creating Supabase client.")
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
    # print("Splitting lyrics into lines.")
    lines = lyrics.strip().split('\n')
    return lines

def tokenize(lines):
    # print("Tokenizing lyrics.")
    line_list = []
    # to_hiragana_list = []
    # lyric_list = []
    for line in lines:
        # print(f"Tokenizing line: {line}")
        tagged_line = tagger(line)
        # lyric_line = [word.surface for word in tagged_line]
        # lyric_list.append(lyric_line)
        # to_hiragana_list.append(conv.do(line))
        # for word in tagged_line:
        #     print(word.surface, word.feature, word.pos, sep='\t')
        line_list.append(tagged_line)
    return line_list

'''
This function queries the dictionary for a word and returns the information.
There are still some edge cases to handle here - for example, particles and conjunctions
are not always found in the dictionary.

TODO: Make considerations on JISHO API (maybe query it when JMDict fails)
TODO: Make an edge case dictionary (for words that get incorrectly tokenized)
'''
def get_word_info(word, type="word"):
    # print(f"Looking up word: {word}")
    
    try:
        result = jam.lookup(word)
    except Exception as e:
        return []
    word_info = []
    for entry in result.entries[:3]: 
        common = False
        if type == "particle" and not ("conjunction" in entry.senses[0].pos or "particle" in entry.senses[0].pos):
            continue
        for kanji in entry.kanji_forms:
            #kanji contains text and info
            if kanji.text == word and kanji.pri and "news1" in kanji.pri:
                common = True
                break
        # Limit to 3 entries
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
        if(common):
            word_info.insert(0, entry_result)
        else:
            word_info.append(entry_result)

    # print(f"Word info retrieved: {word_info}")
    return word_info

def is_japanese(text):
    # Regex to match Hiragana, Katakana, Kanji, and Japanese punctuation
    return re.match(r'[\u3040-\u30FF\u4E00-\u9FFF\uFF00-\uFFEF]', text)

'''
This function handles the processing of the lyrics once they are tokenized. There's a lot of edge
cases here, so the logic loops through every line in the lyrics, and every lyric in the line. 
My current best option is to handle part of speech cases individually. 

TODO: consider integrating JISHO dictionary instead of Jamdict for more accurate, common definitions
TODO: handle more edge cases for suffixes and other parts of speech
'''
def process_tokenized_lines(lines):
    word_dict = {}
    lyrics = []

    for line in lines:
        new_line = []

        pos = 0
        while pos < len(line):
            word = line[pos]
            # Get word information using lemma for definition lookup
            if not is_japanese(word.surface):
                # print(f"Skipping non-Japanese token: {word.surface}")
                temp_list = []
                temp_properties = {'pos': ["Not Applicable"], 'definition': ['not found']}
                temp_list.append({
                    "idseq": "none",
                    "word": word.surface,
                    "furigana": "N/A",
                    "romaji": "N/A",
                    "definitions": temp_properties
                })
                word_dict[word.surface] = temp_list
                new_line.append(word.surface)
                pos += 1
                continue
            
            if word.surface in word_dict:
                #efficiency modification - most songs will repeat words, why look them up again
                # print(f"Word already processed: {word.surface}")
                new_line.append(word.surface)
                pos += 1
                continue

            # print(f"Processing word: {word.surface}, Lemma: {word.feature.lemma}, POS1: {word.feature.pos1}")
            
            # Verbs, adjectives, adjectival nouns.
            if (word.feature.pos1 == '動詞' 
                or word.feature.pos1 == '形容詞' 
                or (word.feature.pos1 == '名詞' and word.feature.pos3 == '形状詞可能')
                or word.feature.pos1 == '形状詞'
                or word.feature.pos1 == '形容詞'):
                
                #retrieve definition from dictionary.
                word_info = get_word_info(word.feature.lemma)
                for info in word_info:
                    info['furigana'] = conv.do(word.surface)
                    info['romaji'] = kakasi.convert(word.surface)[0]["hepburn"]
                
                base_word_data = deepcopy(word_info)
                final_word = word.surface
                pos += 1
                suffix_data = []
                #continue through the line to check for auxiliaries. 
                while pos < len(line) and ((line[pos].surface in AUXILIARIES and line[pos].feature.pos1 == '助動詞') or line[pos].feature.pos1 == '接尾辞' or line[pos].surface in ['て', 'で', 'ん','ちゃ']):
                    # we have found a bound auxiliary. Need to reflect in main verb's definitions, furigana, and romaji
                    aux_word = line[pos]
                    # print(aux_word.surface, aux_word.feature, aux_word.pos, sep='\t')
                    final_word += aux_word.surface
                    aux_furigana = conv.do(aux_word.surface)
                    aux_romaji = kakasi.convert(aux_word.surface)[0]["hepburn"]
                    for info in word_info:
                        info['furigana'] += aux_furigana
                        info['romaji'] += aux_romaji
                    aux_lemma = aux_word.feature.lemma
                    aux_meaning = AUXILIARIES.get(aux_lemma)
                    if aux_meaning:
                        for info in word_info:
                            info['definitions'] = modify_definitions(info['definitions'], [aux_meaning])
                            
                    suffix_data.append({
                        "token": aux_word.surface,
                        "root_form": aux_word.feature.lemma,
                        "furigana": aux_furigana,
                        "romaji": aux_romaji,
                        "meaning": aux_meaning
                    })
                        
                    pos += 1
                    
                composite_word_data = word_info
                full_word_data = {
                    "root": base_word_data,
                    "suffixes": suffix_data,
                    "composite": composite_word_data
                }
                word_dict[final_word] = full_word_data
                new_line.append(final_word)
            # Suffix detection
            elif word.feature.pos1 == '接尾辞':  
                # print(word.surface, word.feature, word.pos, sep='\t')
                noun = line[pos - 1]
                suffix = word
                word_info = get_word_info(noun.surface + suffix.surface)
                if len(word_info) > 0:
                    # the combined word exists.
                    word_dict[noun.surface + suffix.surface] = word_info
                    composite_word_data = word_info
                    full_word_data = {
                        "root": None,
                        "suffixes": None,
                        "composite": composite_word_data
                    }
                    
                    new_line.append(noun.surface + suffix.surface)
                elif suffix.surface in SUFFIX_DICT:
                    # the suffix is a known suffix
                    temp_list = []
                    temp_properties = {'pos': ["Suffix"], 'definition': [SUFFIX_DICT[suffix.surface]]}
                    temp_list.append({
                        "idseq": "none",
                        "word": suffix.surface,
                        "furigana": conv.do(suffix.surface),
                        "romaji": kakasi.convert(suffix.surface)[0]["hepburn"],
                        "definitions": temp_properties
                    })
                    
                    full_word_data = {
                        "root": None,
                        "suffixes": None,
                        "composite": temp_list
                    }
                    
                    word_dict[suffix.surface] = temp_list
                    new_line.append(suffix.surface)
                else:
                    # the suffix is not one of the commons, so we will look up the suffix alone
                    suffix_info = get_word_info(suffix.surface)
                    if len(suffix_info) > 0:
                        full_word_data = {
                            "root": None,
                            "suffixes": None,
                            "composite": suffix_info
                        }
                        word_dict[suffix.surface] = full_word_data
                        new_line.append(suffix.surface)
                pos += 1
            elif word.feature.pos1 == '助詞':  # Particle detection
                # print(word.surface, word.feature, word.pos, sep='\t')
                word_info = get_word_info(word.surface, type="particle")
                
                if len(word_info) > 0:
                    full_word_data = {
                        "root": None,
                        "suffixes": None,
                        "composite": word_info
                    }
                    word_dict[word.surface] = full_word_data
                    new_line.append(word.surface)
                
                pos += 1
            else:  # For other parts of speech (nouns, adjectives, etc.)
                # print(word.surface, word.feature, word.pos, sep='\t')
                word_info = get_word_info(word.surface)
                if len(word_info) > 0:
                    full_word_data = {
                        "root": None,
                        "suffixes": None,
                        "composite": word_info
                    }
                    word_dict[word.surface] = full_word_data
                    new_line.append(word.surface)
                else :
                    # print("lemma lookup")
                    word_info = get_word_info(word.feature.lemma)
                    if len(word_info) > 0:
                        full_word_data = {
                            "root": None,
                            "suffixes": None,
                            "composite": word_info
                        }
                        word_dict[word.surface] = full_word_data
                        new_line.append(word.surface)
                    else : 
                        # print("creating dummy data")
                        temp_list = []
                        temp_properties = {'pos': [word.pos], 'definition': ['not found']}
                        temp_list.append({
                            "idseq": "none",
                            "word": word.surface,
                            "furigana": conv.do(word.surface),
                            "romaji": kakasi.convert(word.surface)[0]["hepburn"],
                            "definitions": temp_properties
                        })
                        full_word_data = {
                            "root": None,
                            "suffixes": None,
                            "composite": temp_list
                        }
                        word_dict[word.surface] = full_word_data
                        new_line.append(word.surface)
                pos += 1

        lyrics.append(new_line)
    return word_dict, lyrics

# def process_tokenized_lines(lines):
#     word_dict = {}
#     lyrics = []
    
#     # Cache for processed combinations to improve efficiency
#     combination_cache = {}

#     for line in lines:
#         new_line = []
#         pos = 0
        
#         while pos < len(line):
#             word = line[pos]
            
#             # Fast path for non-Japanese and cached words
#             if not is_japanese(word.surface):
#                 if word.surface not in word_dict:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": "N/A",
#                             "lemma": "N/A",
#                             "romaji": "N/A",
#                             "definitions": {'pos': ["Not Applicable"], 'definition': ['not found']}
#                         },
#                         "suffixes": []
#                     }
#                 new_line.append(word.surface)
#                 pos += 1
#                 continue
            
#             if word.surface in word_dict:
#                 new_line.append(word.surface)
#                 pos += 1
#                 continue

#             # Process verbs, adjectives, and adjectival nouns
#             if (word.feature.pos1 in ['動詞', '形容詞'] or 
#                 (word.feature.pos1 == '名詞' and word.feature.pos3 == '形状詞可能') or
#                 word.feature.pos1 in ['形状詞', '形容詞']):
                
#                 # Get root word information
#                 word_info = get_word_info(word.feature.lemma)
#                 root_info = {
#                     "idseq": word_info[0]["idseq"] if word_info else "none",
#                     "word": word.surface,
#                     "lemma": word.feature.lemma,
#                     "furigana": conv.do(word.surface),
#                     "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                     "definitions": word_info[0]["definitions"] if word_info else {'pos': [word.pos], 'definition': ['not found']}
#                 }
                
#                 suffixes = []
#                 final_word = word.surface
#                 pos += 1
                
#                 # Process auxiliaries and suffixes
#                 while pos < len(line):
#                     next_token = line[pos]
#                     if not (
#                         (next_token.surface in AUXILIARIES and next_token.feature.pos1 == '助動詞') or 
#                         next_token.feature.pos1 == '接尾辞' or 
#                         next_token.surface in ['て', 'で', 'ん', 'ちゃ']
#                     ):
#                         break
                        
#                     suffix_info = {
#                         "type": next_token.feature.pos1,
#                         "surface": next_token.surface,
#                         "lemma": next_token.feature.lemma,
#                         "furigana": conv.do(next_token.surface),
#                         "romaji": kakasi.convert(next_token.surface)[0]["hepburn"]
#                     }
                    
#                     # Add auxiliary meaning if available
#                     if next_token.surface in AUXILIARIES:
#                         suffix_info["meaning"] = AUXILIARIES[next_token.surface]
                    
#                     suffixes.append(suffix_info)
#                     final_word += next_token.surface
#                     pos += 1
                
#                 word_dict[final_word] = {
#                     "root": root_info,
#                     "suffixes": suffixes
#                 }
#                 new_line.append(final_word)
                
#             # Handle suffixes
#             elif word.feature.pos1 == '接尾辞':
#                 prev_word = line[pos - 1].surface
#                 combined = prev_word + word.surface
                
#                 # Use cached result if available
#                 if combined in combination_cache:
#                     word_dict[combined] = combination_cache[combined]
#                     new_line.pop()
#                     new_line.append(combined)
#                 else:
#                     word_info = get_word_info(combined)
#                     if word_info:
#                         result = {
#                             "root": {
#                                 "word": prev_word,
#                                 "furigana": conv.do(prev_word),
#                                 "romaji": kakasi.convert(prev_word)[0]["hepburn"]
#                             },
#                             "suffixes": [{
#                                 "surface": word.surface,
#                                 "furigana": conv.do(word.surface),
#                                 "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                                 "type": "接尾辞"
#                             }]
#                         }
#                         combination_cache[combined] = result
#                         word_dict[combined] = result
#                         new_line.pop()
#                         new_line.append(combined)
#                     else:
#                         # Handle standalone suffix
#                         suffix_info = get_word_info(word.surface) or [{
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": {'pos': ["Suffix"], 'definition': [SUFFIX_DICT.get(word.surface, 'not found')]}
#                         }]
#                         word_dict[word.surface] = {
#                             "root": suffix_info[0],
#                             "suffixes": []
#                         }
#                         new_line.append(word.surface)
#                 pos += 1
                
#             # Handle particles and other parts of speech
#             else:
#                 lookup_surface = word.surface
#                 lookup_lemma = word.feature.lemma
                
#                 # Try surface form first, then lemma
#                 word_info = get_word_info(lookup_surface) or get_word_info(lookup_lemma)
                
#                 if word_info:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": word_info[0]["idseq"],
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": word_info[0]["definitions"]
#                         },
#                         "suffixes": []
#                     }
#                 else:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": {'pos': [word.pos], 'definition': ['not found']}
#                         },
#                         "suffixes": []
#                     }
#                 new_line.append(word.surface)
#                 pos += 1

#         lyrics.append(new_line)
    
#     return word_dict, lyrics

# def process_tokenized_lines(lines):
#     word_dict = {}
#     lyrics = []
#     combination_cache = {}

#     for line in lines:
#         new_line = []
#         pos = 0
        
#         while pos < len(line):
#             word = line[pos]
            
#             # Fast path for non-Japanese and cached words
#             if not is_japanese(word.surface):
#                 if word.surface not in word_dict:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": "N/A",
#                             "lemma": "N/A",
#                             "romaji": "N/A",
#                             "definitions": [{'pos': ["Not Applicable"], 'definition': ['not found']}]  # Changed to list
#                         },
#                         "suffixes": [],
#                         "combination": None
#                     }
#                 new_line.append(word.surface)
#                 pos += 1
#                 continue
            
#             if word.surface in word_dict:
#                 new_line.append(word.surface)
#                 pos += 1
#                 continue

#             # Process verbs, adjectives, and adjectival nouns
#             if (word.feature.pos1 in ['動詞', '形容詞'] or 
#                 (word.feature.pos1 == '名詞' and word.feature.pos3 == '形状詞可能') or
#                 word.feature.pos1 in ['形状詞', '形容詞']):
                
#                 # Get root word information
#                 word_info = get_word_info(word.feature.lemma)
#                 root_info = {
#                     "idseq": word_info[0]["idseq"] if word_info else "none",
#                     "word": word.surface,
#                     "lemma": word.feature.lemma,
#                     "furigana": conv.do(word.surface),
#                     "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                     "definitions": word_info[0]["definitions"] if word_info else [{'pos': [word.pos], 'definition': ['not found']}]
#                 }
                
#                 suffixes = []
#                 final_word = word.surface
#                 final_furigana = root_info["furigana"]
#                 final_romaji = root_info["romaji"]
#                 combined_definitions = root_info["definitions"].copy()  # Create a copy of the list
#                 pos += 1
                
#                 # Process auxiliaries and suffixes
#                 aux_meanings = []  # Collect auxiliary meanings
#                 while pos < len(line):
#                     next_token = line[pos]
#                     if not (
#                         (next_token.surface in AUXILIARIES and next_token.feature.pos1 == '助動詞') or 
#                         next_token.feature.pos1 == '接尾辞' or 
#                         next_token.surface in ['て', 'で', 'ん', 'ちゃ']
#                     ):
#                         print("breaking")
#                         break
                        
#                     suffix_info = {
#                         "type": next_token.feature.pos1,
#                         "surface": next_token.surface,
#                         "lemma": next_token.feature.lemma,
#                         "furigana": conv.do(next_token.surface),
#                         "romaji": kakasi.convert(next_token.surface)[0]["hepburn"]
#                     }
                    
#                     # Add auxiliary meaning if available
#                     if next_token.surface in AUXILIARIES:
#                         aux_meaning = AUXILIARIES[next_token.surface]
#                         suffix_info["meaning"] = aux_meaning
#                         aux_meanings.append(aux_meaning)
#                     elif next_token.word.lemma in AUXILIARIES:
#                         aux_meaning = AUXILIARIES[next_token.word.lemma]
#                         suffix_info["meaning"] = aux_meaning
#                         aux_meanings.append(aux_meaning)
                    
#                     suffixes.append(suffix_info)
#                     final_word += next_token.surface
#                     final_furigana += suffix_info["furigana"]
#                     final_romaji += suffix_info["romaji"]
#                     pos += 1
                
#                 # Modify definitions if we have auxiliary meanings
#                 if aux_meanings:
#                     combined_definitions = modify_definitions(combined_definitions, aux_meanings)
                
#                 # Create combined form if there are suffixes
#                 combination = {
#                     "idseq": root_info["idseq"],
#                     "word": final_word,
#                     "furigana": final_furigana,
#                     "romaji": final_romaji,
#                     "definitions": combined_definitions
#                 } if suffixes else None
                
#                 word_dict[final_word] = {
#                     "root": root_info,
#                     "suffixes": suffixes,
#                     "combination": combination
#                 }
#                 new_line.append(final_word)
                
#             # Handle suffixes
#             elif word.feature.pos1 == '接尾辞':
#                 prev_word = line[pos - 1].surface
#                 combined = prev_word + word.surface
                
#                 # Use cached result if available
#                 if combined in combination_cache:
#                     word_dict[combined] = combination_cache[combined]
#                     new_line.pop()
#                     new_line.append(combined)
#                 else:
#                     word_info = get_word_info(combined)
#                     if word_info:
#                         root_part = {
#                             "word": prev_word,
#                             "furigana": conv.do(prev_word),
#                             "romaji": kakasi.convert(prev_word)[0]["hepburn"]
#                         }
                        
#                         suffix_part = {
#                             "surface": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "type": "接尾辞"
#                         }
                        
#                         combination = {
#                             "idseq": word_info[0]["idseq"],
#                             "word": combined,
#                             "furigana": root_part["furigana"] + suffix_part["furigana"],
#                             "romaji": root_part["romaji"] + suffix_part["romaji"],
#                             "definitions": word_info[0]["definitions"]
#                         }
                        
#                         result = {
#                             "root": root_part,
#                             "suffixes": [suffix_part],
#                             "combination": combination
#                         }
                        
#                         combination_cache[combined] = result
#                         word_dict[combined] = result
#                         new_line.pop()
#                         new_line.append(combined)
#                     else:
#                         # Handle standalone suffix
#                         suffix_info = get_word_info(word.surface) or [{
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": [{'pos': ["Suffix"], 'definition': [SUFFIX_DICT.get(word.surface, 'not found')]}]  # Changed to list
#                         }]
#                         word_dict[word.surface] = {
#                             "root": suffix_info[0],
#                             "suffixes": [],
#                             "combination": None
#                         }
#                         new_line.append(word.surface)
#                 pos += 1
                
#             # Handle particles and other parts of speech
#             else:
#                 lookup_surface = word.surface
#                 lookup_lemma = word.feature.lemma
                
#                 # Try surface form first, then lemma
#                 word_info = get_word_info(lookup_surface) or get_word_info(lookup_lemma)
                
#                 if word_info:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": word_info[0]["idseq"],
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": word_info[0]["definitions"]
#                         },
#                         "suffixes": [],
#                         "combination": None
#                     }
#                 else:
#                     word_dict[word.surface] = {
#                         "root": {
#                             "idseq": "none",
#                             "word": word.surface,
#                             "furigana": conv.do(word.surface),
#                             "romaji": kakasi.convert(word.surface)[0]["hepburn"],
#                             "definitions": [{'pos': [word.pos], 'definition': ['not found']}]  # Changed to list
#                         },
#                         "suffixes": [],
#                         "combination": None
#                     }
#                 new_line.append(word.surface)
#                 pos += 1

#         lyrics.append(new_line)
    
#     return word_dict, lyrics


# Modify definitions to include auxiliary meanings
def modify_definitions(definitions_list, aux_meanings):
    if aux_meanings:
        for i, definition in enumerate(definitions_list):
            aux_str = ", ".join(aux_meanings)
            definitions_list[i]['definition'].append(aux_str)
    return definitions_list

def convert_to_hiragana(lyrics):
    hiragana_lyrics = []
    for line in lyrics:
        hiragana_line = []
        for word in line:
            hiragana_line.append(conv.do(word))
        hiragana_lyrics.append(hiragana_line)
    return hiragana_lyrics

'''
The main processing code. SQS will send a message to this lambda function, which will then process the lyrics.
The lyrics are split into lines, tokenized, and then processed. The processed lyrics are then updated in the database.
'''
def lambda_handler(event, context):
    try:
        # print("Lambda handler invoked.")
        for record in event['Records']:
            try:
                body = json.loads(record['body'])
                # print(f"Processing record: {body}")
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
            tokenized_lines = tokenize(lines)
            word_mapping, lyrics = process_tokenized_lines(tokenized_lines)
            hiragana_lines = convert_to_hiragana(lyrics)

            supabase.auth.set_session(access_token, refresh_token)
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




# cleaned_lyrics = """[Intro]
# 未熟
# 無ジョウ
# されど
# 美しくあれ

# [Verse 1]
# No destiny ふさわしく無い
# こんなんじゃきっと物足りない
# くらい語っとけばうまくいく
# 物, 金, 愛, 言, もう自己顕示飽きた
# 既視感[デジャヴ]何がそんな不満なんだ?
# 散々ワガママ語っといて これ以上他に何がいる?
# そんなところも割と嫌いじゃ無い

# [Pre-Chorus]
# もう「聞き飽きたんだよ, そのセリフ」
# 中途半端だけは嫌

# [Chorus]
# もういい
# ああしてこうして言ってたって
# 愛して どうして? 言われたって
# 遊びだけなら簡単で 真剣交渉無茶苦茶で
# 思いもしない軽[おも]い言葉
# 何度使い古すのか?
# どうせ
# 期待してたんだ出来レースでも
# 引用だらけのフレーズも
# 踵持ち上がる言葉タブーにして
# 空気を読んだ雨降らないでよ

# [Verse 2]
# まどろっこしい話は嫌
# 必要最低限でいい 2文字以内でどうぞ
# 紅の蝶は何のメールも送らない
# 脆い扇子広げる その方が魅力的でしょう

# [Chorus]
# 迷で
# 応えられないなら ほっといてくれ
# 迷えるくらいなら 去っといてくれ
# 肝心なとこは筒抜けで
# 安心だけはさせられるような
# 甘いあめが降れば
# 傘もさしたくなるだろう?
# このまま
# 期待したままでよかった 目を瞑った
# 変えたかった 大人ぶった
# 無くした 巻き戻せなかった
# 今雨, 止まないで

# [Bridge]
# コピー, ペースト, デリート その繰り返し
# 吸って, 吐いた
# だから
# それでもいいからさ 此処いたいよ

# [Chorus]
# もういい
# ああしてこうして言ってたって
# 愛して どうして? 言われたって
# 遊びだけなら簡単で 真剣交渉支離滅裂で
# 思いもしない重い真実[うそ]は
# タブーにしなくちゃな?
# きっと
# 期待してたんだ出来レースでも
# 公式通りのフレーズも
# 踵上がる癖もう終わりにして
# 空気を読んだ空晴れないでよ

# [Outro]
# 今日も, 雨
# 傘を閉じて 濡れて帰ろうよ
# """

# cleaned_lyrics = """
# ない
# """
# lines = split_into_lines(cleaned_lyrics)
# tokenized_lines = tokenize(lines)
# word_mapping, lyrics = process_tokenized_lines(tokenized_lines)
# hiragana_lines = convert_to_hiragana(lyrics)
# print(word_mapping)
# print(lyrics)


# # pipe to a file
# with open("word_mapping.json", "w") as f:
#     json.dump(word_mapping, f, indent=4)



# previously generated by ChatGPT (incorrectly)

        # combined_word = ""
        # combined_furigana = ""
        # combined_romaji = ""
        # combined_word_info = []
        # aux_meanings = []
                # If there's an unfinished verb+auxiliary sequence, store it
                # if combined_word:
                #     word_dict[combined_word] = {
                #         "idseq": combined_word_info[0]['idseq'],
                #         "word": combined_word,
                #         "furigana": conv.do(combined_furigana),
                #         "romaji": kakasi.convert(combined_furigana)[0]["hepburn"],
                #         "definitions": modify_definitions(combined_word_info[0]['definitions'], aux_meanings)
                #     }

                # Reset combined data for the new verb
                # combined_word = word.surface
                # combined_furigana = word.feature.kana
                # combined_romaji = word.feature.pronBase
                # combined_word_info = word_info
                # aux_meanings = []

                # elif word.feature.pos1 == '助動詞':  # Auxiliary verb detection
                #     # Combine auxiliary verb with main verb
                #     combined_word += word.surface
                #     combined_furigana += word.feature.kana
                #     combined_romaji += word.feature.pronBase

                #     # Get auxiliary lemma and check for its meaning
                #     aux_lemma = word.feature.lemma
                #     aux_meaning = AUXILIARIES.get(aux_lemma)
                #     if aux_meaning:
                #         aux_meanings.append(aux_meaning)



                # word_info = get_word_info(word.surface)
                # # Store the current combined word before switching to the next word
                # if combined_word:
                #     word_dict[combined_word] = {
                #         "idseq": combined_word_info[0]['idseq'],
                #         "word": combined_word,
                #         "furigana": conv.do(combined_furigana),
                #         "romaji": kakasi.convert(combined_furigana)[0]["hepburn"],
                #         "definitions": modify_definitions(combined_word_info[0]['definitions'], aux_meanings)
                #     }

                # # Add the current word (non-verb) to the dictionary
                # if len(word_info) > 0:
                #     word_dict[word.surface] = {
                #         "idseq": word_info[0]['idseq'],
                #         "word": word_info[0]['word'],
                #         "furigana": word_info[0]['furigana'],
                #         "romaji": word_info[0]['romaji'],
                #         "definitions": word_info[0]['definitions']
                #     }

                # # Reset combined variables for future use
                # combined_word = ""
                # combined_furigana = ""
                # combined_romaji = ""
                # aux_meanings = []
                
                
        # Store any remaining combined word+auxiliary sequence after processing the line
        # if combined_word:
        #     word_dict[combined_word] = {
        #         "idseq": combined_word_info[0]['idseq'],
        #         "word": combined_word,
        #         "furigana": conv.do(combined_furigana),
        #         "romaji": kakasi.convert(combined_furigana)[0]["hepburn"],
        #         "definitions": modify_definitions(combined_word_info[0]['definitions'], aux_meanings)
        #     }