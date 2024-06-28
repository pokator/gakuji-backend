from fastapi import FastAPI
from db.supabase import create_supabase_client, Client
from mangum import Mangum


app = FastAPI()

supabase: Client = create_supabase_client()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/users", summary="a sample summary for our get users endpoint")
async def get_current_caregiver():
    res = supabase.from_("users").select("*").execute()
    return res.data


handler = Mangum(app)
