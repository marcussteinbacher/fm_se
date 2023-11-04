import pandas as pd
import numpy as np
import scipy as sp
from cpi import RefCPI

class Bond():
    """
    id: str
    name: str
    issue_date: pd.Timestamp 
    redem_date: pd.Timestamp
    prices: pd.Series: The timeseries of market prices where the respective index of type pd.DatetimeIndex
    coupon: float (nominal coupon)
    coupon_dates: list of strings: e.g.['AS-JUN','AS-DEC']: yearly on the first of June and first of December. See pd.date_range! If 
        the list is empty, the bond ist calculated as a zero coupon bond.
    """
    
    def __init__(self,issue_date:pd.Timestamp,redem_date:pd.Timestamp,coupon:float,coupon_freq:list[str,]=[],id:str=None,name:str=None,prices:pd.Series=None):
        self.id = id
        self.name = name
        self.issue_date = issue_date
        self.redem_date = redem_date
        self.prices = prices
        self.coupon = coupon
        self.freq = len(coupon_freq)
        self.coupon_freq = coupon_freq

    def __days_in_year(self,daycount: str) -> int:
        """
        Returns the days in one year depending on the chosen day count convention.
        daycount: str: one of 'act/365','act/360'.
        """
        if daycount == "act/365":
            days_in_year = 365
        elif daycount == "act/360":
            days_in_year = 360
        else:
            raise NotImplementedError(f"Day count convention {daycount} not implemented.")
        return days_in_year

    def __coupon_dates(self)->pd.DatetimeIndex:
        """
        Returns all coupon dates within the total runtime (issue_date to redem_date) of the bond in chronological order.
        """
        cp_dates = pd.DatetimeIndex([])
        if self.freq > 0:
            for cf_date in self.coupon_freq:
                cp_dates = cp_dates.append(pd.date_range(start=self.issue_date,end=self.redem_date,freq=cf_date))
        
        return cp_dates.sort_values()

    def __repr__(self):
        return f"{self.id} | {self.name} | {self.coupon}\n{self.issue_date.strftime("%d/%m/%y")} - {self.redem_date.strftime("%d/%m/%y")}" 
    
    def cashflows(self, evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365",force=False)->pd.Series:
        """
        A chronological ordered series of cashflows that starts with the negative price at evaluation date (=settlement_date).
        dirty: bool: If True, calculates the accrued interest and adds it to the first cashflow (purchase).
        force: bool: If True, assumes par value (100) for the market price if no price is reprted for the given evaluation date.
        """

        p = price

        all_dates = self.__coupon_dates().append(pd.DatetimeIndex([self.issue_date,evaluation_date,self.redem_date])).unique().sort_values()

        cf_dates = all_dates[all_dates>=evaluation_date] # incl settlement day und alle cfs danach
        cp_dates = self.__coupon_dates()[self.__coupon_dates()>=evaluation_date] # nur tage, an denen coupon kommt; wenn settlement_day = coupon zahlung, ann an diesem tag keine coupon zahlung

        cfs = pd.Series(data=0.0,index=cf_dates)

        #Accrued interest evaluation for dirty price
        acc_interest = 0
        days_between_cps = self.__days_in_year(daycount)/2
            
        if dirty:
            p_loc = all_dates.get_loc(evaluation_date)
           
            #das coupon datum, das eines vor dem settlement datum liegt
            previous_cp_date = all_dates[p_loc-1]
            days_since_last_cp = (evaluation_date - previous_cp_date).days

    	    #wenn evaluation date und coupon datum zusammenfallen, dann kein accrued interest für dieses evaluation date
            if not evaluation_date in cp_dates and evaluation_date != self.issue_date and self.freq>0:
                acc_interest = (self.coupon/self.freq) * (days_since_last_cp/days_between_cps)

        cfs.loc[evaluation_date] = - (p + acc_interest)
        if self.freq >0:
            cfs.loc[cp_dates[cp_dates>evaluation_date]] = self.coupon/self.freq #cfs.loc[cp_dates[cp_dates>evaluation_date]] += self.coupon/self.freq
        cfs.loc[self.redem_date] += 100 #letzter tag coupon + redemption

        return cfs
        
    def ytm(self,evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365",force=False):
        """
        evaluation_date: pd.Timestamp: Date for which to evaluate the bond (fictional purchase day).
        dirty: bool: If true, the first cashflow includes accured interest for the days since the last coupon.
        daycount: str: The daycount convention to use for coupon payments; one of 'act/act', 'act/360', 'act/365'
        Solves for the internal rate in the sum of all discounted cashflows starting from evaluation_date to redemption date.
        -p + sum cp_t/(1+r)**(delta_d/365) + fv/(1+r)**(delta_d/365) = 0.
        """
        
        cfs = self.cashflows(evaluation_date,price,dirty=dirty,daycount=daycount,force=force)

        days_in_year = self.__days_in_year(daycount) #365/360
        delta_days = cfs.index - evaluation_date

        def pv(r):
            s = 0
            for cf, dd in zip(cfs.values,delta_days.days):
                s += cf/(1+r)**(dd/days_in_year)
            return s

        r = np.nan
        try:
            r = sp.optimize.newton(pv,0)
        except RuntimeError as e:
            print(self.id,": ",evaluation_date.strftime("%Y-%m-%d"), ": ",e)
    
        return r
    
    
    def yield_curve(self,prices:pd.Series=None, daycount: str="act/365") -> pd.DataFrame:
        """
        Returnes a pd.DataFrame with the yield to maturity and term to maturity for each date in the total observed runtime of the bond.
        In other words: Calcualates the YTM (self.ytm()) and the date difference TTM in years for every observed trading day of the bond in self.prices
        |date       |TTM    |YTM    |
        |01.05.1998 |4.753  |0.05763|
        |...        |...    |...    |
        """
        if not prices is None:
            df = prices.to_frame(name="P")
        elif not self.prices is None: #wenn preise nicht direkt übergeben, dann checkne ob bei initialisierung übergeben wurden
            df = self.prices.to_frame(name="P")
        else:
            raise ValueError("Prices must be specified! Either set an instance attribute or function argument.")

        df = df.loc[self.issue_date:self.redem_date,:].dropna()

        def ytm_for_row(row):
            date = row.name
            price = row["P"]
            ytm = self.ytm(date,price)
            
            return ytm

        days_in_year = self.__days_in_year(daycount)
        
        df["TTM"] = (self.redem_date - df.index).days / days_in_year
        df["YTM"] = df.apply(ytm_for_row, axis=1)

        return df
        

class ILB(Bond):
    """
    ref_cpi_base: float: If no value is specified the reference CPI is calculated based on the issue date of the ILB.
    """
    def __init__(self,*args,ref_cpi_base:float=None,**kwargs):
        super().__init__(*args,**kwargs) #args und kwargs, die das parent braucht
        self.cpi = RefCPI(online=False)
        if ref_cpi_base:
            self.cpi_base = ref_cpi_base
        else:
            self.cpi_base  = self.cpi.ref_cpi(self.issue_date)
    
    def cashflows(self, evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365",force=False)->pd.Series:
        #nominal cashflows
        cfs_nom = super().cashflows(evaluation_date,price,dirty=dirty,daycount=daycount,force=force)
        
        #index ratios für jeden cashflow
        irs = [self.cpi.ref_cpi(date)/self.cpi_base for date in cfs_nom.index] #jeden cashflow ausser den ersten (Kauf) mit IR multiplizieren
        irs[0] = 1 #erster cashflow (Kauf) nicht mit IR skalieren
        
        self.index_ratios = pd.Series(data = irs ,index=cfs_nom.index).round(decimals=5)
        return cfs_nom * self.index_ratios
    

if __name__ == "__main__":
    pass
"""
    import argparse
    import sys 

    #bond.py ytm ilb issue_date redem_date coupon coupon_freq price

    op = sys.argv[1] #ytm, cf
    typ = sys.argv[2]

    if typ == "nominal":
        cls = Bond 
    elif typ == "ilb":
        cls = ILB
    else:
        print("Typ must be 'nominal' or 'ilb'!")
    
    bond = cls()
"""