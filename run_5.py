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
d_plyr_dict = {x.split(' ')[0]: y for (x,y) in plyr_dict.items() if x.split(' ')[1] == 'D/ST'}

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


def total_lineup(combo, key):
    return round(position_dict['QB'][combo[0]][key], 2)

def total_lineup_all(combo, key):
	qb = combo[0]
	rb = combo[1]
	wr = combo[2]

	return round(position_dict['QB'][qb][key] + \
		position_dict['RB'][rb[0]][key] + \
		position_dict['RB'][rb[1]][key] + \
		position_dict['WR'][wr[0]][key] + \
		position_dict['WR'][wr[1]][key], 2)


def add_func(position, plyrs, key):
	plyrs = [x for x in plyrs]
	return sum([position_dict[position][x][key] for x in plyrs])


results_dict = {qb: {'salary': 0, 'projection': 0, 'lineup': []} for qb in position_dict['QB'].keys()}

def create_salary_dict():
	return {salary: {'players': [], 'projection': 0} for salary in range(0,60100,100)}


combos = {'RB': 2, 'WR': 2, 'QB': 1}
rb_dict = create_salary_dict()
wr_dict = create_salary_dict()
qb_dict = create_salary_dict()


def create_combo_dictionaries(combo_args):
	position = combo_args[0]
	count = combo_args[1]
	if position == 'RB': 
		for combo in combinations(position_dict[position], count):
			projection = add_func(position, combo, 'Projection')
			salary = add_func(position, combo, 'Salary')
			if projection > rb_dict[salary]['projection']:
				rb_dict[salary]['projection'] = projection
				rb_dict[salary]['players'] = combo 
	elif position == 'WR': 
		for combo in combinations(position_dict[position], count):
			projection = add_func(position, combo, 'Projection')
			salary = add_func(position, combo, 'Salary')
			if projection > wr_dict[salary]['projection']:
				wr_dict[salary]['projection'] = projection
				wr_dict[salary]['players'] = combo 
	elif position == 'QB': 
		for qb in position_dict['QB'].keys():
			print (qb, position_dict.keys())
			projection = position_dict['QB'][qb]['Projection']
			salary = position_dict['QB'][qb]['Salary']
			if projection > qb_dict[salary]['projection']:
				qb_dict[salary]['projection'] = projection
				qb_dict[salary]['players'] = qb 

def clean_dict(dict_zeros):
	for key in dict_zeros.keys():
		if dict_zeros[key]['projection'] == 0:
			del dict_zeros[key]
	return dict_zeros

if __name__=="__main__":
	start_time = datetime.datetime.now()
	Parallel(n_jobs=-1)(delayed(create_combo_dictionaries)(i) for i in combos.items())
	rb_dict = clean_dict(rb_dict)
	wr_dict = clean_dict(wr_dict)
	qb_dict = clean_dict(qb_dict)
	total_dict = {(qb_dict[other]['players'], rb_dict[rb]['players'], wr_dict[wr]['players']): \
		{'salary': total_lineup_all((qb_dict[other]['players'], \
				rb_dict[rb]['players'], \
				wr_dict[wr]['players']), 'Salary'),\
		 'projection': total_lineup_all((qb_dict[other]['players'], \
				rb_dict[rb]['players'], \
				wr_dict[wr]['players']), 'Projection')} \
		for other in qb_dict.keys() \
		for rb in rb_dict.keys() \
		for wr in wr_dict.keys() \
		if total_lineup_all((qb_dict[other]['players'], \
			rb_dict[rb]['players'], wr_dict[wr]['players']), 'Salary') <= 60000}

	max_projection = max([total_dict[x]['projection'] for x in total_dict.keys()])
	df = pd.DataFrame.from_dict(total_dict, orient='index').reset_index().set_index('projection').sort(ascending=False)
	print (df.head(15))
	#for key in total_dict.keys():
	#	print total_dict[key]['projection'], key
	#	if total_dict[key]['projection'] == max_projection:
	#		print key
	print (datetime.datetime.now() - start_time)