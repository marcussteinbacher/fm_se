import pandas as pd
from tqdm import tqdm
from bond  import ILB
import pickle
from cpi import RefCPI

with pd.ExcelFile("data/can.xlsx") as xls:
    df_info = pd.read_excel(xls,"Info",index_col=0)
    df_info.index = df_info.index.map(str)
    df_info.loc[:,"ISSUE DATE"] = pd.to_datetime(df_info["ISSUE DATE"],format="%d/%m/%Y")
    df_info.loc[:,"REDEMPTION DATE"] = pd.to_datetime(df_info["REDEMPTION DATE"],format="%d/%m/%y")

with pd.ExcelFile("data/can.xlsx") as xls:
    df_prices = pd.read_excel(xls,"Price",index_col=0,parse_dates=True)
    df_prices.columns = df_prices.columns.map(str)


ilbs = df_info[df_info["TYPE"]=="ILB"].index #nur vom typ ilb

bonds = []
for ilb in ilbs:
    name = df_info.loc[ilb,"NAME"]
    issue_date = df_info.loc[ilb,"ISSUE DATE"]
    redem_date = df_info.loc[ilb,"REDEMPTION DATE"]
    prices = df_prices[ilb]
    coupon = df_info.loc[ilb,"INDEX LINKED COUP"]
    coupon_dates_raw = df_info.loc[ilb,"COUPON DATES"]
    if type(coupon_dates_raw) == str:
        coupon_dates = ["AS-JUN","AS-DEC"]
    else:
        coupon_dates = []
    
    bonds.append(ILB(ilb,name,issue_date,redem_date,prices,coupon,coupon_freq=coupon_dates))

date = pd.Timestamp("2023-10-01")
data = {}
for ilb in tqdm(bonds):
    pass
    #print("EVALUATING:", ilb.id)
    
    #data[bond.id] = bond.yield_curve()

#with open("export/yield_curves.pickle","wb") as f:
#    pickle.dump(data,f)

my_ilb = bonds[0]
print(my_ilb)
print(my_ilb.ref_cpi.ref_cpi(my_ilb.issue_date))

