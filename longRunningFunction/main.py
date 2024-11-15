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

# Mapping of basic hiragana/katakana to their dakuten and handakuten equivalents
DAKUTEN_MAP = {
    # Dakuten cases (濁点)
    'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
    'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
    'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
    'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
    'ハ': 'バ', 'ヒ': 'ビ', 'フ': 'ブ', 'ヘ': 'ベ', 'ホ': 'ボ',
    'カ': 'ガ', 'キ': 'ギ', 'ク': 'グ', 'ケ': 'ゲ', 'コ': 'ゴ',
    'サ': 'ザ', 'シ': 'ジ', 'ス': 'ズ', 'セ': 'ゼ', 'ソ': 'ゾ',
    'タ': 'ダ', 'チ': 'ヂ', 'ツ': 'ヅ', 'テ': 'デ', 'ト': 'ド',
}

HANDAKUTEN_MAP = {
    # Handakuten cases (半濁点)
    'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    'ハ': 'パ', 'ヒ': 'ピ', 'フ': 'プ', 'ヘ': 'ペ', 'ホ': 'ポ'
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
    # print(lines)
    return lines

# sometimes, the lyrics use the wrong characters for a dakuten'd character. This function checks for that and corrects it.
def dakuten_check(lines):
    result = []
    for line in lines:
        new_line = process_dakuten_handakuten(line)
        result.append(new_line)
    return result

def process_dakuten_handakuten(text: str) -> str:
    """
    Process a string to handle standalone dakuten (゛) and handakuten (゜) marks
    by combining them with the previous character if possible.
    
    Args:
        text: Input string that may contain standalone dakuten/handakuten marks
        
    Returns:
        Processed string with proper dakuten/handakuten combinations
    """
    result = []
    chars = list(text)
    i = 0
    
    while i < len(chars):
        if i < len(chars) - 1:
            current_char = chars[i]
            next_char = chars[i + 1]
            
            if next_char == '゙':  # Dakuten mark
                if current_char in DAKUTEN_MAP:
                    result.append(DAKUTEN_MAP[current_char])
                    i += 2
                else:
                    result.append(current_char)
                    result.append(next_char)
                    i += 2
            elif next_char == '゚':  # Handakuten mark
                if current_char in HANDAKUTEN_MAP:
                    result.append(HANDAKUTEN_MAP[current_char])
                    i += 2
                else:
                    result.append(current_char)
                    result.append(next_char)
                    i += 2
            else:
                result.append(current_char)
                i += 1
        else:
            result.append(chars[i])
            i += 1
            
    return ''.join(result)

def has_standalone_diacritics(text: str) -> bool:
    """
    Check if a string contains any standalone dakuten or handakuten marks.
    
    Args:
        text: Input string to check
        
    Returns:
        True if standalone dakuten or handakuten is found, False otherwise
    """
    return '゙' in text or '゚' in text
    


'''
There is a race condition occurring in this code. I believe the tagger is not thread safe. However, the only way I know at the moment is to use the print.
'''
def tokenize(lines):
    # print("Tokenizing lyrics.")
    line_list = []
    for line in lines:
        print(f"Tokenizing line: {line}")
        tagged_line = tagger(line)
        for word in tagged_line:
            print(f"Tokenizing word: {word.surface}, Lemma: {word.feature.lemma}, POS1: {word.feature.pos1}")
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
    try:
        result = jam.lookup(word)
    except Exception as e:
        return []
    word_info = []
    for entry in result.entries: 
        # print(f"Processing entry: {entry}")
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
        
        # limit definitions to 3
        for sense in entry.senses[:3]:
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
    return word_info[:4]

def is_japanese(text):
    # Regex to match Hiragana, Katakana, Kanji, and Japanese punctuation
    return re.match(r'[぀-ヿ一-鿿＀-￯]', text)

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
                
                full_word_data = {
                    "root": None,
                    "suffixes": None,
                    "composite": temp_list
                }
                word_dict[word.surface] = full_word_data
                new_line.append(word.surface)
                pos += 1
                continue
            
            if word.surface in word_dict:
                #efficiency modification - most songs will repeat words, why look them up again
                new_line.append(word.surface)
                pos += 1
                continue

            print(f"Processing word: {word.surface}, Lemma: {word.feature.lemma}, POS1: {word.feature.pos1}")
            
            # Verbs, adjectives, adjectival nouns.
            if (word.feature.pos1 == '動詞' 
                or word.feature.pos1 == '形容詞' 
                or (word.feature.pos1 == '名詞' and word.feature.pos3 == '形状詞可能')
                or word.feature.pos1 == '形状詞'
                or word.feature.pos1 == '形容詞' or word.feature.pos1 == '助動詞'):
                
                
                #retrieve definition from dictionary.
                word_info = get_word_info(word.feature.lemma)
                for info in word_info:
                    info['furigana'] = conv.do(word.surface)
                    info['romaji'] = kakasi.convert(info['furigana'])[0]["hepburn"]
                
                base_word_data = deepcopy(word_info)
                
                base_furigana = conv.do(word.feature.lemma)
                base_romaji = kakasi.convert(base_furigana)[0]["hepburn"]
                
                for info in base_word_data:
                    info['word'] = word.feature.lemma
                    info['furigana'] = base_furigana
                    info['romaji'] = base_romaji
                    
                for info in word_info:
                    info['word'] = word.surface
                    
                final_word = word.surface
                pos += 1
                suffix_data = []
                #continue through the line to check for auxiliaries. 
                while pos < len(line) and ((line[pos].surface in AUXILIARIES and line[pos].feature.pos1 == '助動詞') or line[pos].feature.pos1 == '接尾辞' or line[pos].surface in ['て', 'で', 'ん','ちゃ']):
                    # we have found a bound auxiliary. Need to reflect in main verb's definitions, furigana, and romaji
                    aux_word = line[pos]
                    final_word += aux_word.surface
                    aux_furigana = conv.do(aux_word.surface)
                    aux_romaji = kakasi.convert(aux_word.surface)[0]["hepburn"]
                    for info in word_info:
                        info['furigana'] += aux_furigana
                        info['romaji'] += aux_romaji
                        info['word'] += aux_word.surface
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
                    composite_word_data = word_info
                    full_word_data = {
                        "root": word_dict[noun.surface]["composite"],
                        "suffixes": word_dict[noun.surface]["suffixes"],
                        "composite": composite_word_data
                    }
                    word_dict[noun.surface + suffix.surface] = full_word_data
                    new_line.pop()
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
                # print(f"Processing particle: {word.surface}")
                # if word.surface == 'は':
                #     temp_list = []
                #     temp_properties = {'pos': ["Particle"], 'definition': ['topic marker']}
                #     temp_list.append({
                #         "idseq": "none",
                #         "word": word.surface,
                #         "furigana": "は",
                #         "romaji": "ha",
                #         "definitions": temp_properties
                #     })
                    
                #     full_word_data = {
                #         "root": None,
                #         "suffixes": None,
                #         "composite": temp_list
                #     }
                #     word_dict[word.surface] = full_word_data
                #     new_line.append(word.surface)
                #     pos += 1
                #     continue
                word_info = get_word_info(word.surface, type="particle")
                # print(f"Particle info retrieved: {word_info}")
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
            checked_lines = dakuten_check(lines)
            tokenized_lines = tokenize(checked_lines)
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
# やり残した鼓動が この夜を覆って
# 僕らを包んで 粉々になる前に
# 頼りなくてもいい その手を
# この手は 自分自身のものさ
# 変わらないはずはないよ 手を伸ばして
# """
# lines = split_into_lines(cleaned_lyrics)
# checked_lines = dakuten_check(lines)
# tokenized_lines = tokenize(checked_lines)
# word_mapping, lyrics = process_tokenized_lines(tokenized_lines)
# hiragana_lines = convert_to_hiragana(lyrics)
# print(word_mapping)
# print(lyrics)


# やり残した鼓動が この夜を覆って



# pipe to a file
# with open("word_mapping.json", "w") as f:
#     json.dump(word_mapping, f, indent=4)