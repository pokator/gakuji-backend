from fastapi import Body, Depends, status, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.supabase import create_supabase_client
from app.dbmodels import User
from app.models import Token, CreateUser
from dotenv import load_dotenv
import os
from typing import Union

router = APIRouter(prefix="/auth", tags=["auth"])
load_dotenv()
stage = os.getenv("STAGE")

oauth2_scheme = (
    OAuth2PasswordBearer(tokenUrl="/auth/token")
    if stage == "local"
    else OAuth2PasswordBearer(tokenUrl="/dev/auth/token")
)
supabase = create_supabase_client()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


    try:

        data = supabase.auth.get_user(token)
        user_id = data.user.id
        print(supabase.auth.get_session())

        # First, try to find the user in the Caregiver table
        user = (
            supabase.from_("User").select("*").eq("id", user_id).execute()
        )
        if user.data:
            # Assuming you have a Caregiver model that accepts the row data
            return User(**user.data[0])

    except Exception as e:
        print(e)  # Handle exceptions appropriately
        raise credential_exception

async def get_current_session(token: str = Depends(oauth2_scheme)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    data = supabase.auth.get_user(token)
    print(supabase.auth.get_session())
    return supabase.auth.get_session()

@router.get("/current-user")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/create-user")
async def create_new_user(input: CreateUser, password: str = Body(...)):
    try:
    # check if user exists
        db_user = (
            supabase.from_("User").select("*").eq("email", input.email).execute()
        )
        if len(db_user.data) == 0:
            createdUser = supabase.auth.sign_up(
                {"email": input.email, "password": password}
            )
        else:
            # if the user exists, sign in, and use this and update it
            createdUser = supabase.auth.sign_in_with_password(
                {"email": input.email, "password": password}
            )
        newUserDict = input.model_dump()
        newUserDict["id"] = createdUser.user.id
        # I usually use upsert instead of update because i don't have to worry if an entry exists or not
        insert_user = supabase.from_("User").upsert({**newUserDict}).execute()
        return insert_user.data[0]
# at this point there is an empty user in the db; we need to access the id of that empty user and add the details that we want
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="User could not be created: " + str(e)
        )



@router.post("/token", response_model=Token)
async def set_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    data = supabase.auth.sign_in_with_password(
        {"email": form_data.username, "password": form_data.password}
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print(data.session.access_token)
    supabase.auth.set_session(data.session.access_token, data.session.refresh_token)
    return {"access_token": data.session.access_token, "token_type": "bearer"}

def return_session():
    return supabase.auth.get_session()
