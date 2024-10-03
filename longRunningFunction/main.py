from jamdict import Jamdict
import json
import pykakasi
import os
from supabase import Client, create_client
from dotenv import load_dotenv
import fugashi
import re

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
    'てしまう': 'completion', 'て': 'indicates continuing action​', 'で': 'indicates continuing action​' # Add more as needed based on specific usage scenarios
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
        print(f"Tokenizing line: {line}")
        tagged_line = tagger(line)
        # lyric_line = [word.surface for word in tagged_line]
        # lyric_list.append(lyric_line)
        # to_hiragana_list.append(conv.do(line))
        for word in tagged_line:
            print(word.surface, word.feature, word.pos, sep='\t')
        line_list.append(tagged_line)
    return line_list

def get_word_info(word):
    print(f"Looking up word: {word}")
    
    try:
        result = jam.lookup(word)
    except Exception as e:
        # print(f"Error in jamdict lookup: {e}")
        return []
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

def is_japanese(text):
    # Regex to match Hiragana, Katakana, Kanji, and Japanese punctuation
    return re.match(r'[\u3040-\u30FF\u4E00-\u9FFF\uFF00-\uFFEF]', text)

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
                print(f"Skipping non-Japanese token: {word.surface}")
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
                print(f"Word already processed: {word.surface}")
                new_line.append(word.surface)
                pos += 1
                continue

            print(f"Processing word: {word.surface}, Lemma: {word.feature.lemma}, POS1: {word.feature.pos1}")

            if word.feature.pos1 == '動詞' or word.feature.pos1 == '形容詞':  # Main verb detection
                word_info = get_word_info(word.feature.lemma)
                for info in word_info:
                    info['furigana'] = conv.do(word.surface)
                    info['romaji'] = kakasi.convert(word.surface)[0]["hepburn"]
                final_word = word.surface
                pos += 1
                while pos < len(line) and (line[pos].surface in AUXILIARIES or line[pos].feature.pos1 == '接尾辞'):
                    # we have found an auxiliary verb. Need to reflect in main verb's definitions, furigana, and romaji
                    aux_word = line[pos]
                    print(aux_word.surface, aux_word.feature, aux_word.pos, sep='\t')
                    final_word += aux_word.surface
                    aux_furigana = conv.do(aux_word.surface)
                    for info in word_info:
                        info['furigana'] += aux_furigana
                        info['romaji'] += kakasi.convert(aux_furigana)[0]["hepburn"]
                    aux_lemma = aux_word.feature.lemma
                    aux_meaning = AUXILIARIES.get(aux_lemma)
                    if aux_meaning:
                        for info in word_info:
                            info['definitions'] = modify_definitions(info['definitions'], [aux_meaning])
                    pos += 1
                word_dict[final_word] = word_info
                new_line.append(final_word)

            elif word.feature.pos1 == '接尾辞':  # Suffix detection
                print(word.surface, word.feature, word.pos, sep='\t')
                noun = line[pos - 1]
                suffix = word
                word_info = get_word_info(noun.surface + suffix.surface)
                word_dict[noun.surface + suffix.surface] = word_info
                new_line.pop()
                new_line.append(word_info)
                pos += 1
            else:  # For other parts of speech (nouns, adjectives, etc.)
                print(word.surface, word.feature, word.pos, sep='\t')
                word_info = get_word_info(word.surface)
                if len(word_info) > 0:
                    word_dict[word.surface] = word_info
                    new_line.append(word.surface)
                else :
                    print("surface lookup")
                    word_info = get_word_info(word.feature.lemma)
                    if len(word_info) > 0:
                        word_dict[word.surface] = word_info
                        new_line.append(word.surface)
                    else : 
                        print("creating dummy data")
                        temp_list = []
                        temp_properties = {'pos': [word.pos], 'definition': ['not found']}
                        temp_list.append({
                            "idseq": "none",
                            "word": word.surface,
                            "furigana": conv.do(word.surface),
                            "romaji": kakasi.convert(word.surface)[0]["hepburn"],
                            "definitions": temp_properties
                        })
                        word_dict[word.surface] = temp_list
                        new_line.append(word.surface)
                pos += 1

        lyrics.append(new_line)


    return word_dict, lyrics


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
            # print(f"Updating database for song: {song} by {artist}")
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




# cleaned_lyrics = """[星街すいせい「Stellar Stellar」歌詞]

# [Intro]
# だって僕は星だから
# Stellar-stellar

# [Verse 1]
# きっと君はもう気づいていた
# 僕の心の奥で描いた
# それが これから話す 陳腐なモノローグさ

# [Verse 2]
# ── ずっと言えない言葉があった
# 壊せない壁があったんだ ずっとさ
# ふっと香り立つ朝の匂いが
# どうしようもなく憎らしくて
# 部屋の隅で 膝を抱えて震えていた
# 太陽なんていらないから
# 明けないでいて ──

# [Pre-Chorus]
# その手を伸ばして 誰かに届くように
# 僕だって君と同じ 特別なんかじゃないから

# [Chorus]
# そうさ 僕は夜を歌うよ Stellar-stellar
# ありったけの輝きで
# 今宵 音楽は ずっと ずっと 止まない
# そうだ 僕がずっとなりたかったのは
# 待ってるシンデレラじゃないさ
# 迎えに行く王子様だ
# だって僕は星だから

# [Verse 3]
# なんて, ありふれた話なんだ
# 理想だけ書き連ねていた
# ノートの隅に眠る ほんのワンシーンだ
# ── きっとあの星も泣いてるんだ
# 明日なんて来ないままでいて ──

# [Pre-Chorus]
# その手を伸ばして 誰かに届くように
# 本当に大切なものは
# 目に見えないみたいなんだ

# [Chorus]
# そうさ 僕は夜を歌うよ Stellar-stellar
# ありのまま考えないで
# 今宵 音楽はきっときっと止まない
# そうだ 僕がずっとなりたかったのは
# あえかなヒロインじゃないさ
# 救いに行くヒーローだ

# [Bridge]
# 夢見がちなおとぎ話
# おとぎ話

# [Chorus]
# そうさ 僕は夜を歌うよ Stellar-stellar
# ありったけの輝きで
# 今宵 音楽はずっとずっと止まない
# そうさ 僕は愛を歌うよ Stellar-stellar
# 世界 宇宙の真ん中で
# 今宵 音楽はきっときっと止まない
# そうだ 僕がずっとなりたかったのは
# 待ってるシンデレラじゃないさ
# 迎えに行く王子様だ
# だって僕は星だから

# [Outro]
# そうだ僕は星だった
# Stellar-stellar"""

# cleaned_lyrics = """
# 欲しがって
# """
lines = split_into_lines(cleaned_lyrics)
tokenized_lines = tokenize(lines)
word_mapping, lyrics = process_tokenized_lines(tokenized_lines)

print(word_mapping)
print(lyrics)


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