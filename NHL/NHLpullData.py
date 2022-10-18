import requests
import pandas          as pd
import numpy           as np



# define a method that shortens 'pd.DataFrame.from_records'.  Strictly for readability.
def json_to_df(x):
    return pd.DataFrame.from_records(x)

# The NHL has an API method that returns a summary of teams who participated in each season.  This
# method pulls this data for a prescribed season.
def getTeamsSeasonGeneralData(season):
    #
    # Get the data from the API, and extract the portion of the JSON structure containing the team data.
    r  = requests.get(url='http://statsapi.web.nhl.com/api/v1/teams?season='+season)
    df = json_to_df( json_to_df( r.json() ).teams.values ).set_index('id')
    #
    # Condition the general team data by dropping extraneous columns, and creating other useful columns.
    df.drop(columns=['name','teamName','locationName','venue','division','conference','franchise','shortName','officialSiteUrl'], inplace=True)
    df['season']          = season
    df['clinchIndicator'] = np.NaN

    return df

# The NHL provides an API to get detailed season stats for each team.  Since these stats need to be
# retrieved on a team-by-team basis, the columns need to be created first, and populated later.
# This method only creates the columns, and initializes them to zeros.  This method only needs to be
# called once.
def addTeamStatsColumns(df, season):
    #
    # Get the data from the API, and extract the portion of the JSON structure containing the team data.
    r    = requests.get(url='http://statsapi.web.nhl.com'+df.link.iloc[0]+'/stats?season='+season)
    temp = json_to_df( json_to_df( json_to_df( json_to_df( r.json() ).stats ).splits[0] ).stat )
    #
    # Create the stat columns, initialize them to zeros, and set their data types to 'float64'
    for col in temp.columns:
        df[col] = 0.
        df[col] = df[col].astype('float64')

    return df

# This method loops over all the teams in the input data frame, and populates their stats columns.
def getTeamsSeasonStats(df, season):
    for i in df.index:
        #
        # Get the data from the API, and extract the portion of the JSON structure containing the team data.
        r = requests.get(url='http://statsapi.web.nhl.com'+df.link.loc[i]+'/stats?season='+season)
        temp = json_to_df( json_to_df( json_to_df( json_to_df( r.json() ).stats ).splits[0] ).stat )
        #
        # Set the temporary dataframe's index to match the current row, and ensure all the stats are
        # stored as 'float64'
        temp.set_index([pd.Index([i])], inplace=True)
        for col in temp.columns:
            temp[col] = temp[col].astype('float64', errors='raise')
        #
        # Update the stats into the resulting dataframe
        df.update(temp)

    return df


# The NHL provides a single API to retrieve which teams qualified for the Playoffs each season, but
# the format of this data varies based on how the NHL determines which teams qualified.  (The top four
# teams in each division used to qualify, but that led to some stronger teams not qualifying because
# they were in an exceptionally good division.  Now, the top three teams in each division qualify,
# followed by the next two wild card teams from either division.)
def markPlayoffTeams(df, season):
    #
    # Get the data from the API, and extract the portion of the JSON structure containing the
    # playoff qualification data.
    r      = requests.get(url='https://statsapi.web.nhl.com/api/v1/standings/wildCardWithLeaders?season='+season)
    temp   = json_to_df( json_to_df( json_to_df( r.json() ).records ).teamRecords )
    #
    # Form a matrix of flags indicating which dataframe locations contain data
    toread = temp.notna()
    #
    # Populate data from the retrieved data into each teams's 'clinchIndicator' column.
    for i in temp.index:
        for col in temp.columns:

            if not toread.loc[i][col]:
                continue

            teamID = temp.loc[i][col]['team']['id']

            if any('clinchIndicator' in d for d in temp.loc[i][col]):
                df.loc[teamID,'clinchIndicator'] = 1
            else:
                df.loc[teamID,'clinchIndicator'] = 0

    return df

def getTeamsData(min_year=2009, max_year=2019):

    teamsData = pd.DataFrame()

    for year in range(min_year,max_year):
        #
        # NHL defines its season as the concatenation of the start and end years of the season.  For
        # example, the current season started in 2019, and will end in 2020, so the season is 20192020.
        season = str(year)+str(year+1)
        if year > min_year:
            # After the first year, concatenate each successive season's data with the accumulated data.
            teamsData = pd.concat([teamsData, getTeamsSeasonGeneralData(season)])
        else:
            # On the first year, establish the team data dataframe, including the stat columns.
            teamsData = getTeamsSeasonGeneralData(season)
            teamsData = addTeamStatsColumns(teamsData.copy(), season)
        #
        # For all years, get the team detailed stats, and mark which teams qualified for the playoffs.
        this_season = teamsData.season == season
        teamsData.loc[this_season] = getTeamsSeasonStats(teamsData[this_season].copy(), season)
        teamsData.loc[this_season] = markPlayoffTeams(teamsData[this_season].copy(), season)

    return teamsData
