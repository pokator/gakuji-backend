from fastapi import FastAPI
from db.supabase import create_supabase_client, Client
from mangum import Mangum
from dotenv import load_dotenv
import os

supabase: Client = create_supabase_client()
load_dotenv()
stage = os.getenv("STAGE")
openapi_prefix = "" if stage == "local" else "/dev"

app = FastAPI(
    root_path=openapi_prefix,
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/users", summary="a sample summary for our get users endpoint")
async def get_current_caregiver():
    res = supabase.from_("users").select("*").execute()
    return res.data



handler = Mangum(app)
