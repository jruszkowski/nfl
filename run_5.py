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

#plyr_dict['Todd Gurley II'] = plyr_dict.pop('Todd Gurley')
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

position_dict = df.groupby(['Position']).apply(lambda x: x.to_dict(orient='index'))

all_plyr_dict = df.to_dict(orient='index')
qb_position_dict = df[df['Position'] == 'QB'].to_dict(orient='index')
team_dict = df[df['Position'] != 'QB'].groupby(['Team']).apply(lambda x: x.to_dict(orient='index'))
position_dict_all = df.groupby(['Position']).apply(lambda x: x.to_dict(orient='index'))

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


def add_func_list(plyrs, key):
    return sum([all_plyr_dict[x][key] for x in plyrs])

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
			if len(plyr_tuple) == 2:
                        	total_dict[x]['players'] += list(plyr_tuple)
			else:
				total_dict[x]['players'].append(plyr_tuple)

        total_dict = {y['projection']: y['players'] for x,y in total_dict.items()}
        df = pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False)
        print (datetime.datetime.now() - start_time)
        return df

def stack():
	stack_list = []
	for qb in qb_position_dict.keys():
	    for team_plyr in team_dict[qb_position_dict[qb]['Team']]:
		stack_list.append((qb, team_plyr))

	player_list = []
	for stack in stack_list:
	    qb = stack[0]
	    other = stack[1]
	    other_position = all_plyr_dict[other]['Position']
	    if other_position == 'RB':
		for rb in position_dict_all['RB'].keys():
			if rb != other:
			    for wr_combo in combinations(position_dict_all['WR'], 2):
				wr_1 = wr_combo[0]
				wr_2 = wr_combo[1]
				if 59000 < add_func_list([qb, other, rb, wr_1, wr_2], 'Salary') <= 60000:
				    player_list.append((add_func_list([qb, other, rb, wr_1, wr_2], 'Projection'), qb, other, rb, wr_1, wr_2))
	    elif other_position == 'WR':
		for wr in position_dict_all['WR'].keys():
			if wr != other:
			    for rb_combo in combinations(position_dict_all['RB'], 2):
				rb_1 = rb_combo[0]
				rb_2 = rb_combo[1]
				if 59000 < add_func_list([qb, rb_1, rb_2, other, wr], 'Salary') <= 60000:
				    player_list.append((add_func_list([qb, rb_1, rb_2, other, wr], 'Projection'), qb, rb_1, rb_2, other, wr))

	columns = ['Projection', 'QB', 'RB1', 'RB2', 'WR1', 'WR2']

	df = pd.DataFrame(player_list)
	df.sort_values([0], ascending=False, inplace=True)
	df.columns = columns
	max_projection = pd.DataFrame(df.groupby(['QB'])['Projection'].agg([np.max])['amax'].sort_values(ascending=False)).reset_index()
	df = pd.merge(max_projection, df, how='inner', left_on=['QB', 'amax'], right_on=['QB', 'Projection']).set_index('Projection')
	df = df[columns[1:]]
	return df

if __name__=="__main__":
        df = main()
        print (df.head(10))
	df = stack()
	print (df.head(10))
