from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class CreateUser(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
