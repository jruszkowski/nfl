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
min_dict = {'QB': 10, 'RB': min_rb_projection, 'WR': min_wr_projection,\
         'TE': min_te_projection, 'DST': min_d_projection}


grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')
player_dict = {}
for item in position_dict.items():
	for plyr_name in item[1].keys():
		player_dict[plyr_name] = item[1][plyr_name]

		
def total_lineup(qb, te, d, rb, wr, key):
	team_list = []
	rbs = [x for x in rb]
	te = [x for x in te]
	wrs = [x for x in wr]
	team_list = te + rbs + wrs + [qb] + [d]
	return round(sum([player_dict[x][key] for x in team_list]), 2)


flex_combos = {
	1: {'TE': 1, 'RB': 3, 'WR': 3},
	2: {'TE': 1, 'RB': 2, 'WR': 4},
	3: {'TE': 2, 'RB': 2, 'WR': 3}
	}

def run(single_position):
	optimal_lineup = 0
	lineup = []
	qb = single_position
	singles_list = [d for d in position_dict['DST'].keys()]
	i = 0
	for d in singles_list:
		for fc in flex_combos.keys():
			for rbs in combinations(position_dict['RB'], flex_combos[fc]['RB']):
				for wrs in combinations(position_dict['WR'], flex_combos[fc]['WR']):
					for te in combinations(position_dict['TE'], flex_combos[fc]['TE']):
					    i+=1
					    salary = total_lineup(qb, te, d, rbs, wrs, 'Salary')
					    if 49500 < salary <= 50000:
						total_projection = total_lineup(qb, te, d, rbs, wrs, 'Projection')
						if total_projection >= optimal_lineup:
						    optimal_lineup = total_projection
						    lineup = [qb, te, d, rbs, wrs]
						    if total_projection > 130: 
							print (optimal_lineup, lineup, i)
	print ('final', optimal_lineup, lineup)
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
	df = pd.DataFrame(team)
	df.to_csv('results.csv')
