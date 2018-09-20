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

df = df.reset_index()
df_pos_salary = df.groupby(['Position', 'Salary'])['Projection'].agg([np.max])['amax']
df_pos_salary = df_pos_salary.reset_index()
df = df.merge(df_pos_salary, on=['Position', 'Salary'])
df = df[df['Projection'] >= df['amax']]
del df['amax']
df.set_index(plyr_names[f[0]], inplace=True)

# df_pos = df.groupby(['Position'])['Projection'].agg([np.min])['amin'].reset_index()
# df = df.merge(df_pos_salary, on=['Position', 'Salary'])
# df = df[df['Projection'] >= df['amax']]

min_salary = df.groupby(['Position'])['Salary'].agg([np.min]).to_dict()
min_rb_projection = df[df['Salary'] == min_salary['amin']['RB']][df['Position'] == 'RB']['Projection'].max()
min_wr_projection = df[df['Salary'] == min_salary['amin']['WR']][df['Position'] == 'WR']['Projection'].max()
min_te_projection = df[df['Salary'] == min_salary['amin']['TE']][df['Position'] == 'TE']['Projection'].max()
min_d_projection = df[df['Salary'] == min_salary['amin'][defense[f[0]]]][df['Position'] == defense[f[0]]]['Projection'].max()
min_qb_projection = df[df['Salary'] == min_salary['amin']['QB']][df['Position'] == 'QB']['Projection'].max()
min_dict = {'QB': min_qb_projection,
			'RB': min_rb_projection,
			'WR': min_wr_projection,
			'TE': min_te_projection,
			defense[f[0]]: min_d_projection}

grouped = df.groupby(['Position'])
position_dict = defaultdict()
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')

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

def lineup_list(te, wr, rb, single):
	team = [x for x in wr] + [y for y in rb] + single
	if type(te) == str:
		team = team + [te]
		return team
	return team + [x for x in te]

def eligible_lineup(qb_d):
	lineup_dict = defaultdict(float)
	for k in flex_combos.keys():
		team_list = [lineup_list(te, wr, rb, qb_d) \
				for te in flex_combos[k]['TE'] \
						for rb in flex_combos[k]['RB'] \
								for wr in flex_combos[k]['WR']]
		print(qb_d, k, len(team_list))
		for lineup in team_list:
			if sum([player_dict[j]['Salary'] for j in lineup]) <= 50000:
				lineup_dict[tuple(lineup)] = sum([player_dict[x]['Projection'] for x in lineup])
	return lineup_dict

if __name__=="__main__":
	start_time = datetime.datetime.now()
	results = Parallel(n_jobs=-1)(delayed(eligible_lineup)(qb_d) for qb_d in singles_list)
	total_dict = defaultdict(float)
	for d in results:
		for k, v in d.items():
			total_dict[k] = v
	df = pd.DataFrame.from_dict(total_dict, orient='index').sort_values(0, ascending=False).reset_index()
	df.columns = [['lineup', 'projection']]
	df[['p1','p2','p3','p4','p5','p6','p7','p8','p9']] = df['lineup'].apply(pd.Series)
	df = df[['projection','p1','p2','p3','p4','p5','p6','p7','p8','p9']]
	df.to_csv('results/output_' + sys.argv[1])

	print (datetime.datetime.now() - start_time)
	print (df.head(5))
