"""Code to generate a bar graph of English Premier League teams who can still qualify for Europe"""

# importing package
from datetime import datetime, timezone
import os
import time
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.ticker as plticker
from matplotlib.ticker import AutoMinorLocator
import matplotlib.pyplot as plt
import numpy as np
import requests
import pandas as pd
from dotenv import load_dotenv
from PIL import Image

pd.set_option('display.max_columns', None)


def generate_efl_data():
    """Generate data for the EFL Championship"""

    # Load API Key from .env file in the same location as this file.
    # API used: https://www.football-data.org/
    load_dotenv()
    football_data_key = os.getenv('FOOTBALL_DATA_KEY')
    pd.set_option('future.no_silent_downcasting', True)

    url = 'https://api.football-data.org/v4/'
    headers = { 'X-Auth-Token': football_data_key }

    fdorg = requests.get(url+'competitions/ELC/matches?season=2024',
                         headers=headers, timeout=10).json()
    fixtures = pd.json_normalize(fdorg['matches'])

    fixtures = fixtures.rename(columns={'homeTeam.id': 'team_h',
                                        'awayTeam.id': 'team_a', 
                                        'score.fullTime.home': 'team_h_score', 
                                        'score.fullTime.away': 'team_a_score',
                                        'status': 'finished',
                                        'awayTeam.name': 'name_x',
                                        'homeTeam.name': 'name_y',
                                        'utcDate': 'kickoff_time'
                                        })
    fixtures = fixtures.replace({'FINISHED': True,
                                 'TIMED': False,
                                 'IN_PLAY': False,
                                 'PAUSED': False,
                                 'SCHEDULED': False})

    teams = requests.get(url+'competitions/ELC/standings', headers=headers, timeout=10).json()
    teams = pd.json_normalize(teams['standings'], 'table')
    teams = teams.rename(columns={'team.tla': 'short_name'})
    teams.sort_values('team.name', inplace=True)

    team_colours = ['#009ee0', '#e21a23', '#690039', '#035da9',
                    '#009edc', '#8d8d8d', '#f8b100', '#ffdf1a',
                    '#f28c00', '#e40f1b', '#00367a', '#00a650',
                    '#fff500', '#143f2a', '#323c9c', '#0799d5',
                    '#1a59a3', '#ee2227', '#4681cf', '#e1393e',
                    '#e20025', '#030303', '#fff002', '#173675']
    teams['colours'] = team_colours
    teams = teams.rename(columns={'team.id': 'id'})

    # replace Sheffield Wednesday short name, as it is the same as Sheffield United's
    teams.loc[teams.id==345, 'short_name'] = "SHW"

    # create dictionary of team crests
    team_crest = {}
    for row in teams.itertuples():
        crest_id = f"https://raw.githubusercontent.com/MatthewG375/Prem-Table/refs/heads/main/Logos/ELC/{row.id}.png"
        loaded_crest = Image.open(requests.get(crest_id,
                                               stream=True,
                                               timeout=10).raw).convert('RGBA')
        team_crest[row.id] = loaded_crest

    fix_started = []
    home_diff = []
    away_diff = []

    for row in fixtures.itertuples():
        str_time = row.kickoff_time
        fix_time = datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        cur_time = datetime.now(timezone.utc)

        if row.finished == "POSTPONED":
            fixtures.at[row.Index, 'finished'] = False
            fixtures.at[row.Index, 'kickoff_time'] = "None"

        if cur_time > fix_time:
            fix_started.append(True)
        else:
            fix_started.append(False)

        # determine difficulty of the away team by league table position
        hpos = teams.loc[teams.id == row.team_a, 'position'].item()
        if hpos <= 4:
            away_diff.append(5)
        elif 5 <= hpos <= 8:
            away_diff.append(4)
        elif 9 <= hpos <= 20:
            away_diff.append(3)
        else:
            away_diff.append(2)

        # determine difficulty of the home team by league table position
        apos = teams.loc[teams.id == row.team_h, 'position'].item()
        if apos <= 4:
            home_diff.append(5)
        elif 5 <= apos <= 8:
            home_diff.append(4)
        elif 9 <= apos <= 20:
            home_diff.append(3)
        else:
            home_diff.append(2)

    fixtures['team_h_difficulty'] = away_diff
    fixtures['team_a_difficulty'] = home_diff
    fixtures['started'] = fix_started
    fixtures['finished_provisional'] = fixtures['finished']

    return teams, fixtures, team_crest


def generate_data():
    """A function to generate the 'teams' and 'df2' dataframes for the EPL"""
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

    # add team colours to dataframe
    team_colours = ['#e20814', '#91beea', '#ca0b17', '#b60501', '#004a9b',
                    '#021581', '#004b97', '#024593', '#282624', '#0c3e94',
                    '#13428d', '#b30011', '#b1d4fa', '#dc1116', '#0d0805',
                    '#f4031c', '#d20911', '#152055', '#7d2d3f', '#feb906']
    teams['colours'] = team_colours

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

    # create dictionary of team crests
    team_crest = {}
    for row in teams.itertuples():
        crest_id = f"https://raw.githubusercontent.com/MatthewG375/Prem-Table/refs/heads/main/Logos/PL/{row.id}.png"
        crest_load = Image.open(requests.get(crest_id, stream=True, timeout=10).raw).convert('RGBA')
        # crest_name = f"Logos/Colour/{row.id}.png"
        # crest_load = Image.open(crest_name)
        team_crest[row.id] = crest_load

    return teams, df2, team_crest


def get_team_record(team_id, df2):
    """Function to get teams record from their ID"""
    # team_name = teams.loc[teams.id == team_id, 'name'].values[0]

    record_df = df2[ (df2['team_h'] == team_id) | (df2['team_a'] == team_id) ]
    record_df = record_df.reset_index()
    # record_df[['name_y','team_h_score', 'team_a_score', 'name_x']].head(11)

    w = 0
    d = 0
    l = 0

    gd = 0
    gf = 0

    for row in record_df.itertuples():
        # print(row['name_y'],row['team_h_score'], row['team_a_score'], row['name_x'])
        if row.team_h == team_id and (row.team_h_score > row.team_a_score):
            w += 1
            # print("home win")
        elif row.team_h == team_id and (row.team_h_score == row.team_a_score):
            d += 1
            # print("home draw")
        elif row.team_h == team_id and (row.team_h_score < row.team_a_score):
            l += 1
            # print("home loss")

        if row.team_a == team_id and (row.team_a_score > row.team_h_score):
            w += 1
            # print("away win")
        elif row.team_a == team_id and (row.team_a_score == row.team_h_score):
            d += 1
            # print("away draw")
        elif row.team_a == team_id and (row.team_a_score < row.team_h_score):
            l += 1
            # print("away loss")

    for row in record_df.itertuples():
        # if team is at home, and the game has happened(==), add home goals and subtract away goals
        if row.team_h == team_id and (row.team_h_score == row.team_h_score):
            gd += row.team_h_score
            gd -= row.team_a_score
            gf += row.team_h_score
        # if team is away, and the game has happened(==), subtract home goals and add away goals
        elif row.team_a == team_id and (row.team_h_score == row.team_h_score):
            gd -= row.team_h_score
            gd += row.team_a_score
            gf += row.team_a_score

    gd = int(gd)
    if gd >= 0:
        gd = str(f'+{gd}')
    else:
        gd = str(gd)

    # fixture is in the future if it has not: Finished, Provisionally Finished, or Started
    remaining_df = df2.loc[ ((~df2['finished']) & (~df2['finished_provisional']) &
                             ( (df2['started'] == False) | (df2['started'].isnull()) )) &
                            ((df2['team_h'] == team_id) | (df2['team_a'] == team_id)) ]
    remaining_df = remaining_df.reset_index()

    pts = int((w*3)+(d))

    # when testing smaller, - amount of removed fixtures here
    left = int(len(remaining_df))
    max_theory = int(pts + 3*left)

    # ply = int(w+d+l)
    # print(f"{team_name} Record: Played: {ply}, Won: {w}, Draw: {d}, Loss: {l},"
    #       f"Points: {pts}, Goal Difference: {gd}, Remaining: {left}")

    return pts, max_theory, gd, gf

def putfirst(df, i):
    "Moves the specified index 'i' in dataframe 'df' to the top of the dataframe"
    df["new"] = range(1,len(df)+1)
    df.loc[df.index==i, 'new'] = 0
    df.sort_values("new", inplace=True)
    df.drop('new', axis=1)


def get_remaining_fixtures(team_id, df2):
    """Takes a team ID and returns a pandas dataframe of remaining fixtures."""
    filtered_df = df2.loc[ ((~df2['finished']) & (~df2['finished_provisional']) &
                            ( (df2['started'] == False) | (df2['started'].isnull()) )) &
                           ((df2['team_h'] == team_id) | (df2['team_a'] == team_id)) ]
    filtered_df = filtered_df.reset_index()
    #filtered_df[['name_y','team_h_score', 'team_a_score', 'name_x']]

    remaining_fix = []
    fix_location = []
    opposition = []
    opp_name = []
    diff = []

    for row in filtered_df.itertuples():
        if row.team_h == team_id:
            location = "H"
            oppos = row.team_a
            tname = row.name_x
            try:
                opp_diff = row.team_h_difficulty
            except AttributeError:
                opp_diff = 3
        else:
            location = "A"
            oppos = row.team_h
            tname = row.name_y
            try:
                opp_diff = row.team_a_difficulty
            except AttributeError:
                opp_diff = 3

        if (row.kickoff_time is None) or (row.kickoff_time == "None"):
            newdate = "TBC"
            opp_diff = "TBC"
        else:
            date = row.kickoff_time[5:10]
            left, right = date.split('-')
            newdate = f"{location} {right}-{left}"
        # print(newdate)
        remaining_fix.append(newdate)
        fix_location.append(location)
        opposition.append(oppos)
        opp_name.append(tname)
        diff.append(opp_diff)

    # print(remaining_fix)
    filtered_df['remaining_fixtures'] = remaining_fix
    filtered_df['fixture_location'] = fix_location
    filtered_df['opposition_id'] = opposition
    filtered_df['opposition_name'] = opp_name
    filtered_df['opposition_difficulty'] = diff

    filtered_df = filtered_df[['remaining_fixtures', 'fixture_location',
                               'opposition_id', 'opposition_name', 'opposition_difficulty']]

    for row in filtered_df.itertuples():
        if row.remaining_fixtures == "TBC":
            putfirst(filtered_df, row.Index)

    # testing for smaller image size, need to -10 to remaining as well
    # filtered_df.drop(filtered_df.tail(10).index, inplace=True)


    return filtered_df


def gen_additional_data(teams, df2):
    '''Generates additional data for each team'''
    # add max points row, goal difference, and goals scored to dataframe (for H2H tiebreakers)
    max_points = []
    gd = []
    gf = []
    for team in teams.itertuples():
        _points, max_pts, goal_difference, goals_for = get_team_record(team.id, df2)
        max_points.append(max_pts)
        gd.append(int(goal_difference))
        gf.append(goals_for)

    teams['max_points'] = max_points
    teams['goal_difference'] = gd
    teams['goals_for'] = gf
    teams = teams.sort_values(by=['max_points', 'goal_difference', 'goals_for'],
                            ascending=[False, False, False])

    # make dataframe with all teams in, in order to remove extraneous teams from main dataset
    teams_all = teams.copy()

    return teams, teams_all


def points_deductions(row, points, max_pts):
    '''Calculate points deductions for the current team'''
    # Calculate points deductions
    if row == 356: # SHU 2pt deduction
        points -= 2
        max_pts -= 2
        return points, max_pts
    else:
        return points, max_pts


def set_title_and_labels(title_text, total_y, teams):
    '''Set the title and axis labels'''
    # adjust label size when image gets smaller
    x_labelsize = 17
    y_labelsize = 17

    if total_y < 40:
        y_labelsize = 15

    if len(teams.index) < 10:
        x_labelsize = 15

    plt.title(title_text, size=16, fontname='sans-serif', weight='semibold')

    plt.xlabel("Teams in order of highest possible points total   ",
            labelpad=15, size=x_labelsize, fontname='sans-serif', weight='semibold', loc='center')
    plt.ylabel("Points and remaining fixures in chronological order",
            labelpad=15, size=y_labelsize, fontname='sans-serif', weight='semibold')
    plt.xticks(rotation=60, color='w')

    return y_labelsize


def generate_table(competition: str, lines_to_generate: list, title_text_1: str,
                   file_text: str, pos_one=1, pos_two=20):
    """Function to generate the visualization of the table

    Keyword Arguments:
        competition -- a string denoting which competition to generate the graph for ('PL' or 'ELC)

        lines_to_generate -- a 2D list containing all lines to be shown on the image 
        ( [[position, 'message to show on line', line colour], ...] )
        include __ in the message to replace with the points value of the line

        title_text_1 -- the first line of the image title

        file_text -- the name of the file

        pos_one -- the first position in the table to show on the image (default 1)

        pos_two -- the second position in the table to show on the image (default 20)
    """
    origin_time = time.time()

    # convert competition code into correct data load
    if competition == 'PL':
        teams, df2, team_crest = generate_data()
    elif competition == 'ELC':
        teams, df2, team_crest = generate_efl_data()
    else:
        raise ValueError('Only PL or ELC is allowed')
    teams, teams_all = gen_additional_data(teams, df2)

    # convert table position to usable numbers
    remove_from_top = pos_one - 1
    remove_from_bottom = len(teams_all.index) - pos_two

    teams.drop(teams.tail(remove_from_bottom).index, inplace=True)
    teams.drop(teams.head(remove_from_top).index, inplace=True)

    # create the canvas and general constants
    starting_x = 18
    step_x = 0.8869
    default_x = 20

    x_offset = {
        24: 0.0120,
        23: 0.0125,
        22: 0.0135,
        21: 0.0140,
        20: 0.0150,
        19: 0.0160,
        18: 0.0175,
        17: 0.0185,
        16: 0.0200,
        15: 0.0210,
        14: 0.0225,
        13: 0.0240,
        12: 0.0260,
        11: 0.0280,
        10: 0.0305,
        9: 0.0330,
        8: 0.0395,
        7: 0.0440,
        6: 0.0550,
        5: 0.0660,
        4: 0.0825,
        3: 0.1130,
        2: 0.1750 }

    starting_y = 26
    step_y = 0.2601
    default_y = 100

    barwidth = 0.7
    theory_min = 114

    data_time = time.time()

    plt.figure(figsize=(starting_x, starting_y))

    # Fixture Difficulty Colours
    colours = {2: '#b5f7c6', 3: '#e7e7e7', 4: '#f5a1b2', 5: '#f47272', 'TBC': '#a1a1a1'}

    # loop for every team that needs a bar
    for row in teams.itertuples():
        points, max_pts, goal_difference, _goals_for = get_team_record(row.id, df2)
        goal_difference = f'GD {goal_difference}'

        # Calculate points deductions
        points, max_pts = points_deductions(row.id, points, max_pts)

        # update lowest theoretical points total if new teams is lower
        theory_min = min(theory_min, points)

        # create bar for current points, with team colour
        cpts = plt.bar(row.short_name, points,
                       color=row.colours, edgecolor=row.colours, width=barwidth)
        bot = points

        # loop for every remaining fixture for current team: row.id
        fixtures_remaining = get_remaining_fixtures(row.id, df2)
        for fx in fixtures_remaining.itertuples():

            dif_col = colours[fx.opposition_difficulty]
            cur_bar = plt.bar(row.short_name, 3, bottom=bot,
                              color=dif_col, edgecolor="#808080", lw=1.5, width=barwidth)
            perma_y = points

            # positioning of image and text in upcoming fixture bar
            for bar_im in cur_bar:
                x,y = bar_im.get_xy()
                w, h = bar_im.get_width(), bar_im.get_height()

                xleft = x + w/8.5
                xright = x + w/1.121212
                ybot = y + h/3.5
                ytop = y + h/1.09

                # plot the team logo and the fixture date
                imdis =  team_crest[fx.opposition_id].convert('LA')
                plt.imshow(imdis, extent=[xleft, xright, ybot, ytop], aspect='auto', zorder=2)

                plt.text(x+w/2, y+0.18, fx.remaining_fixtures,
                         ha='center', fontname='sans-serif', c="#757171",
                         weight='semibold', size='x-small')

            # goal difference label
            plt.text(x+w/2, perma_y-0.5, goal_difference,
                     ha='center', fontname='sans-serif', c='white',
                     weight='semibold', size='x-small')

            # increment counter by 3, as each fixture has a possible value of 3 points
            bot += 3

        # remove bottom box outline
        for bar_a in cpts:
            x,y = bar_a.get_xy()
            w, h = bar_a.get_width(), bar_a.get_height()
            #print(x,y,w,h)
            plt.bar(x+w/2, color=bar_a.get_facecolor(),
                    lw=1.5, height=h+0.01, edgecolor=row.colours, width=barwidth)

    # axis is slightly shorter than the number of teams being plotted
    ax_width = len(teams.index) - 0.5


    # offset y axis if bottom would fall on a multiple of 5, for readability
    if (theory_min - 3) % 5 == 0:
        theory_min -= 1

    # get the max and min points, then add padding to graph to improve readability
    theory_max = teams['max_points'].max()
    total_y = int((theory_max + 2) - (theory_min-3))

    # if y height under 30, set height to 30 for better visual
    if total_y < 32:
        total_y = 32
        theory_min = theory_max - 30

    # change limits for improved readability, and set ticks between new limits
    plt.ylim((theory_min-3), (theory_max + 2))
    plt.yticks(np.arange((theory_min-2), (theory_max + 2), 1))

    # correct the plot size
    new_x = starting_x - (step_x * (default_x - len(teams.index)))
    new_y = starting_y - (step_y * (default_y - total_y))

    plt.gcf().set_size_inches(new_x, new_y)

    # choose correct x offset from x_offset dict
    main_offset = x_offset[len(teams.index)]
    plt.margins(x=main_offset, tight=None)

    # format position numbers
    title_pos = [remove_from_top+1, len(teams_all.index) - remove_from_bottom]
    for i, x in enumerate(title_pos):
        if x == 1:
            title_pos[i] = '1st'
        elif x == 2:
            title_pos[i] = '2nd'
        elif x == 3:
            title_pos[i] = '3rd'
        elif x == 21:
            title_pos[i] = '21st'
        elif x == 22:
            title_pos[i] = '22nd'
        elif x == 23:
            title_pos[i] = '23rd'
        else:
            title_pos[i] = f'{title_pos[i]}th'

    # set the title and axes labels

    # set axis lables and title
    cur_day = datetime.today().strftime('%d-%m-%y')
    title_text = (
        title_text_1 +
        f'\n{title_pos[0]} to {title_pos[1]} as of {cur_day}   '
        )

    y_labelsize = set_title_and_labels(title_text, total_y, teams)

    # reset teams index for use in generating label position
    teams = teams.reset_index()
    teams_all = teams_all.reset_index()

    class ThresholdLine():
        """Class representing a horizontal competition threshhold line"""
        def __init__(self, position, label, colour):
            self.position = position
            self.pts_required = teams_all['max_points'][self.position]
            self.label = label.replace('__', str(self.pts_required))
            self.colour = colour
            self.linestyle = (0, (5, 5))
            self.label_space()
            self.label_offset = self.pts_required + 0.12
            self.text = None
            self.line = None

        def __str__(self):
            return f"{self.position} {self.label} {self.colour}"

        def label_space(self):
            """A function to calculate the positioning of a label on a competition bar"""
            # adjust text spacing to not overlap any data bars
            for x in teams.itertuples():
                if x.max_points == self.pts_required:
                    label_space = x.Index - 0.5
                    break
                label_space = None

            self.labelpos = label_space

        def generate_threshold_line(self):
            """Function to generate the line and plot it on the figure"""
            # only draw the line if there are bars that max out under the value
            # e.g: if image shows pos 1 - 10, dont draw the relegation line, as there is no need
            if self.labelpos is not None:
                lne = plt.axhline(y=self.pts_required, color=self.colour, linestyle=self.linestyle)
                txt = plt.text(self.labelpos, self.label_offset, self.label,
                        color=self.colour, ha='left', weight='semibold', size='medium', va='bottom')
                self.text = txt
                self.line = lne
            else:
                pass

    # create a list of ThresholdLine objects, to iterate through.
    obj_lst = []
    for x in lines_to_generate:
        # Position, Label, Hex Colour Code
        tvar = ThresholdLine(x[0], x[1], x[2])
        obj_lst.append(tvar)

    # for each line, check if overlapping, and change positioning of label if they are
    for index, line in enumerate(obj_lst):
        # oldline is the previous line by index, but not if the index would be -1
        oldline = obj_lst[index-1]
        if index - 1 < 0:
            pass
        elif oldline.pts_required == line.pts_required:
            # update the new line to be offset, and move the old label higher
            line.linestyle = (5, (5,5))
            oldline.label_offset += 0.8
            oldline.text.set_position((oldline.labelpos, oldline.label_offset))
            plt.draw()

        line.generate_threshold_line()

    # Axis modifications
    axes = plt.gca() #Getting the current axis

    # format ticks to show every multiple of 5, and add grid behind to increase readability
    intervals = float(5)

    loc = plticker.MultipleLocator(base=intervals)
    axes.yaxis.set_major_locator(loc)

    minor_locator = AutoMinorLocator(intervals)
    axes.yaxis.set_minor_locator(minor_locator)

    axes.tick_params(axis='y', which='both', length=4, width=1)
    axes.tick_params(axis='x', which='both', pad=15)
    axes.set_axisbelow(True)
    axes.grid(which='major', axis='y', linestyle=(0, (4, 4)))

    # replace tick labels with club crests
    def offset_image(coord, name, ax):
        img = team_crest[name]
        im = OffsetImage(img, zoom=0.18)
        im.image.axes = ax

        ab = AnnotationBbox(im, (coord, theory_min-3),  xybox=(0., -30.), frameon=False,
                            xycoords='data',  boxcoords="offset points", pad=0)

        ax.add_artist(ab)

    tick_replace = teams['id'].tolist()

    for i, c in enumerate(tick_replace):
        offset_image(i, c, axes)


    # add an invisible ylabel on the right to make padding equal on both sides of graph
    ax2 = axes.twinx()
    ax2.set_ylabel("Points and remaining fixures in chronological order",
                   labelpad=15, size=y_labelsize, fontname='sans-serif',
                   weight='semibold', color='w', zorder=0)
    ax2.spines[['top', 'right', 'left', 'bottom']].set_visible(False)
    ax2.tick_params(left = False, right = False , labelleft = False ,
                    labelbottom = False, labelright = False, bottom = False)

    axes.spines['top'].set_visible(False)
    axes.spines['right'].set_visible(False)

    axes.spines['bottom'].set_bounds(-1, ax_width)
    axes.spines['bottom'].set_linewidth(2)
    axes.spines['left'].set_linewidth(2)

    graph_time = time.time()

    date_time = datetime.today().strftime('%d-%m-%y %H.%M')
    title_name = f'{file_text} {date_time}.png'

    cur_dir_path = os.getcwd()
    sub_name = rf'History\{competition}'
    sub_path = os.path.join(cur_dir_path, sub_name)

    if not os.path.exists(sub_path):
        os.makedirs(sub_path)

    file_path = os.path.join(sub_path, title_name)

    plt.savefig(file_path, bbox_inches='tight', pad_inches=0.25, dpi=300)
    print(f'Done. \nTime to gen data: {round(data_time - origin_time, 3)} sec.'
          f'\nTime to gen graph: {round(graph_time - data_time, 3)} sec.'
          f'\nTime to save: {round(time.time() - graph_time, 3)} sec.')
    # plt.show()
