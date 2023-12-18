import pandas as pd
import numpy as np

#df_prices
with pd.ExcelFile("data/can.xlsx") as xls:
    df_prices = pd.read_excel(xls,"Price",index_col=0,parse_dates=True)
    df_prices.columns = df_prices.columns.map(str)

#df_info
with pd.ExcelFile("data/can.xlsx") as xls:
    df_info = pd.read_excel(xls,"Info",index_col=0,dtype={"ISSUE DATE":str,"REDEMPTION DATE":str,'START YEAR':str,'MATURITY YEAR':str})
    df_info.index = df_info.index.map(str)
    df_info.loc[:,"ISSUE DATE"] = df_info.loc[:,"ISSUE DATE"].map(lambda d: pd.to_datetime(d,format = "%d/%m/%Y"))
    df_info.loc[:,"REDEMPTION DATE"] = df_info.loc[:,"REDEMPTION DATE"].map(lambda d: pd.to_datetime(d,format = "%d/%m/%Y"))
    df_info.sort_values(by="ISSUE DATE",inplace=True)

def get_years_diff(date1:pd.Timestamp, date2:pd.Timestamp):
    return (date1.year - date2.year) +  (date1.dayofyear - date2.dayofyear)/365.25


def get_class(x:float)->str:
    """
    lower boundary exclusive, upper boundary inclusive
    """
    __classes = {"0-3y":(0,3),"3-5y":(3,5),"5-10y":(5,10),"10-20y":(10,20),"20y+":(20,np.inf)}
    for key, interval in __classes.items():
        if interval[0] < x <= interval[1]:
            return key

df_info["DURATION"] = df_info.apply(lambda r: get_years_diff(r["REDEMPTION DATE"],r["ISSUE DATE"]),axis=1)
df_info["CLASS"] = df_info.apply(lambda r: get_class(r["DURATION"]),axis=1)


#inflation  expectations & benchmark yield spread
df = pd.read_csv("data/inflation_expectations_and_bei.csv")
inflation_expectations = df.drop(columns=["INDINF_INFEXP_BOND_G"])
inflation_expectations.dropna(inplace=True)
inflation_expectations.index = pd.DatetimeIndex(data=inflation_expectations["date"])
inflation_expectations.drop(columns=["date"],inplace=True)
inflation_expectations.columns=["2-3y ahead","6-10y ahead"]
inflation_expectations = inflation_expectations/100
inflation_expectations = inflation_expectations.resample("MS").ffill() #upsample from quaterly to monthly data

yield_spread = df.loc[:,["date","INDINF_INFEXP_BOND_G"]]
yield_spread.dropna(inplace=True)
yield_spread.index = pd.DatetimeIndex(yield_spread["date"])
yield_spread.drop(columns=["date"],inplace=True)
yield_spread = yield_spread/100
yield_spread.columns = ["yield spread"]


#[TODO] other data: cpi, ip, ippi ...

if __name__ == "__main__":
    print(df_info.head())
    print(df_prices.head())