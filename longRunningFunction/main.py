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
    print("Creating Supabase client")
    supabase: Client = create_client(api_url, key)
    print("Supabase client created")
    return supabase

jam = Jamdict(memory_mode=True)
kakasi = pykakasi.kakasi()
kakasi.setMode("J", "H")
kakasi.setMode("K", "H")
conv = kakasi.getConverter()
supabase = create_supabase_client()

def get_word_info(word):
    print(f"Looking up word: {word}")
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
        print(f"Processing entry: {entry}")
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
    print(f"Word info: {word_info}")
    return word_info

def process_tokenized_lines(lines):
    print(f"Processing tokenized lines: {lines}")
    word_dict = {}
    for line in lines:
        for word in line:
            print(f"Processing word: {word}")
            word_info = get_word_info(word)
            if len(word_info) > 0:
                word_dict[word] = word_info
    print(f"Word dictionary: {word_dict}")
    return word_dict

def lambda_handler(event, context):
    print(f"Processing event: {event}")
    try:
        for record in event['Records']:
            print(f"Processing record: {record}")
            print(f"Body content: {record['body']}")
            try:
                body = json.loads(record['body'])
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}")
                return {
                    'statusCode': 400,
                    'body': json.dumps('JSON decoding error: ' + str(e))
                }
            
            tokenized_lines = body['word_mapping']
            artist = body['artist']
            song = body['song']
            token = body['token']
            # Perform the long-running task
            word_mapping = process_tokenized_lines(tokenized_lines)
            print(f"Updating Supabase with token: {token}")
            supabase.auth.set_session(token)
            response = supabase.table("SongData").update({"word_mapping": word_mapping}).eq("title", song).eq("artist", artist).execute()
            print(f"Supabase update response: {response}")
            
        return {
            'statusCode': 200,
            'body': json.dumps('Long-running task completed successfully.')
        }
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps('Long-running task failed with error: ' + str(e))
        }


# mapping = {
#     "Records": [
#         {
#             "messageId": "059f36b4-87a3-44ab-83d2-661975830a7d",
#             "receiptHandle": "AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...",
#             "body": "{\"song\":\"Burning\",\"artist\":\"Hitsujibungaku\",\"word_mapping\":[[\"[\",\"Verse\",\"1\",\"[\"],[\"都合\",\"良い\",\"理想\",\"ばつ\",\"か\"],[\"並べ\",\"たって\",\"現実\",\"は\",\"暗い\"],[\"傷つく\",\"の\",\"が\",\"癖\",\"に\",\"なっ\",\"てる\"],[\"誰\",\"を\",\"許せ\",\"ない\",\"の\",\"？\"],[],[\"[\",\"Pre\",\"-\",\"Chorus\",\"[\"],[\"愛し\",\"たい\",\"もの\",\"から\",\"壊し\",\"て\"],[\"失う\",\"前\",\"に\",\"手放し\",\"て\",\"しまえ\",\"ば\"],[\"いい\",\"と\",\"思っ\",\"て\",\"い\",\"た\"],[],[\"[\",\"Chorus\",\"[\"],[\"But\",\"I\",\"'\",\"m\",\"crying\"],[\"今\",\"重たい\",\"幕\",\"が\",\"開け\",\"ば\"],[\"「\",\"ここ\",\"に\",\"気づい\",\"て\",\"」\",\"と\",\"(\",\"いて\",\"と\",\")\"],[\"声\",\"を\",\"枯らし\",\"ながら\"],[\"叫び\",\"続け\",\"て\",\"い\",\"た\"],[],[\"[\",\"Verse\",\"2\",\"[\"],[\"足り\",\"ない\",\"自分\",\"数え\",\"て\"],[\"比べ\",\"たって\",\"変われ\",\"ない\",\"や\"],[\"また\",\"ここ\",\"で\",\"立ち止まっ\",\"た\"],[\"どこ\",\"へ\",\"行け\",\"ば\",\"いい\",\"の\",\"？\"],[\"[\",\"Pre\",\"-\",\"Chorus\",\"[\"],[\"適当\",\"な\",\"理由\",\"探し\",\"て\"],[\"目\",\"を\",\"逸らし\",\"た\",\"って\",\"チラつい\",\"た\",\"あの\",\"日\",\"の\",\"夢\"],[\"奇跡\",\"なんて\",\"信じ\",\"ない\",\"って\",\"決め\",\"た\",\"の\",\"に\"],[\"どっ\",\"か\",\"望ん\",\"で\",\"しまう\",\"の\",\"を\"],[\"何\",\"度\",\"も\",\"掻き消し\",\"た\"],[],[\"[\",\"Chorus\",\"[\"],[\"But\",\"well\",\"I\",\"'\",\"m\",\"crying\"],[\"今\",\"眩しい\",\"光\",\"の\",\"中\",\"で\"],[\"どんな\",\"痛み\",\"さえ\"],[\"輝き\",\"に\",\"変え\",\"ながら\"],[\"命\",\"を\",\"燃やす\",\"の\"],[\"Lying\"],[\"完璧\",\"な\",\"舞台\",\"の\",\"裏\",\"で\"],[\"震える\",\"言葉\",\"を\"],[\"噛み殺し\",\"て\",\"も\"],[],[\"[\",\"Bridge\",\"[\"],[\"何に\",\"も\",\"なれ\",\"ない\",\"って\"],[\"誰\",\"より\",\"わかっ\",\"て\",\"いる\",\"みたい\",\"に\"],[\"吐き捨て\",\"た\"],[\"あと\",\"幾\",\"つ\",\"手\",\"に\",\"し\",\"たら\"],[\"満たさ\",\"れる\",\"ん\",\"だ\",\"？\"],[\"れん\",\"答え\",\"て\",\"涙\",\"が\",\"あ\",\"あ\",\"涙\",\"が\"],[\"[\",\"Chorus\",\"[\"],[\"Yeah\",\" ,\",\"I\",\"'\",\"m\",\"crying\"],[\"消え\",\"ない\",\"傷跡\",\"が\",\"明日\",\"を\"],[\"飲み込む\",\"前\",\"に\"],[\"暗闇\",\"の\",\"底\",\"から\"],[\"命\",\"を\",\"燃やす\",\"の\"],[\"Lying\"],[\"今\",\"眩しい\",\"光\",\"の\",\"中\",\"で\"],[\"どんな\",\"痛み\",\"さえ\"],[\"輝き\",\"に\",\"変え\",\"ながら\"],[\"命\",\"を\",\"燃やす\",\"の\"],[],[\"[\",\"Outro\",\"[\"],[\"この\",\"気持ち\",\"は\"],[\"誰\",\"に\",\"も\",\"言え\",\"ない\",\"Embed\"]],\"token\":\"eyJhbGciOiJIUzI1NiIsImtpZCI6IjdxaTlpTzk0djh5Q1dNVkQiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2xlb3J5b3dibGVmaXVlbnp6aXl0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIxMThmYmY3OS1kOWVmLTQ0NGItYTc4MS0wMWRlN2Y5NzE4YzIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzI0NTI3OTA2LCJpYXQiOjE3MjQ1MjQzMDYsImVtYWlsIjoic291cmF2QHV0ZXhhcy5lZHUiLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoic291cmF2QHV0ZXhhcy5lZHUiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiMTE4ZmJmNzktZDllZi00NDRiLWE3ODEtMDFkZTdmOTcxOGMyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3MjQ1MjQzMDZ9XSwic2Vzc2lvbl9pZCI6ImQ5ZDE5ZGM3LWE5NjgtNDY5ZS1iYjZhLWQ5YzcxYTk2Y2U2OSIsImlzX2Fub255bW91cyI6ZmFsc2V9.RIKaU-66n8s3Er0miJDjCXK61NCMZS-WZzLbyLDgbhE\"}",
#             "attributes": {
#                 "ApproximateReceiveCount": "1",
#                 "SentTimestamp": "1545082649183",
#                 "SenderId": "AIDAIENQZJOLO23YVJ4VO",
#                 "ApproximateFirstReceiveTimestamp": "1545082649185"
#             }
#         }
#     ]
# }



# process_lines(mapping, None)
