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
plyr_df = pd.DataFrame.from_dict(plyr_dict, orient='index')
d_plyr_df = pd.DataFrame.from_dict(d_plyr_dict, orient='index')
plyr_df = pd.concat([plyr_df, d_plyr_df])
plyr_df = plyr_df.reset_index()
plyr_df.columns = ['Name', 'Projection']
plyr_df['Name'] = plyr_df['Name'].apply(lambda x: x.strip())
if f[0] == 'd':
	df['Name'] = df['Name'].apply(lambda x: x.strip())
	df = df.merge(plyr_df, on=['Name'], suffixes=('_1', '_2'))
	df = df.reset_index()
	df = df.drop(df.loc[(df['Name'] == 'Michael Thomas') & (df.Salary == 3000)].index)
	df = df.drop(df.loc[(df['Name'] == 'Chris Thompson') & (df.Salary == 3000)].index)
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

plyr_names = {'d': 'Name', 'f': 'Nickname'}
salary = {'d': 50000, 'f': 60000}

df = df.reset_index()
df_pos_salary = df.groupby(['Roster Position', 'Salary'])['Projection'].agg([np.max])['amax']
df_pos_salary = df_pos_salary.reset_index()
df = df.merge(df_pos_salary, on=['Roster Position', 'Salary'])
df = df[df['Projection'] >= df['amax']]
del df['amax']
df.set_index('Name + ID', inplace=True)

df = df.reset_index()
df_pos = df.groupby(['Roster Position', 'Projection'])['Salary'].agg([np.min])['amin']
df_pos = df_pos.reset_index()
df = df.merge(df_pos, on=['Roster Position', 'Projection'])
df = df[df['Salary'] <= df['amin']]
del df['amin']
df.set_index('Name + ID', inplace=True)

grouped = df.groupby(['Roster Position'])
position_dict = defaultdict()
for pos, frame in grouped:
	position_dict[pos] = frame.to_dict(orient='index')

player_dict = defaultdict()
for item in position_dict.items():
	for plyr_name in item[1].keys():
		player_dict[plyr_name] = item[1][plyr_name]

capt_plyr_list = [k for k,v in player_dict.items() if v['Roster Position'] == 'CPT']
flex_plyr_list = [k for k,v in player_dict.items() if v['Roster Position'] == 'FLEX']
player_names = {k: v['Name'] for k,v in player_dict.items()}

def return_combos(plyr_list, count):
	return list(combinations(plyr_list, count))

flex = return_combos(flex_plyr_list, 5)

def df_value(row, k, n):
	if n == 1:
		return player_dict[row[0]][k]
	if n == 2:
		return player_dict[row[0]][k]+ player_dict[row[1]][k]
	if n == 3:
		return player_dict[row[0]][k] + player_dict[row[1]][k] + player_dict[row[2]][k]
	if n == 4:
		return player_dict[row[0]][k] + player_dict[row[1]][k] + player_dict[row[2]][k] + player_dict[row[3]][k]
	if n == 5:
		return player_dict[row[0]][k] \
			+ player_dict[row[1]][k] \
			+ player_dict[row[2]][k] \
			+ player_dict[row[3]][k] \
			+ player_dict[row[4]][k]

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

def get_projections():

	df_capt = pd.DataFrame(capt_plyr_list)
	col_n = len(df_capt.columns)
	df_capt['Salary'] = df_capt.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_capt['Projection'] = df_capt.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_capt['Projection'] = df_capt['Projection'] * 1.5
	df_capt = clean_frame(df_capt)

	df_flex = pd.DataFrame(flex)
	col_n = len(df_flex.columns)
	df_flex['Salary'] = df_flex.apply(df_value, args=(['Salary', col_n]), axis=1)
	df_flex['Projection'] = df_flex.apply(df_value, args=(['Projection', col_n]), axis=1)
	df_flex = clean_frame(df_flex)

	df_capt['key'] = 1
	df_flex['key'] = 1

	df = df_flex.merge(df_capt, on=['key'], suffixes=('_flex', '_capt'))
	df['Salary'] = df['Salary_capt'] + df['Salary_flex']
	df['Projection'] = df['Projection_flex'] + df['Projection_capt']
	df = df[df['Salary'] <= salary[f[0]]]
	df = clean_frame(df)

	df = df.sort_values('Projection', ascending=False)
	df.columns = [str(x) for x in df.columns]
	df = df[df.columns[~df.columns.str.contains('Projection_|Salary_|key')]].dropna(axis=1)
	df = df.replace(player_names)
	df = df[df['0_capt']!=df['1']]
	df = df[df['0_capt']!=df['2']]
	df = df[df['0_capt']!=df['3']]
	df = df[df['0_capt']!=df['4']]
	df = df[df['0_capt']!=df['0_flex']]
	return df

if __name__=="__main__":
	start_time = datetime.datetime.now()
	results = get_projections()
	results.to_csv('results/output_' + sys.argv[1])

	print (datetime.datetime.now() - start_time)
	print (results.iloc[0])
