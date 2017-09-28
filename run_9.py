from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np

base_page = 'http://games.espn.com/ffl/tools/projections'
addon = '?startIndex='
startindex = list(range(40, 1080, 40))
plyr_dict = {}
page = base_page
for i in startindex:
    get_page = urllib2.urlopen(page)
    soup = BeautifulSoup(get_page, 'html.parser')
    rows = soup.find_all('tr')
    for row in rows:
        if len(row) == 14:
            if row.a.get_text()!='PLAYER':
                plyr_dict[row.a.get_text()] = [float(td.string) \
			for td in row.find_all('td', {'class': 'playertableStat appliedPoints sortedCell'})][0]
    page = base_page + addon + str(i)

plyr_dict['Todd Gurley II'] = plyr_dict.pop('Todd Gurley')
d_plyr_dict = {x.split(' ')[0]: y for (x,y) in plyr_dict.items() if x.split(' ')[1] == 'D/ST'}

df = pd.read_csv('fanduel_9.csv').set_index('Nickname')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df.reset_index()
df.set_index('Last Name', inplace=True)
df.loc[df['Position']=='D', 'Projection'] = pd.DataFrame.from_dict(d_plyr_dict, orient='index')[0]
df = df.reset_index().set_index('Nickname')
df = df[df['Injury Indicator'].isnull()]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]

min_salary = df.groupby(['Position'])['Salary'].agg([np.min])['amin'].to_dict()
min_rb_projection = df[df['Salary'] == min_salary['RB']][df['Position'] == 'RB']['Projection'].max()
min_wr_projection = df[df['Salary'] == min_salary['WR']][df['Position'] == 'WR']['Projection'].max()
min_k_projection = df[df['Salary'] == min_salary['K']][df['Position'] == 'K']['Projection'].max()
min_te_projection = df[df['Salary'] == min_salary['TE']][df['Position'] == 'TE']['Projection'].max()
min_d_projection = df[df['Salary'] == min_salary['D']][df['Position'] == 'D']['Projection'].max()
min_dict = {'QB': 1, 'D': 1, 'RB': min_rb_projection, 'WR': min_wr_projection,\
         'K': min_k_projection, 'TE': min_te_projection, 'D': min_d_projection}

grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')

def total_lineup(qb, k, te, d, rb, wr, key):
    return round(position_dict['QB'][qb][key] + \
        position_dict['K'][k][key] + \
        position_dict['TE'][te][key] + \
        position_dict['D'][d][key] + \
        position_dict['RB'][rb[0]][key] + \
        position_dict['RB'][rb[1]][key] + \
        position_dict['WR'][wr[0]][key] + \
        position_dict['WR'][wr[1]][key] + \
        position_dict['WR'][wr[2]][key], 2)

def run():
        i = 1
        optimal_lineup = 0
        lineup = []
        for qb in position_dict['QB'].keys():
                for k in position_dict['K'].keys():
                        for te in position_dict['TE'].keys():
                                for d in position_dict['D'].keys():
                                    for rbs in combinations(position_dict['RB'], 2):
                                        for wrs in combinations(position_dict['WR'], 3):
                                            if i % 1000000000 == 0: print (i)
                                            i += 1
                                            salary = total_lineup(qb, k, te, d, rbs, wrs, 'Salary')
                                            if 59000 < salary <= 60000:
                                                if total_lineup(qb, k, te, d, rbs, wrs, 'Projection') >= optimal_lineup:
                                                    optimal_lineup = total_lineup(qb, k, te, d, rbs, wrs, 'Projection')
                                                    lineup = [qb, k, te, d, rbs, wrs]
                                                    print (optimal_lineup, salary, lineup)

if __name__=="__main__":
        run()