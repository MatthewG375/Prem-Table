"""Load data from the external Premier League API"""

from pathlib import Path
import requests
import pandas as pd
from PIL import Image

def load_fixture_data():
    """
    Generates data for the English Premier League\n
    No API key needed, free access available to the Fantasy PL API\n
    API used: https://fantasy.premierleague.com/api/
    """
    # base url for all FPL API endpoints
    base_url = 'https://fantasy.premierleague.com/api/'

    # get data from fixtures endpoint
    fix = requests.get(base_url+'fixtures/', timeout=10).json()

    # create fixtures dataframe
    fixtures = pd.json_normalize(fix)

    # get data from bootstrap-static endpoint
    r = requests.get(base_url+'bootstrap-static/', timeout=10).json()

    # create teams dataframe
    teams = pd.json_normalize(r['teams'])

    # join fixtures to teams
    df = pd.merge(
        left=fixtures,
        right=teams,
        left_on='team_a',
        right_on='id'
    )

    df2 = pd.merge(
        left=df,
        right=teams,
        left_on='team_h',
        right_on='id'
    )

    df2['status'] = 'SCHEDULED'
    df2.loc[df2['finished'], 'status'] = 'FINISHED'
    df2.loc[
        (df2['started']) & (~df2['finished']), 'status'
    ] = 'IN_PLAY'

    # create dictionary of team crests
    cur_dir = Path(__file__).resolve().parent
    logo_dir = cur_dir / '..' / '..' / '..' / 'Logos' / 'PL'

    team_crest = {
        row.id: Image.open(logo_dir / f"{row.id}.png").convert("RGBA")
        for row in teams.itertuples()
    }

    teams["colours"] = [
        img.info.get("primary_color") for img in team_crest.values()
    ]

    return teams, df2, team_crest
