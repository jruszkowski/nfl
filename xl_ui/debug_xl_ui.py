import xlwings as xw
import dfs.calcs
import dfs.projections

wb = xw.Book("xl_ui.xlsm")
d = dfs.calcs.get_roster(wb, 'dk')
plyr_dict = dfs.projections.get_nf_projections()
d_plyr_dict = dfs.projections.get_nf_d_projections()
full_roster = dfs.calcs.apply_projection(d, plyr_dict, d_plyr_dict)
dfs.calcs.main(full_roster)

if __name__=="__main__":
    pass