from bond import Bond, ILB
import pandas as pd


with pd.ExcelFile("data/can.xlsx") as xls:
    df_prices = pd.read_excel(xls,"Price",index_col=0,parse_dates=True)
    df_prices.columns = df_prices.columns.map(str)

with pd.ExcelFile("data/can.xlsx") as xls:
    df_info = pd.read_excel(xls,"Info",index_col=0)
    df_info.index = df_info.index.map(str)
    df_info.loc[:,"ISSUE DATE"] = pd.to_datetime(df_info["ISSUE DATE"],format="%d/%m/%Y")
    df_info.loc[:,"REDEMPTION DATE"] = pd.to_datetime(df_info["REDEMPTION DATE"],format="%d/%m/%y")


bnd_id = "597973"
name = df_info.loc[bnd_id,"NAME"]
issue_date = df_info.loc[bnd_id,"ISSUE DATE"]
redem_date = df_info.loc[bnd_id,"REDEMPTION DATE"]
prices = df_prices[bnd_id]
coupon = df_info.loc[bnd_id,"INDEX LINKED COUP"]

eval_date = pd.Timestamp("2020-05-01")

#COUPON BOND
bond = ILB(issue_date,redem_date,coupon,name=name,coupon_freq=["AS-DEC","AS-JUN"])
print(bond)

nominal_cfs = bond.cashflows(eval_date,100,dirty=True,daycount="act/365")

print("EVALUATION AS NOMINAL COUPON BOND")
print(nominal_cfs)

print("YTM: ",bond.ytm(eval_date,100))
bond.prices = prices

#print(bond.yield_curve())


#ZERO BOND
zb = Bond(issue_date,redem_date,0)
zb_cfs = zb.cashflows(eval_date,100)
print("EVALUATION AS ZERO BOND")

print(zb_cfs)
