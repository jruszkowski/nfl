from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed

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

df = pd.read_csv('draftkings.csv').set_index('Name')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df.reset_index()
df['Name'] = df['Name'].apply(lambda x: x.strip())
df.set_index(['Name'], inplace=True)
df.loc[df['Position']=='DST', 'Projection'] = pd.DataFrame.from_dict(d_plyr_dict, orient='index')[0]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]

min_salary = df.groupby(['Position'])['Salary'].agg([np.min])['amin'].to_dict()
min_rb_projection = df[df['Salary'] == min_salary['RB']][df['Position'] == 'RB']['Projection'].max()
min_wr_projection = df[df['Salary'] == min_salary['WR']][df['Position'] == 'WR']['Projection'].max()
min_te_projection = df[df['Salary'] == min_salary['TE']][df['Position'] == 'TE']['Projection'].max()
min_d_projection = df[df['Salary'] == min_salary['DST']][df['Position'] == 'DST']['Projection'].max()
min_dict = {'QB': 1, 'RB': min_rb_projection, 'WR': min_wr_projection,\
         'TE': min_te_projection, 'DST': min_d_projection}


grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')


def total_lineup(qb, te, d, rb, wr, flex, key):
    return round(position_dict['QB'][qb][key] + \
        position_dict[flex[0]][flex[1]][key] + \
        position_dict['TE'][te][key] + \
        position_dict['DST'][d][key] + \
        position_dict['RB'][rb[0]][key] + \
        position_dict['RB'][rb[1]][key] + \
        position_dict['WR'][wr[0]][key] + \
        position_dict['WR'][wr[1]][key] + \
        position_dict['WR'][wr[2]][key], 2)


def flex_players():
	flex_player_list = []
	for item in position_dict.items():
		if item[0] in ['TE','WR','RB']:
			plyr_tuples = [(item[0], x) for x in item[1].keys()]
			flex_player_list += plyr_tuples
	return flex_player_list

def flex_list(te, rbs, wrs):
	team_list = []
	rbs = [x for x in rbs]
	wrs = [x for x in wrs]
	team_list = [te] + rbs + wrs
	return [x for x in flex_players() if x[1] not in team_list]

def run(single_position):
	optimal_lineup = 0
	lineup = []
	qb = single_position
	singles_list = [(te, d) for te in position_dict['TE'].keys() \
			for d in position_dict['DST'].keys()]
	for i in singles_list:
		te,d = i
		for rbs in combinations(position_dict['RB'], 2):
			for wrs in combinations(position_dict['WR'], 3):
				for flex in flex_list(te, rbs, wrs):
				    salary = total_lineup(qb, te, d, rbs, wrs, flex, 'Salary')
				    if 49500 < salary <= 50000:
					if total_lineup(qb, te, d, rbs, wrs, flex, 'Projection') >= optimal_lineup:
					    optimal_lineup = total_lineup(qb, te, d, rbs, wrs, flex, 'Projection')
					    lineup = [qb, te, d, rbs, wrs, flex[1]]
	print (optimal_lineup, lineup)
	return (optimal_lineup, lineup)


def get_combo_list():
	return [(qb) for qb in position_dict['QB'].keys()] 


if __name__=="__main__":
	results = Parallel(n_jobs=-1)(delayed(run)(i) for i in get_combo_list())
	print len(results)
	max_projection = 0
	team = []
	for i in results:
		if i[0] > max_projection:
			max_projection = i[0]
			team = i[1]
	print max_projection, team 
