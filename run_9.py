from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed
import datetime

base_page = 'http://games.espn.com/ffl/tools/projections'
addon = '?startIndex='
startindex = list(range(40, 1000, 40))
plyr_dict = {}
page = base_page

def return_int(s):
	if s == '--':
		return 0
	return float(s)

for i in startindex:
    get_page = urllib2.urlopen(page)
    soup = BeautifulSoup(get_page, 'html.parser')
    rows = soup.find_all('tr')
    for row in rows:
        if len(row) == 14:
            if row.a.get_text()!='PLAYER':
                plyr_dict[row.a.get_text()] = [return_int(td.string) \
			for td in row.find_all('td', {'class': 'playertableStat appliedPoints sortedCell'})][0]
    page = base_page + addon + str(i)

#plyr_dict['Todd Gurley II'] = plyr_dict.pop('Todd Gurley')
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


singles_list = ((qb, te, d, k) for qb in position_dict['QB'].keys() \
				for te in position_dict['TE'].keys() \
				for d in position_dict['D'].keys() \
				for k in position_dict['K'])

def create_salary_dict():
	return {salary: {'players': [], 'projection': 0} for salary in range(0,60100,100)}

rb_dict = create_salary_dict()
wr_dict = create_salary_dict()
qb_dict = create_salary_dict()

def total_lineup(combo, key):
    return round(position_dict['QB'][combo[0]][key] + \
        position_dict['TE'][combo[1]][key] + \
        position_dict['K'][combo[3]][key] + \
        position_dict['D'][combo[2]][key], 2)

def total_lineup_all(combo, key):
	other = combo[0]
	rb = combo[1]
	wr = combo[2]

	return round(position_dict['QB'][other[0]][key] + \
		position_dict['TE'][other[1]][key] + \
		position_dict['K'][other[3]][key] + \
		position_dict['D'][other[2]][key] + \
		position_dict['RB'][rb[0]][key] + \
		position_dict['RB'][rb[1]][key] + \
		position_dict['WR'][wr[0]][key] + \
		position_dict['WR'][wr[1]][key] + \
		position_dict['WR'][wr[2]][key], 2)


def add_func(position, plyrs, key):
	plyrs = [x for x in plyrs]
	return sum([position_dict[position][x][key] for x in plyrs])


results_dict = {qb: {'salary': 0, 'projection': 0, 'lineup': []} for qb in position_dict['QB'].keys()}



combos = {'RB': 2, 'WR': 3, 'QB': 1}


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
		for combo in singles_list:
			projection = total_lineup(combo, 'Projection')
			salary = total_lineup(combo, 'Salary')
			if projection > qb_dict[salary]['projection']:
				qb_dict[salary]['projection'] = projection
				qb_dict[salary]['players'] = combo 

def clean_dict(dict_zeros):
	for key in dict_zeros.keys():
		if dict_zeros[key]['projection'] == 0:
			del dict_zeros[key]
	return dict_zeros

def main():
        start_time = datetime.datetime.now()
	for i in combos.items():
		create_combo_dictionaries(i)

        rb_dict_clean = clean_dict(rb_dict)
        wr_dict_clean = clean_dict(wr_dict)
        qb_dict_clean = clean_dict(qb_dict)
        total_dict = {(qb_dict_clean[other]['players'], rb_dict_clean[rb]['players'], wr_dict_clean[wr]['players']): \
                {'salary': total_lineup_all((qb_dict_clean[other]['players'], \
                                rb_dict_clean[rb]['players'], \
                                wr_dict_clean[wr]['players']), 'Salary'),\
                 'projection': total_lineup_all((qb_dict_clean[other]['players'], \
                                rb_dict_clean[rb]['players'], \
                                wr_dict_clean[wr]['players']), 'Projection')} \
                for other in qb_dict_clean.keys() \
                for rb in rb_dict_clean.keys() \
                for wr in wr_dict_clean.keys() \
                if total_lineup_all((qb_dict_clean[other]['players'], \
                        rb_dict_clean[rb]['players'], wr_dict_clean[wr]['players']), 'Salary') <= 60000}
        for x in total_dict.keys():
                total_dict[x]['players'] = []
                for plyr_tuple in x:
                        total_dict[x]['players'] += list(plyr_tuple)
        total_dict = {y['projection']: y['players'] for x,y in total_dict.items()}
        df = pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False)
	return df

if __name__=="__main__":
	df = main()
	print (df.head(15))
