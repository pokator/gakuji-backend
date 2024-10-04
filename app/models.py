from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class CreateUser(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str

class SpotifyAdd(BaseModel):
    uri: str | None = None
    refresh_token: str | None = None
    
class ManualAdd(BaseModel):
    title: str
    artist: str
    uuid: str | None = None
    lyrics: str
    
class WordAdd(BaseModel):
    word: str
    title: str
    artist: str
    list_id: str | None = None
    
class ListAdd(BaseModel):
    list_name: str
    type: str