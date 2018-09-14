from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
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

df = pd.read_csv('fanduel.csv')
df = df.drop(df.loc[(df['Nickname'] == 'Michael Thomas') & (df.Team == 'LAR')].index)
df = df.drop(df.loc[(df['Nickname'] == 'Ryan Griffin') & (df.Team == 'TB')].index)
df = df.drop(df.loc[(df['Nickname'] == 'Chris Thompson') & (df.Team == 'HOU')].index)
df = df.set_index('Nickname')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df[df['Injury Indicator'].isnull()]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]

all_plyr_dict = df.to_dict(orient='index')


def add_func_list(plyrs, key):
    plyr_list = [x for x in plyrs]
    return sum([all_plyr_dict[x][key] for x in plyr_list])

def create_salary_dict():
	return {salary: {'players': [], 'projection': 0} for salary in range(0,60100,100)}

flex_dict = create_salary_dict()

flex_dict = defaultdict(dict)
for combo in combinations(all_plyr_dict.keys(), 5):
    projection = add_func_list(combo, 'Projection')
    salary = add_func_list(combo, 'Salary')
    if salary <= 60000:
        flex_dict[combo] = {'s': salary, 'p': projection}

def main():
        start_time = datetime.datetime.now()
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
