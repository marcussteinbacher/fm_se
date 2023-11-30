import pandas as pd

#df_prices
with pd.ExcelFile("data/can_copy.xlsx") as xls:
    df_prices = pd.read_excel(xls,"Price",index_col=0,parse_dates=True)
    df_prices.columns = df_prices.columns.map(str)

#df_info
with pd.ExcelFile("data/can_copy.xlsx") as xls:
    df_info = pd.read_excel(xls,"Info",index_col=0,dtype={"ISSUE DATE":str,"REDEMPTION DATE":str,'START YEAR':str,'MATURITY YEAR':str})
    df_info.index = df_info.index.map(str)
    df_info.loc[:,"ISSUE DATE"] = df_info.loc[:,"ISSUE DATE"].map(lambda d: pd.to_datetime(d,format = "%d/%m/%Y"))
    df_info.loc[:,"REDEMPTION DATE"] = df_info.loc[:,"REDEMPTION DATE"].map(lambda d: pd.to_datetime(d,format = "%d/%m/%Y"))
    df_info.sort_values(by="ISSUE DATE",inplace=True)

#[TODO] other data: cpi, ip, ippi ...


def get_data()->tuple[pd.DataFrame,pd.DataFrame]:
    """
    Returns a tuple of pd.Dataframes: (prices, info)
    """
    return df_prices, df_info