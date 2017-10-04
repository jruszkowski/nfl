from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed
import datetime

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

df = pd.read_csv('fanduel.csv').set_index('Nickname')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df[df['Injury Indicator'].isnull()]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]
min_salary = df.groupby(['Position'])['Salary'].agg([np.min])['amin'].to_dict()
min_rb_projection = df[df['Salary'] == min_salary['RB']][df['Position'] == 'RB']['Projection'].max()
min_wr_projection = df[df['Salary'] == min_salary['WR']][df['Position'] == 'WR']['Projection'].max()
min_dict = {'QB': 1, 'RB': min_rb_projection, 'WR': min_wr_projection}

grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')

def total_lineup(qb, rb, wr, key):
    return round(position_dict['QB'][qb][key] + \
        position_dict['RB'][rb[0]][key] + \
        position_dict['RB'][rb[1]][key] + \
        position_dict['WR'][wr[0]][key] + \
        position_dict['WR'][wr[1]][key], 2)

def run(qb):
	i = 1
	optimal_lineup = 0
	lineup = []
	for rbs in combinations(position_dict['RB'], 2):
		for wrs in combinations(position_dict['WR'], 2):
		    i += 1
		    salary = total_lineup(qb, rbs, wrs, 'Salary')
		    if 58000 < salary <= 60000:
			if total_lineup(qb, rbs, wrs, 'Projection') >= optimal_lineup:
			    optimal_lineup = total_lineup(qb, rbs, wrs, 'Projection')
			    lineup = [qb, rbs, wrs]
			    print (optimal_lineup, salary, lineup)
	return (optimal_lineup, lineup)


def get_combo_list():
        return [(qb) for qb in position_dict['QB'].keys()]


if __name__=="__main__":
        start_time = datetime.datetime.now()
        results = Parallel(n_jobs=-1)(delayed(run)(i) for i in get_combo_list())
        max_projection = 0
        team = []
        for i in results:
                if i[0] > max_projection:
                        max_projection = i[0]
                        team = i[1]

        print (datetime.datetime.now() - start_time)
        print (max_projection, team)
