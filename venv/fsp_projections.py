import csv
import requests

projection_file = 'https://dfs-projections.wetalkfantasysports.com/shiny/DFS/session/e2e4b4000831f7e748fdd3b1e83574df/download/downloadData5?w='

def get_csv_file(f):
    req = requests.get(f)
    url_content = req.content
    csv_file = open('fsp_projection.csv', 'wb')
    csv_file.write(url_content)
    csv_file.close()

fanduel_d = {
    'Pittsburgh Steelers': 'Steelers',
    'Miami Dolphins': 'Dolphins',
    'Baltimore Ravens': 'Ravens',
    'Cleveland Browns': 'Browns',
    'Los Angeles Chargers': 'Chargers',
    'Minnesota Vikings': 'Vikings',
    'New England Patriots': 'Patriots',
    'Green Bay Packers': 'Packers',
    'New Orleans Saints': 'Saints',
    'Washington Football Team': 'Washington',
    'Indianapolis Colts': 'Colts',
    'Philadelphia Eagles': 'Eagles',
    'Denver Broncos': 'Broncos',
    'Tennessee Titans': 'Titans',
    'Cincinnati Bengals': 'Bengals',
    'Houston Texans': 'Texans',
    'Detroit Lions': 'Lions',
    'Carolina Panthers': 'Panthers',
    'Jacksonville Jaguars': 'Jaguars',
    'Atlanta Falcons': 'Falcons',
    'New York Jets': 'Jets',
    'Dallas Cowboys': 'Cowboys',
    'Los Angeles Rams': 'Rams',
    'San Francisco 49ers': '49ers',
    'Seattle Seahawks': 'Seahawks',
    'Chicago Bears': 'Bears',
    'Tampa Bay Buccaneers': 'Bucs',
    'Buffalo Bills': 'Bills',
    'Kansas City Chiefs': 'Chiefs',
    'Arizona Cardinals': 'Cardinals',
}

def remove_suffix(p, fanduel=False):
    if fanduel:
        if p != 'Odell Beckham Jr.':
            p = p.replace(' Jr.', '')
        if fanduel_d.get(p.strip()):
            p = fanduel_d.get(p.strip())
    if (not fanduel) and defense.get(p.strip()):
        p = defense.get(p.strip())
    p = p.replace(' III', '')
    p = p.replace(' II', '')
    p = p.replace(' IV', '')
    if p != 'Las Vegas':
        p = p.replace(' V', '')
    p = p.replace('AJ ', 'A.J. ')
    p = p.replace('DJ Chark Jr.', 'D.J. Chark')
    p = p.replace('Marvin Jones Jr.', 'Marvin Jones')
    p = p.replace('Robert Griffin', 'Robert Griffin III')
    p = p.replace('DJ ', 'D.J. ')
    p = p.replace('DK ', 'D.K. ')
    p = p.replace('Eli Mitchell', 'Elijah Mitchell')
    return p

def get_df(p_dict):
    f = 'fanduel_thurs.csv'
    df = pd.read_csv('inputs/' + f)
    df = df.drop(df.loc[(df['Nickname'] == 'Ryan Griffin') & (df.Team == 'TB')].index) #duplicate name
    df.loc[df['Nickname'].isin(fanduel_d.keys()), 'Nickname'] = df.loc[df['Nickname'].isin(fanduel_d.keys()), 'Nickname'].replace(fanduel_d)
    assert len(df) == len(df['Nickname'].unique())
    players = df['Nickname'].to_list()
    players = {p: remove_suffix(p, True) for p in players}
    df['Nickname'] = df['Nickname'].replace(players)
    df = df.set_index('Nickname')
    df['Projection'] = pd.DataFrame.from_dict(p_dict, orient='index')
    return df

def main():
    get_csv_file(projection_file)
    fsp = pd.read_csv('fsp_projection.csv')
    fsp.set_index('Player', inplace=True)
    fsp_dict = {k: v['Proj'] for k,v in fsp.to_dict(orient='index').items()}
    df = get_df(fsp_dict)
