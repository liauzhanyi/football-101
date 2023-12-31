import requests
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

HEADER = {
        "x-rapidapi-host" : os.getenv("RAPIDAPI_HOST"),
        "x-rapidapi-key" : os.getenv("RAPIDAPI_KEY")
}

LEAGUES_ID = {
    "Premier League" : 39,
    "La-Liga" : 140
}

############################
##### Helper Functions #####
############################
def make_url(endpoint):
    return f"https://api-football-v1.p.rapidapi.com/v3{endpoint}"

def get_api_response(endpoint, args:dict={}, headers=HEADER, method:str="GET"):
    url = make_url(endpoint)
    response = requests.request(method, url, headers=headers, params=args)
    return response

########################
###### Endpoints #######
########################

###################
##=== Leagues ===##
###################
def get_leagues_data():
    df = pd.DataFrame()

    ## get leagues data from api
    r = get_api_response("/leagues")

    ## if response is successful, convert to pandas df
    if r.status_code == 200:
        ## unnest top layer json response, convert to pandas df
        df = pd.json_normalize(r.json()["response"])
        
        ## unnest seasons column (list of dicts)
        df = df.explode("seasons").reset_index(drop=True)
        
        ## unnest seasons column (dict)
        df = df.join(pd.json_normalize(df["seasons"])).drop(columns=["seasons"])
        
        ## select columns
        df = df[["league.id", "league.name", "league.type", "start", "end"]]
        
        ## convert to datetime
        df["start"] = pd.to_datetime(df["start"])
        df["end"] = pd.to_datetime(df["end"])
        
        ## rename columns
        df.columns = ["id", "name", "type", "start", "end"]

    return df

#####################
##=== Standings ===##
#####################
def get_league_standing(season:int, league_id:int=None, team_id:int=None):
    df = pd.DataFrame()
    
    ## set args
    args = {"season" : season}

    if league_id != None:
        args["league"] = league_id

    if team_id != None:
        args["team"] = team_id

    ## get standings data from api
    r = get_api_response("/standings", args=args)

    ## if response is successful, convert to pandas df
    if r.status_code == 200:
        ## unnest top layer json response, convert to pandas df
        response_list = pd.json_normalize(r.json()["response"])["league.standings"][0][0]
        df = pd.DataFrame(response_list)

        ## select columns
        df = df.drop(columns=["group", "status", "description", "update"])

        ## extract team name and id from team column
        df["id"] = df["team"].apply(lambda x: x["id"])
        df["team"] = df["team"].apply(lambda x: x["name"])

        ## unnest columns
        def expand_col(col):
            return pd.json_normalize(col).add_prefix(f"{col.name}.")
        
        df = df.join(expand_col(df["all"])).drop(columns=["all"])
        df = df.join(expand_col(df["home"])).drop(columns=["home"])
        df = df.join(expand_col(df["away"])).drop(columns=["away"])

    return df

## standings for specific leagues
def get_premier_league_standing(season:int):
    return get_league_standing(season, LEAGUES_ID["Premier League"])

def get_laliga_standing(season:int):
    return get_league_standing(season, LEAGUES_ID["La-Liga"])

####################
##=== Fixtures ===##
####################

def get_fixtures(league_id:int):
    df = pd.DataFrame()
    num_fixtures = 20

    ## set args
    args = {"league" : league_id, "next" : num_fixtures}

    ## get fixtures data from api
    r = get_api_response("/fixtures", args=args)

    ## if response is successful, convert to pandas df
    if r.status_code == 200:
        ## unnest top layer json response, convert to pandas df
        df = pd.json_normalize(r.json()["response"])
        
        ## select columns
        df = df[['fixture.id', 'fixture.timezone', 'fixture.date', 
                 'fixture.venue.name', 'fixture.venue.city', 
                 'league.season', 'league.round', 
                 'teams.home.id', 'teams.home.name', 'teams.away.id', 'teams.away.name']]
        
        ## convert to datetime
        df["fixture.date"] = pd.to_datetime(df["fixture.date"], utc=True)
        ## TODO: convert to local time using fixture.timezone
        df = df.drop(columns=["fixture.timezone"])
        
        ## rename columns
        df.columns = ['id', 'date', 'venue', 'city', 'season', 'round', 
                      'home.id', 'home.name', 'away.id', 'away.name']

    return df

def get_premier_league_fixtures():
    return get_fixtures(LEAGUES_ID["Premier League"])
