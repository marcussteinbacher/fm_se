from bond import Bond, ILB
from datasets import df_prices, df_info
import pandas as pd

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

nominal_cfs = bond.cashflows(eval_date,100,dirty=True,daycount="act/act")

print("EVALUATION AS COUPON BOND")
print(nominal_cfs)

print("YTM: ",bond.ytm(eval_date,100))
print("Index Ratios: ",bond.index_ratios)

# setting historical prices for the bond object
bond.prices = prices

#print(bond.yield_curve())


#ZERO BOND
zb = Bond(issue_date,redem_date,0)
zb_cfs = zb.cashflows(eval_date,100)
print("EVALUATION AS ZERO BOND")

print(zb_cfs)

#DATE PARSER
print(Bond.parse_coupon_dates("01/06,01/12"))

print(bond.current_yield_curve())

print("------------------------------------")
#UNVALID NUMBER IN SCALAR POWER
#2022-05-25
#2022-05-26
#2022-05-27
#2022-05-30
#2022-05-31

bnd_id = "491987" 
eval_time = pd.Timestamp("2022-06-01")
name = df_info.loc[bnd_id,"NAME"]
issue_date = df_info.loc[bnd_id,"ISSUE DATE"]
redem_date = df_info.loc[bnd_id,"REDEMPTION DATE"]
prices = df_prices[bnd_id]
coupon = df_info.loc[bnd_id,"INDEX LINKED COUP"]
cp_freq = Bond.parse_coupon_dates(df_info.loc[bnd_id,"COUPON DATES"])

inval_bnd = Bond(issue_date,redem_date,coupon,id=bnd_id,name=name,coupon_freq=cp_freq,prices=prices)
print(inval_bnd)
print(eval_time)

print(inval_bnd.ytm(eval_date,102.25))
print(df_prices.loc[eval_date,bnd_id])
print("---------------------------------")
df = pd.DataFrame()
for d, p in inval_bnd.prices.dropna().items():
    ytm = inval_bnd.ytm(d,p)
    df.loc[d,"YTM"] = ytm

print(df)