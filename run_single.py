import pandas as pd
import itertools as it
from operator import itemgetter

df = pd.DataFrame.from_csv('dk_single.csv')
positions = {
'QB': 'O',
'TE': 'O',
'WR': 'O',
'RB': 'O',
'LB': 'D',
'CB': 'D',
'S': 'D',
'DE': 'D',
'DT': 'D'}
df = df.reset_index().set_index('Name')
players = df.to_dict(orient='index')

op = {k:v for k,v in players.items() if positions[v['Position']] == 'O'}
dp = {k:v for k,v in players.items() if positions[v['Position']] == 'D'}

oc = it.combinations(op, 4) 
dc = it.combinations(dp, 2) 

def add_up(plyr_tuple, key):
	return sum(players[p][key] for p in plyr_tuple)

team_list = [(o + d, 
	add_up(o, 'AvgPointsPerGame') + add_up(d, 'AvgPointsPerGame'), 
	add_up(o, 'Salary') + add_up(d, 'Salary')) 
	for d in dc for o in oc if (add_up(o, 'Salary') + add_up(d, 'Salary')) <=50000]


print(sorted(team_list, key=itemgetter(1), reverse=True))[:5]

