import pandas as pd
from tqdm import tqdm
from bond  import Bond,ILB
from datasets import get_data
import pickle

df_prices, df_info = get_data()

all_bonds = df_info.index #bond ids
ilbs = df_info[df_info["TYPE"]=="ILB"].index #nur vom typ ilb
noms = df_info[df_info["TYPE"]=="NOM"].index

bond_objs = []
for bond in all_bonds:
    name = df_info.loc[bond,"NAME"]
    issue_date = df_info.loc[bond,"ISSUE DATE"]
    redem_date = df_info.loc[bond,"REDEMPTION DATE"]
    prices = df_prices[bond]
    coupon_dates = Bond.parse_coupon_dates(df_info.loc[bond,"COUPON DATES"])

    #ILBs MIT SKALIERUNG DER CASHFLOWS -> NUR FÜR DATEN MÖGLICH, AN DENEN AUCH CPI BERECHNET WERDEN KANN
    #if df_info.loc[bond,"TYPE"] == "ILB":
    #    coupon = df_info.loc[bond,"INDEX LINKED COUP"]
    #    ilb = ILB(issue_date,redem_date,coupon,coupon_freq=coupon_dates,id=bond,prices=prices,name=name)
    #    if ilb.redem_date < ilb.max_poss_redem_date: #nur dann kann der historische cashflow und damit ytm berechnet werden
    #        bond_objs.append(ilb)

    #HIER WENN ILBs WIE NORMALE EVALUIERT WERDEN SOLLEN
    if df_info.loc[bond,"TYPE"] == "ILB":
        coupon = df_info.loc[bond,"INDEX LINKED COUP"]
        bond_objs.append(Bond(issue_date,redem_date,coupon,coupon_freq=coupon_dates,id=bond,prices=prices,name=name))
    else:
        coupon = df_info.loc[bond,"COUPON"]
        bond_objs.append(Bond(issue_date,redem_date,coupon,coupon_freq=coupon_dates,id=bond,prices=prices,name=name))

#df = pd.DataFrame() #holds only date|YTMs for every bond -> csv
data = {} #holds yield curve dataframes date|price|TTM|YTM für jeden bond
for bond in tqdm(bond_objs):
     print("EVALUATING:", bond.id)
     yc = bond.yield_curve(dirty=True)
     data[bond.id] = yc
     #df[bond.id] = yc["YTM"]

#WRITE TO DISK   
with open("export/ytm_ilb_as_nominal_dataframes.pickle","wb") as f:
    pickle.dump(data,f)