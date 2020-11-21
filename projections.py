
import urllib3
from bs4 import BeautifulSoup
from collections import defaultdict

def convert_string(s):
    try:
        return float(s)
    except:
        return 0.0
    
def get_nf_projections():
    base_page = 'https://www.numberfire.com/nfl/fantasy/fantasy-football-ppr-projections'
    http = urllib3.PoolManager()
    response = http.request('GET', base_page)
    soup = BeautifulSoup(response.data, 'html.parser')
    rows = soup.find_all('tr')
    plyr_list = []
    projections = []
    for row in rows:
        if row.a:
            plyr_list.append(row.a.get_text())
        if len(row)==47:
            score = [convert_string(td.string) for td in row.find_all('td', {'class': 'nf_fp active'})]
            if len(score)>0:
                projections.append(score[0])
    plyr_list = [p.split('\n')[1] for p in plyr_list]
    projection_dict = {x: y for (x,y) in zip(plyr_list, projections)}
    return projection_dict

def get_nf_d_projections():
    base_page = 'https://www.numberfire.com/nfl/fantasy/fantasy-football-projections/d'
    http = urllib3.PoolManager()
    response = http.request('GET', base_page)
    soup = BeautifulSoup(response.data, 'html.parser')
    rows = soup.find_all('tr')
    plyr_list = []
    projections = []
    for row in rows:
        if row.a:
            plyr_list.append(row.a.get_text().replace(' D/ST',''))
        if len(row)==41:
            score = [convert_string(td.string) for td in row.find_all('td', {'class': 'nf_fp active'})]
            if len(score)>0:
                projections.append(score[0])
    plyr_list = [p.split('\n')[1] for p in plyr_list]
    projection_dict = {x: y for (x,y) in zip(plyr_list, projections)}
    return projection_dict

def get_espn_projections():
    base_page = 'http://games.espn.com/ffl/tools/projections?'
    addon = 'startIndex='
    startindex = list(range(40, 1080, 40))
    plyr_dict = defaultdict(dict)
    page = base_page
    for i in startindex:
        http = urllib3.PoolManager()
        response = http.request('GET', page)
        soup = BeautifulSoup(response.data, 'html.parser')
        rows = soup.find_all('tr')
        for row in rows:
            if len(row) == 14:
                if row.a.get_text() != 'PLAYER':
                    plyr_dict[row.a.get_text()] = [convert_string(td.string) for td in \
                                                   row.find_all('td', \
                                                                {'class': 'playertableStat appliedPoints sortedCell'})][0]
        page = base_page + addon + str(i)

    d_plyr_dict = {x.split(' ')[0]: y for (x,y) in plyr_dict.items() if x.split(' ')[1] == 'D/ST'}
    return plyr_dict, d_plyr_dict
