from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed
import datetime

f = open('nfl.txt', 'w')
started = datetime.datetime.now()
f.write(str(started))
f.close()

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
	1: {'TE': 1, 'RB': 3, 'WR': 3, 'QB': 1},
	2: {'TE': 1, 'RB': 2, 'WR': 4, 'QB': 1},
	3: {'TE': 2, 'RB': 2, 'WR': 3, 'QB': 1}
	}

singles_list = ((qb, d, k) for qb in position_dict['QB'].keys() \
				for d in position_dict['D'].keys() \
				for k in position_dict['K'])


def create_combo_dictionaries(combo_key):
	for position in flex_combos.keys():
		count = flex_combos[combo_key][postion]
	
		if position == 'RB': 
			for combo in combinations(position_dict[position], count):
				projection = add_func(position, combo, 'Projection')
				salary = add_func(position, combo, 'Salary')
				if projection > rb_dict[combo_key][salary]['projection']:
					rb_dict[combo_key][salary]['projection'] = projection
					rb_dict[combo_key][salary]['players'] = combo 
		elif position == 'WR': 
			for combo in combinations(position_dict[position], count):
				projection = add_func(position, combo, 'Projection')
				salary = add_func(position, combo, 'Salary')
				if projection > wr_dict[combo_key][salary]['projection']:
					wr_dict[combo_key][salary]['projection'] = projection
					wr_dict[combo_key][salary]['players'] = combo 

		elif position == 'TE': 
			for combo in combinations(position_dict[position], count):
				projection = add_func(position, combo, 'Projection')
				salary = add_func(position, combo, 'Salary')
				if projection > te_dict[combo_key][salary]['projection']:
					te_dict[combo_key][salary]['projection'] = projection
					te_dict[combo_key][salary]['players'] = combo 

		elif position == 'QB': 
			for combo in singles_list:
				projection = total_lineup(combo, 'Projection')
				salary = total_lineup(combo, 'Salary')
				if projection > qb_dict[combo_key][salary]['projection']:
					qb_dict[combo_key][salary]['projection'] = projection
					qb_dict[combo_key][salary]['players'] = combo 



def get_combo_list():
	return [(i, qb) for qb in position_dict['QB'].keys() for i in flex_combos.keys()] 

results_dict = {i: {qb: {'salary': 0, 'projection': 0, 'lineup': []} for qb in position_dict['QB'].keys()} for i in flex_combos.keys()}
def create_salary_dict():
	return {i: {salary: {'players': [], 'projection': 0} for salary in range(0,60100,100) for i in flex_combos.keys()}}
rb_dict = create_salary_dict()
wr_dict = create_salary_dict()
te_dict = create_salary_dict()
qb_dict = create_salary_dict()

def add_func(position, plyrs, key):
	plyrs = [x for x in plyrs]
	return sum([position_dict[position][x][key] for x in plyrs])

if __name__=="__main__":
	Parallel(n_jobs=-1)(delayed(create_combo_dictionaries)(i) for i in flex_combos.keys())
	rb_dict = clean_dict(rb_dict)
	wr_dict = clean_dict(wr_dict)
	qb_dict = clean_dict(qb_dict)
	total_dict = {(qb_dict[key][other]['players'], rb_dict[key][rb]['players'], wr_dict[key][wr]['players'], te_dict[key][te]['players']): \
		{'salary': total_lineup_all((qb_dict[key][other]['players'], \
				rb_dict[key][rb]['players'], \
				wr_dict[key][wr]['players'], \
				te_dict[key][te]['players'], \
				), 'Salary'),\
		 'projection': total_lineup_all((qb_dict[other]['players'], \
				rb_dict[key][rb]['players'], \
				wr_dict[key][wr]['players'], \
				te_dict[key][te]['players'], \
				), 'Projection')} \
		for other in qb_dict[key].keys() \
		for rb in rb_dict[key].keys() \
		for wr in wr_dict[key].keys() \
		for te in te_dict[key].keys() \
		for key in flex_combos.keys()
		if total_lineup_all((qb_dict[key][other]['players'], \
			rb_dict[key][rb]['players'], \
			wr_dict[key][wr]['players'], \
			te_dict[key][te]['players'], \
			), 'Salary') <= 50000}

        #df = pd.DataFrame.from_dict(total_dict, orient='index').set_index('projection').sort(ascending=False)
        df = pd.DataFrame.from_dict(total_dict, orient='index')
        print (df.head(10))

