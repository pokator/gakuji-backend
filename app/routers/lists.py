from fastapi import Body, Depends, status, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.supabase import create_supabase_client
from app.dbmodels import User
from app.models import WordAdd, ListAdd
from app.routers.song import get_kanji_data, create_word_return
from dotenv import load_dotenv
import os
import json
from app.routers.auth import get_current_user

router = APIRouter(prefix="/lists", tags=["lists"])
load_dotenv()
stage = os.getenv("STAGE")
oauth2_scheme = (
    OAuth2PasswordBearer(tokenUrl="/auth/token")
    if stage == "local"
    else OAuth2PasswordBearer(tokenUrl="/dev/auth/token")
)

supabase = create_supabase_client()

#get all lists for a particular user from the List table in supabase
@router.get("/get-lists")
async def get_lists(user: User = Depends(get_current_user)):
    response = supabase.table("List").select("list_name, type, id").eq("user_id", user.id).execute()
    return response

#add a new list to the List table in supabase
@router.post("/add-list")
async def add_list(listModel: ListAdd, user: User = Depends(get_current_user)):
    list_name = listModel.list_name
    type = listModel.type
    if list_name is None or type is None:
        return {"message": "Missing information. Please try again."}
    else:
        response = supabase.table("List").insert({"list_name": list_name, "type": type, "user_id": user.id}).execute()
        return response
    
#delete a list from the List table in supabase
@router.delete("/delete-list")
async def delete_list(list_id: str, user: User = Depends(get_current_user)):
    response = supabase.table("List").delete().eq("id", list_id).eq("user_id", user.id).execute()
    return response

# get a particular list given its id (list is stored in ListItem table)
@router.get("/get-a-list")
async def get_a_list(list_id: str, user: User = Depends(get_current_user)):
    response = supabase.table("ListItem").select("title, artist, value").eq("list_id", list_id).execute()
    return response

# get all lists of a particular type (kanji or word) from List table
@router.get("/get-type-lists")
async def get_type_lists(type: str, user: User = Depends(get_current_user)):
    response = supabase.table("List").select("list_name, type, id").eq("user_id", user.id).eq("type", type).execute()
    return response

def list_has_word(list_id: str, word: str):
    in_my_table = supabase.table("ListItem").select("*", count="exact").eq("list_id", list_id).eq("value", word).execute()
    count = in_my_table.count
    if count > 0:
        return True
    else:
        return False
    
#check all lists of a particular type for a particular user for a particular word and return all lists that DO NOT contain the word
@router.get("/check-all-lists")
async def check_all_lists(word: str, type: str, user: User = Depends(get_current_user)):
    response = supabase.table("List").select("list_name, id").eq("user_id", user.id).eq("type", type).execute()
    lists_without_word = []
    for list in response.data:
        if not list_has_word(list["id"], word):
            lists_without_word.append(list)
    return lists_without_word


#delete a word from a list
@router.delete("/delete-word")
async def delete_word(word: str, list_id: str, user: User = Depends(get_current_user)):
    response = supabase.table("ListItem").delete().eq("list_id", list_id).eq("value", word).execute()
    return response

#add word to a particular list. Words are added as idseqs, Kanji as themselves.
@router.post("/add-word")
async def add_word(wordObject: WordAdd, user: User = Depends(get_current_user)):
    word = wordObject.word
    artist = wordObject.artist
    title = wordObject.title
    list_id = wordObject.list_id
    if word is None or artist is None or list_id is None or title is None:
        return {"message": "Missing information. Please try again."}
    else:
        in_my_table = supabase.table("ListItem").select(count="exact").eq("title", title).eq("artist", artist).eq("list_id", list_id).eq("value", word).execute().count
        if in_my_table > 0:
            return {"message": "Lyric already saved to this list."}
        else:
            response = supabase.table("ListItem").insert({"title": title, "artist": artist, "list_id": list_id, "value": word}).execute()
            return response
        
#get the data for a particular word or kanji from a list, depending on the length of the value itself. You are given the value for the word or kanji, and the length of the string determines whether you use get_kanji_data (for a one-length string) or get_word (for a string of length > 1)
@router.get("/get-word-data")
async def get_word_data(value: str, user: User = Depends(get_current_user)):
    if len(value) == 0:
        return {"message": "Missing information. Please try again."}
    
    if len(value) == 1:
        return get_kanji_data(value)
    else:
        return create_word_return(value)