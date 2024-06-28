import os
from supabase import Client, create_client
from dotenv import load_dotenv
from functools import wraps


load_dotenv()

api_url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_API")


def create_supabase_client():
    supabase: Client = create_client(api_url, key)
    return supabase
