#!usr/bin/python3

import sys
import espn_projections as espn
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed
import datetime
from collections import defaultdict

plyr_dict, d_plyr_dict = espn.projections()
f = sys.argv[1]
df = pd.read_csv('inputs/' + f)
if f[0] == 'd':
	df = df.set_index('Name')
	df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
	df = df.reset_index()
	df['Name'] = df['Name'].apply(lambda x: x.strip())
	df = df.drop(df.loc[(df['Name'] == 'Michael Thomas') & (df.Salary == 3000)].index)
	df = df.drop(df.loc[(df['Name'] == 'Chris Thompson') & (df.Salary == 3000)].index)
	df.set_index(['Name'], inplace=True)
	df.loc[df['Position']=='DST', 'Projection'] = pd.DataFrame.from_dict(d_plyr_dict, orient='index')[0]
	df = df[df['ID']!=11192832]
elif f[0] == 'f':
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

df = df[df['Projection'] > 1]

defense = {'d': 'DST', 'f': 'D'}
plyr_names = {'d': 'Name', 'f': 'Nickname'}
salary = {'d': 50000, 'f': 60000}

df = df.reset_index()
df_pos_salary = df.groupby(['Position', 'Salary'])['Projection'].agg([np.max])['amax']
df_pos_salary = df_pos_salary.reset_index()
df = df.merge(df_pos_salary, on=['Position', 'Salary'])
df = df[df['Projection'] >= df['amax']]
del df['amax']
df.set_index(plyr_names[f[0]], inplace=True)

df = df.reset_index()
df_pos = df.groupby(['Position', 'Projection'])['Salary'].agg([np.min])['amin']
df_pos = df_pos.reset_index()
df = df.merge(df_pos, on=['Position', 'Projection'])
df = df[df['Salary'] <= df['amin']]
del df['amin']
df.set_index(plyr_names[f[0]], inplace=True)

grouped = df.groupby(['Position'])
position_dict = defaultdict()
for pos, frame in grouped:
	position_dict[pos] = frame.to_dict(orient='index')

player_dict = defaultdict()
for item in position_dict.items():
	for plyr_name in item[1].keys():
		player_dict[plyr_name] = item[1][plyr_name]

te_plyr_list = [k for k,v in player_dict.items() if v['Position'] == 'TE']
rb_plyr_list = [k for k,v in player_dict.items() if v['Position'] == 'RB']
wr_plyr_list = [k for k,v in player_dict.items() if v['Position'] == 'WR']
singles_list = [[qb, d] for qb in position_dict['QB'].keys() for d in position_dict[defense[f[0]]].keys()]

def return_combos(plyr_list, count):
	return list(combinations(plyr_list, count))

te = return_combos(te_plyr_list, 2)
wr_3 = return_combos(wr_plyr_list, 3)
wr_4 = return_combos(wr_plyr_list, 4)
rb_2 = return_combos(rb_plyr_list, 2)
rb_3 = return_combos(rb_plyr_list, 3)

flex_combos = {
	1: {'TE': te_plyr_list,
		'RB': rb_3,
		'WR': wr_3},
	2: {'TE': te_plyr_list,
		'RB': rb_2,
		'WR': wr_4},
	3: {'TE': te,
		'RB': rb_2,
		'WR': wr_3}
}

def df_value(row, k, n):
	if n == 1:
		return player_dict[row[0]][k]
	if n == 2:
		return player_dict[row[0]][k]+ player_dict[row[1]][k]
	if n == 3:
		return player_dict[row[0]][k] + player_dict[row[1]][k] + player_dict[row[2]][k]
	if n == 4:
		return player_dict[row[0]][k] + player_dict[row[1]][k] + player_dict[row[2]][k] + player_dict[row[3]][k]

def clean_frame(f):
	df_salary = f.groupby(['Salary'])['Projection'].agg([np.max])['amax']
	f = f.merge(df_salary.to_frame(), on=['Salary'])
	f = f[f['Projection'] >= f['amax']]
	del f['amax']

	df_pos = f.groupby(['Projection'])['Salary'].agg([np.min])['amin']
	f = f.merge(df_pos.to_frame(), on=['Projection'])
	f = f[f['Salary'] <= f['amin']]
	del f['amin']
	return f

def get_projections(ck):

	df_qb = pd.DataFrame(singles_list)
	col_n = len(df_qb.columns)
	df_qb['Salary'] = df_qb.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_qb['Projection'] = df_qb.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_qb = clean_frame(df_qb)

	df_te = pd.DataFrame(flex_combos[ck]['TE'])
	col_n = len(df_te.columns)
	df_te['Salary'] = df_te.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_te['Projection'] = df_te.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_te = clean_frame(df_te)

	df_rb = pd.DataFrame(flex_combos[ck]['RB'])
	col_n = len(df_rb.columns)
	df_rb['Salary'] = df_rb.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_rb['Projection'] = df_rb.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_rb = clean_frame(df_rb)

	df_wr = pd.DataFrame(flex_combos[ck]['WR'])
	col_n = len(df_wr.columns)
	df_wr['Salary'] = df_wr.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_wr['Projection'] = df_wr.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_wr = clean_frame(df_wr)

	df_qb['key'] = 1
	df_te['key'] = 1
	df_rb['key'] = 1
	df_wr['key'] = 1

	df = df_te.merge(df_rb, on=['key'], suffixes=('_te', '_rb'))
	df['Salary'] = df['Salary_te'] + df['Salary_rb']
	df['Projection'] = df['Projection_te'] + df['Projection_rb']
	df = df[df['Salary'] <= salary[f[0]] - (min(df_wr['Salary']) + min(df_qb['Salary']))]
	df = clean_frame(df)

	df = df.merge(df_wr, on=['key'], suffixes=('_2', '_wr'))
	df['Salary'] = df['Salary_2'] + df['Salary_wr']
	df['Projection'] = df['Projection_2'] + df['Projection_wr']
	df = df[df['Salary'] <= salary[f[0]] - min(df_qb['Salary'])]
	df = clean_frame(df)

	df = df.merge(df_qb, on=['key'], suffixes=('_3', '_qb'))
	df['Salary'] = df['Salary_3'] + df['Salary_qb']
	df['Projection'] = df['Projection_3'] + df['Projection_qb']
	df = df[df['Salary'] <= salary[f[0]]]
	df = clean_frame(df)

	df = df.sort_values('Projection', ascending=False)
	df.columns = [str(x) for x in df.columns]
	df = df[df.columns[~df.columns.str.contains('Projection_|Salary_|key')]].dropna(axis=1)
	df.columns = list(range(1,10)) + ['Salary', 'Projection']
	return df

if __name__=="__main__":
	start_time = datetime.datetime.now()
	results = Parallel(n_jobs=-1)(delayed(get_projections)(k) for k in flex_combos.keys())
	df = pd.concat(results, sort=True)
	df.reset_index(inplace=True)
	df = df[list(range(1,10)) + ['Salary', 'Projection']].sort_values('Projection', ascending=False)
	df.to_csv('results/output_' + sys.argv[1])

	print (datetime.datetime.now() - start_time)
	print (df.iloc[0])
