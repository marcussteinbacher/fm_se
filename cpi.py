from matplotlib.cbook import index_of
import pandas as pd
import datetime as dt
import requests 
import json 

class RefCPI():
    def __init__(self,online=False,index = "All-items"):
        self.available_indices = None
        if online:
            self.series = self.__fetch()
        else:
            self.series = self.__read(index)
    
    def __read(self,index):
        """
        Read a csv from disk.
        """
        df = pd.read_csv("data/cpi.csv",index_col="REF_DATE")
        self.available_indices = df["Products and product groups"].unique()
        df = df[df["Products and product groups"]== index]
        df.index = df.index.map(lambda d: dt.datetime.strptime(d,"%Y-%m"))
        
        return df["VALUE"]


    def __fetch(self, name:str="V41690973")->pd.Series:
        """
        Fetch most current data from the BoC valet API:
        name: str: The name of the series: e.g. V41690973 = Total CPI not seasonally adjusted
        """
        r = requests.get("https://www.bankofcanada.ca/valet/observations/"+name+"/json")
        data = json.loads(r.text)
        label = data["seriesDetail"][name]["label"]
        index = [pd.Timestamp(observation["d"]) for observation in data["observations"]]
        values = [float(observation[name]["v"]) for observation in data["observations"]]
        series = pd.Series(index=index,data=values,name=label)

        return series

    def ref_cpi(self, t: pd.Timestamp, lag:int = 3)->float:
        """
        Berechnet den Ref CPI für ein Datum t lt. Bank of Canada, Real Return Bonds, pp. 1-2.
        Basis: CPI All items, seasonally not adjusted 1991 - 2023.
        params:
            t: pd.Timestamp: Das betrachtete Datum, für welches der Ref CPI berechnet werden soll.
            lag: int: Die Anzahl der Monate, die ausgehend von t bis zum jeweiligen Ersten zurückgegangen werden muss; default = 3.
        returns:
            float: Ref CPI für ein Datum t gerundet auf 5 Dezimalstellen (Bank of Canada, Real Return Bonds, p.1)
        """
        d,n = t.day, t.days_in_month
        ref_date = t - pd.DateOffset(months=lag, day=1) #der erste drei monate zuvor

        cpi_0 = self.series.loc[ref_date]
        cpi_1 = self.series.loc[ref_date + pd.DateOffset(months=1, day=1)] #zum ersten im folgemonat

        return round(cpi_0 + ((d-1)/n) * (cpi_1 - cpi_0),ndigits=5)

    def index_ratio(self, t: pd.Timestamp, base: pd.Timestamp)->float:
        """
        Berechnet den Index Ratio für ein Datum t und Basisdatum (=issue date) base lt. Bank of Canada, Real Return Bonds, pp. 1-2.
        params:
            t: pd.Timestamp: Das betrachtete Datum, für welches der IR berechnet werden soll.
            base: pd.Timestamp: Das Basisdatum, für welches der Ref CPI berechnet werden soll (= issue date des Bonds).
        returns:
            float: IR für Datum t und base gerundet auf 5 Dezimalstellen (Bank of Canada, Real Return Bonds, p.1)
        """
        return round(self.ref_cpi(t)/self.ref_cpi(base),ndigits=5)
    

if __name__ == "__main__":
    base_date = pd.Timestamp("1995-01-01")
    date = pd.Timestamp("2023-11-02")


    cpi = RefCPI(online=False)
    ref_cpi_base = cpi.ref_cpi(base_date)
    print(cpi.series)
    print(f"Ref CPI for {base_date.strftime("%d/%m/%Y")}: {ref_cpi_base}")
    
    max_date = cpi.series.index.max()
    print("Latest Value for: ",max_date," ",cpi.ref_cpi(max_date))

    min_date = cpi.series.index.min()
    print(f"Earliest Date: {min_date}")

    #print(cpi.ref_cpi(date))
