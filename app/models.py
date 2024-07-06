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
    
class ManualAdd(BaseModel):
    title: str
    artist: str
    uuid: str | None = None
    lyrics: str