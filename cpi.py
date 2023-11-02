import pandas as pd
import datetime as dt

class RefCPI():
    def __init__(self, index="All-items"):
        df = pd.read_csv("data/cpi.csv",index_col="REF_DATE")
        df.index = df.index.map(lambda d: dt.datetime.strptime(d,"%Y-%m"))
        self.df = df[df["Products and product groups"]== index]
        self.available_indices = df["Products and product groups"].unique()

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
        ref_date = t - pd.DateOffset(months=lag, day=1)
        #print(ref_date, ref_date + pd.DateOffset(months=1,day=1))
        cpi_0 = self.df.loc[ref_date,"VALUE"]
        cpi_1 = self.df.loc[ref_date + pd.DateOffset(months=1, day=1),"VALUE"]

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
    base_date = pd.Timestamp("1995-12-10")
    date = pd.Timestamp("2021-12-01")

    ref_cpi = RefCPI()
    ref_cpi_base = ref_cpi.ref_cpi(base_date)

    print(f"Avialable Indices: {ref_cpi.available_indices}")
    print(f"Ref CPI for {base_date.strftime("%d/%m/%Y")}: {ref_cpi_base}")
    