
# Gakuji-Backend



## Using Pipenv:

Install pipenv if you don't have it: `pip3 install pipenv`



To locally run the app or use pipenv start by activating your pipenv shell: `pipenv shell`



Install all dependencies: `pipenv install`



To install a new dependency: `pipenv install [dependency]`



Think of pipenv like npm - it's a package manager for python.



## Running the app:

Make sure you're in a pipenv virtual environment ( `pipenv shell` ) and run ```uvicorn app.main:app --reload```

## Generating types
To supabase db models, **make sure** you are in the home ( Cura-Backend ) directory.

**Then, run**  `python -m scripts.genTypes`


You may have to run `python3 -m scripts.genTypes` depending on your path.

This command automatically generates a new `dbmodels.py` file in the `app` directory, that contains all of the pydantic models.

**Be sure to run this command any time you make any changes to supabase, such as changing/adding/removing columns or adding/deleting tables.**

## Env Files
**When making a change to the env file, be sure to run** `python scripts/genEnvSample.py`
This generates a new `env.example` file, which helps those that are new to the codebase see exactly what env vars they need.
