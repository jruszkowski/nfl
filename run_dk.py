from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
import datetime

base_page = 'http://games.espn.com/ffl/tools/projections?&scoringPeriodId=1&seasonId=2018'
addon = '&startIndex='
startindex = list(range(40, 1080, 40))
plyr_dict = {}
page = base_page

def convert_string(s):
	try:
		return float(s)
	except:
		return 0.0

for i in startindex:
	get_page = urllib2.urlopen(page)
	soup = BeautifulSoup(get_page, 'html.parser')
	rows = soup.find_all('tr')
	for row in rows:
		if len(row) == 14:
		    if row.a.get_text()!='PLAYER':
			plyr_dict[row.a.get_text()] = [convert_string(td.string) \
				for td in row.find_all('td', {'class': 'playertableStat appliedPoints sortedCell'})][0]
	page = base_page + addon + str(i)

#plyr_dict['Todd Gurley II'] = plyr_dict.pop('Todd Gurley')
d_plyr_dict = {x.split(' ')[0]: y for (x,y) in plyr_dict.items() if x.split(' ')[1] == 'D/ST'}

df = pd.read_csv('dk_2.csv').set_index('Name')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df.reset_index()
df['Name'] = df['Name'].apply(lambda x: x.strip())
df = df.drop(df.loc[(df['Name'] == 'Michael Thomas') & (df.Salary == 3000)].index)
df = df.drop(df.loc[(df['Name'] == 'Chris Thompson') & (df.Salary == 3000)].index)
df.set_index(['Name'], inplace=True)
df.loc[df['Position']=='DST', 'Projection'] = pd.DataFrame.from_dict(d_plyr_dict, orient='index')[0]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]
df = df[df['ID']!=11192832]

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

		
def total_lineup(combo, key):
	qb = combo[0]
	d = combo[1]
	team_list = [qb] + [d]
	return round(sum([player_dict[x][key] for x in team_list]), 2)


flex_combos = {
	1: {'TE': 1, 'RB': 3, 'WR': 3},
	2: {'TE': 1, 'RB': 2, 'WR': 4},
	3: {'TE': 2, 'RB': 2, 'WR': 3}
	}


def create_combo_dictionaries(combo_key):
	for position in flex_combos[combo_key].keys():
		count = flex_combos[combo_key][position]
	
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



def get_combo_list():
	return [(i, qb) for qb in position_dict['QB'].keys() for i in flex_combos.keys()] 

results_dict = {i: {qb: {'salary': 0, 'projection': 0, 'lineup': []} for qb in position_dict['QB'].keys()} for i in flex_combos.keys()}

def create_salary_dict():
	return {i: {salary: {'players': [], 'projection': 0} for salary in range(1000,50100,100)} for i in flex_combos.keys()}

def create_salary_dict_no_key():
	return {salary: {'players': [], 'projection': 0} for salary in range(1000,50100,100)}

rb_dict = create_salary_dict()
wr_dict = create_salary_dict()
te_dict = create_salary_dict()

qb_dict = create_salary_dict_no_key()
singles_list = ((qb, d) for qb in position_dict['QB'].keys() for d in position_dict['DST'].keys()) 
for combo in singles_list:
	projection = total_lineup(combo, 'Projection')
	salary = total_lineup(combo, 'Salary')
	if projection > qb_dict[salary]['projection']:
		qb_dict[salary]['projection'] = projection
		qb_dict[salary]['players'] = combo 


def add_func(position, plyrs, key):
	plyrs = [x for x in plyrs]
	return sum([position_dict[position][x][key] for x in plyrs])

def clean_dict(dict_zeros):
	for key in dict_zeros.keys():
		for salary in dict_zeros[key].keys():
			if dict_zeros[key][salary]['projection'] == 0:
				del dict_zeros[key][salary]
	return dict_zeros

def clean_dict_no_key(dict_zeros):
	for salary in dict_zeros.keys():
		if dict_zeros[salary]['projection'] == 0:
			del dict_zeros[salary]
	return dict_zeros

def total_lineup_all(combo, key):
	other = [x for x in combo[0]]
	rb = [x for x in combo[1]]
	wr = [x for x in combo[2]]
	te = [x for x in combo[3]]
	team_list = other + rb + wr + te
	return round(sum([player_dict[x][key] for x in team_list]), 2)


if __name__=="__main__":
	for i in flex_combos.keys():
		create_combo_dictionaries(i)
	rb_dict = clean_dict(rb_dict)
	wr_dict = clean_dict(wr_dict)
	te_dict = clean_dict(te_dict)
	qb_dict = clean_dict_no_key(qb_dict)
	total_dict = {}
	for i in flex_combos.keys():
		total_dict.update({(qb_dict[salary]['players'], \
				rb_dict[i][rb]['players'], \
				wr_dict[i][wr]['players'], \
				te_dict[i][te]['players']): \
			{'salary': total_lineup_all((qb_dict[salary]['players'], \
					rb_dict[i][rb]['players'], \
					wr_dict[i][wr]['players'], \
					te_dict[i][te]['players'], \
					), 'Salary'),\
			 'projection': total_lineup_all((qb_dict[salary]['players'], \
					rb_dict[i][rb]['players'], \
					wr_dict[i][wr]['players'], \
					te_dict[i][te]['players'], \
					), 'Projection')} \
			for salary in qb_dict.keys() \
			for rb in rb_dict[i].keys() \
			for wr in wr_dict[i].keys() \
			for te in te_dict[i].keys() \
			if 49500 < total_lineup_all((qb_dict[salary]['players'], \
				rb_dict[i][rb]['players'], \
				wr_dict[i][wr]['players'], \
				te_dict[i][te]['players'], \
				), 'Salary') <= 50000})

        for x in total_dict.keys():
                total_dict[x]['players'] = []
                for plyr_tuple in x:
                        total_dict[x]['players'] += list(plyr_tuple)

        total_dict = {y['projection']: y['players'] for x,y in total_dict.items()}
	columns = ['QB', 'DST', 'RB1', 'RB2', 'RB3', 'WR1', 'WR2', 'WR3', 'TE']	
        df = pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False)
	df.columns = columns
#        df = pd.DataFrame.from_dict(total_dict, orient='index').reset_index().set_index('projection').sort_index(ascending=False)
        #df = pd.DataFrame.from_dict(total_dict, orient='index')
        print (df.head(20))
