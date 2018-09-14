from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
import datetime

#base_page = 'http://games.espn.com/ffl/tools/projections?&scoringPeriodId=1&seasonId=2018'
#addon = '&startIndex='
base_page = 'http://games.espn.com/ffl/tools/projections?'
addon = 'startIndex='
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

df = pd.read_csv('fanduel_9.csv')
df = df.drop(df.loc[(df['Nickname'] == 'Michael Thomas') & (df.Team == 'LAR')].index)
df = df.drop(df.loc[(df['Nickname'] == 'Ryan Griffin') & (df.Team == 'TB')].index)
df = df.drop(df.loc[(df['Nickname'] == 'Chris Thompson') & (df.Team == 'HOU')].index)
df = df.set_index('Nickname')
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
min_te_projection = df[df['Salary'] == min_salary['TE']][df['Position'] == 'TE']['Projection'].max()
min_d_projection = df[df['Salary'] == min_salary['D']][df['Position'] == 'D']['Projection'].max()
min_dict = {'QB': 1, 'D': 1, 'RB': min_rb_projection, 'WR': min_wr_projection, 'TE': min_te_projection}


grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
	if pos!='K':
		position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')


singles_list = [(qb, d) for qb in position_dict['QB'].keys() for d in position_dict['D'].keys()]

def create_salary_dict():
	return {salary: {'players': [], 'projection': 0} for salary in range(0,60100,100)}


def total_lineup(combo, key):
    return round(position_dict['QB'][combo[0]][key] + \
        position_dict['D'][combo[1]][key], 2)

def total_lineup_all(combo, key):
	other = combo[0]
	rb = combo[1]
	wr = combo[2]
	te = combo[3]
	if len(rb) == 3:
		flex = position_dict['RB'][rb[2]][key]
	elif len(wr) == 4:
		flex = position_dict['WR'][wr[3]][key]
	elif len(te) == 2:
		flex = position_dict['TE'][te[1]][key]
	return round(position_dict['QB'][other[0]][key] + \
		position_dict['TE'][te[0]][key] + \
		position_dict['D'][other[1]][key] + \
		position_dict['RB'][rb[0]][key] + \
		position_dict['RB'][rb[1]][key] + \
		position_dict['WR'][wr[0]][key] + \
		position_dict['WR'][wr[1]][key] + \
		position_dict['WR'][wr[2]][key] + flex, 2)


def add_func(position, plyrs, key):
	plyrs = [x for x in plyrs]
	return sum([position_dict[position][x][key] for x in plyrs])


combos = {1: {'RB': 2, 'WR': 3, 'QB': 1, 'TE': 2},
	2: {'RB': 2, 'WR': 4, 'QB': 1, 'TE': 1},
	3: {'RB': 3, 'WR': 3, 'QB': 1, 'TE': 1}}


def create_combo_dictionaries(combo_args):
	position = combo_args[0]
	count = combo_args[1]
	if position == 'RB': 
		rb_dict = create_salary_dict()
		for combo in combinations(position_dict[position], count):
			projection = add_func(position, combo, 'Projection')
			salary = add_func(position, combo, 'Salary')
			if projection > rb_dict[salary]['projection']:
				rb_dict[salary]['projection'] = projection
				rb_dict[salary]['players'] = combo 
		return rb_dict
	elif position == 'WR': 
		wr_dict = create_salary_dict()
		for combo in combinations(position_dict[position], count):
			projection = add_func(position, combo, 'Projection')
			salary = add_func(position, combo, 'Salary')
			if projection > wr_dict[salary]['projection']:
				wr_dict[salary]['projection'] = projection
				wr_dict[salary]['players'] = combo 
		return wr_dict
	elif position == 'TE': 
		te_dict = create_salary_dict()
		for combo in combinations(position_dict[position], count):
			projection = add_func(position, combo, 'Projection')
			salary = add_func(position, combo, 'Salary')
			if projection > te_dict[salary]['projection']:
				te_dict[salary]['projection'] = projection
				te_dict[salary]['players'] = combo 
		return te_dict
	elif position == 'QB': 
		qb_dict = create_salary_dict()
		for combo in singles_list:
			projection = total_lineup(combo, 'Projection')
			salary = total_lineup(combo, 'Salary')
			if projection > qb_dict[salary]['projection']:
				qb_dict[salary]['projection'] = projection
				qb_dict[salary]['players'] = combo 
		return qb_dict

def clean_dict(dict_zeros):
	for key in dict_zeros.keys():
		if dict_zeros[key]['projection'] == 0:
			del dict_zeros[key]
	return dict_zeros

def main():
        start_time = datetime.datetime.now()
	df = None
	for k in combos.keys():
		for i in combos[k].items():
			if i[0] == 'RB':
				rb_dict = create_combo_dictionaries(i)
			elif i[0] == 'WR':
				wr_dict = create_combo_dictionaries(i)
			elif i[0] == 'TE':
				te_dict = create_combo_dictionaries(i)
			elif i[0] == 'QB':
				qb_dict = create_combo_dictionaries(i)
		rb_dict_clean = clean_dict(rb_dict)
		wr_dict_clean = clean_dict(wr_dict)
		te_dict_clean = clean_dict(te_dict)
		qb_dict_clean = clean_dict(qb_dict)
		total_dict = {(qb_dict_clean[other]['players'], \
				rb_dict_clean[rb]['players'], \
				wr_dict_clean[wr]['players'], \
				te_dict_clean[te]['players']): \
			{'salary': total_lineup_all((qb_dict_clean[other]['players'], \
					rb_dict_clean[rb]['players'], \
					wr_dict_clean[wr]['players'], \
					te_dict_clean[te]['players']), 'Salary'),\
			 'projection': total_lineup_all((qb_dict_clean[other]['players'], \
					rb_dict_clean[rb]['players'], \
					wr_dict_clean[wr]['players'], \
					te_dict_clean[te]['players']), 'Projection')} \
			for other in qb_dict_clean.keys() \
			for rb in rb_dict_clean.keys() \
			for wr in wr_dict_clean.keys() \
			for te in te_dict_clean.keys() \
			if total_lineup_all((qb_dict_clean[other]['players'], \
				rb_dict_clean[rb]['players'], \
				wr_dict_clean[wr]['players'], \
				te_dict_clean[te]['players']), 'Salary') <= 60000}
		for x in total_dict.keys():
			total_dict[x]['players'] = []
			for plyr_tuple in x:
				total_dict[x]['players'] += list(plyr_tuple)
		total_dict = {y['projection']: y['players'] for x,y in total_dict.items()}
		if df is None:
			print(pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False).head())
			df = pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False)
		else:
			print(pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False).head())
			df = pd.concat([df, pd.DataFrame.from_dict(total_dict, orient='index').sort_index(ascending=False)])
		print(datetime.datetime.now() - start_time)
	return df.sort_index(ascending=False)

if __name__=="__main__":
	df = main()
	print (df.head(25))
