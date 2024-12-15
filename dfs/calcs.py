import numpy as np
import xlwings as xw
import pandas as pd
from dfs.normalize import names, d_map
from itertools import combinations


def get_roster(wb: xw.Book, ws: str, fs_book: str = 'draftkings') -> dict:
    sht = wb.sheets(ws)
    df = sht.range('A1').options(pd.DataFrame, header=1, index=False, expand='table').value
    df['Name'] = df['Name'].apply(lambda x: x.strip())
    df['Name'] = df['Name'].replace(names[fs_book])
    df['Name'] = df['Name'].replace(d_map)
    d = df.to_dict(orient='index')
    return d


def apply_projection(roster: dict, plyr_dict: dict, d_plyr_dict: dict) -> dict:
    for key in roster.keys():
        plyr_name = roster[key]['Name']
        if roster[key]['Position'] == 'DST':
            roster[key]['Projection'] = d_plyr_dict[plyr_name]
        elif roster[key]['Name'] in plyr_dict.keys():
            roster[key]['Projection'] = plyr_dict.pop(plyr_name)
        else:
            print(f'No projection for {plyr_name}')
            roster[key]['Projection'] = 0
        roster[key]['Opp'] = get_opp(roster[key]['Game Info'], roster[key]['TeamAbbrev'])
    list_of_roster_keys = list(roster.keys())
    for key in list_of_roster_keys:
        if roster[key]['Projection'] == 0:
            roster.pop(key)
    return roster


def get_opp(game_info: str, team: str) -> str:
    game = game_info.split(' ')[0].split('@')
    if game[0] == team:
        return game[1]
    return game[0]


def get_combos(p: str, n: int):
    return list(combinations(p, n))


def main(full_roster: dict):
    full_roster_id = {v['ID']: v for k, v in full_roster.items()}
    salary_id = {k: v['Salary'] for k, v in full_roster_id.items()}
    projection_id = {k: v['Projection'] for k, v in full_roster_id.items()}
    te_plyr_list = [v['ID'] for k, v in full_roster.items() if v['Position'] == 'TE']
    rb_plyr_list = [v['ID'] for k, v in full_roster.items() if v['Position'] == 'RB']
    wr_plyr_list = [v['ID'] for k, v in full_roster.items() if v['Position'] == 'WR']
    qb_plyr_list = [v['ID'] for k, v in full_roster.items() if v['Position'] == 'QB']
    dst_plyr_list = [v['ID'] for k, v in full_roster.items() if v['Position'] == 'DST']
    singles_list = [[qb, d] for qb in qb_plyr_list for d in dst_plyr_list if full_roster_id[qb]['Opp'] != full_roster_id[d]['TeamAbbrev']]


    te_2 = get_combos(te_plyr_list, 2)
    wr_3 = get_combos(wr_plyr_list, 3)
    wr_4 = get_combos(wr_plyr_list, 4)
    rb_2 = get_combos(rb_plyr_list, 2)
    rb_3 = get_combos(rb_plyr_list, 3)

    flex_combos = {
        1: {'TE': te_plyr_list,
            'RB': rb_3,
            'WR': wr_3},
        2: {'TE': te_plyr_list,
            'RB': rb_2,
            'WR': wr_4},
        3: {'TE': te_2,
            'RB': rb_2,
            'WR': wr_3}
    }


    df_qb = pd.DataFrame(singles_list)
    df_qb_salary = df_qb.replace(salary_id).sum(axis=1)
    df_qb_projection = df_qb.replace(projection_id).sum(axis=1)
    qb_max = df_qb_projection.groupby(df_qb_salary).agg(np.max)
    df_qb.set_index('Projection').concat(df_qb_projection.set_index('Projection'))
    # col_n = len(df_qb.columns)
    # df_qb['Salary'] = df_qb.apply(df_value, args=(['Salary', col_n]), axis=1)
    # df_qb['Projection'] = df_qb.apply(df_value, args=(['Projection', col_n]), axis=1)
    # df_qb = clean_frame(df_qb)
    print(df_qb)


def clean_frame(f: pd.DataFrame) -> pd.DataFrame:

	df_salary = f.groupby(['Salary'])['Projection'].agg([np.max])['amax']
	f = f.merge(df_salary.to_frame(), on=['Salary'])
	f = f[f['Projection'] >= f['amax']]
	del f['amax']

	df_pos = f.groupby(['Projection'])['Salary'].agg([np.min])['amin']
	f = f.merge(df_pos.to_frame(), on=['Projection'])
	f = f[f['Salary'] <= f['amin']]
	del f['amin']
	return f