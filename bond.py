import pandas as pd
import numpy as np
import math as m
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
    def __init__(self,id:str,name:str,issue_date:pd.Timestamp,redem_date:pd.Timestamp,prices:pd.Series,coupon:float,coupon_freq=[]):
        self.id = id
        self.name = name
        self.issue_date = issue_date
        self.redem_date = redem_date
        self.prices = prices.dropna()
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

        dt_idx = pd.DatetimeIndex([])
        if self.freq > 0:
            for cf_date in self.coupon_freq:
                dt_idx = dt_idx.append(pd.date_range(start=self.issue_date,end=self.redem_date,freq=cf_date))
        
        return dt_idx.sort_values().unique()

    def __repr__(self):
        return f"{self.id} | {self.name} | {self.coupon}\n{self.issue_date.strftime("%d/%m/%y")} - {self.redem_date.strftime("%d/%m/%y")}" 
    
    def cashflows(self, evaluation_date:pd.Timestamp,dirty=True,daycount="act/365",force=False)->pd.Series:
        """
        A chronological ordered series of cashflows that starts with the negative price at evaluation date (=settlement_date).
        dirty: bool: If True, calculates the accrued interest and adds it to the first cashflow (purchase).
        force: bool: If True, assumes par value (100) for the market price if no price is reprted for the given evaluation date.
        """
        try:
            p = self.prices.loc[evaluation_date]
        except KeyError:
            print(f"No market price is reported for the evaluation date {evaluation_date.strftime("%Y-%m-%d")}.")
            if force:
                print(f"Assume par value for the evaluation date {evaluation_date.strftime("%Y-%m-%d")}!")
                p = 100
            else:
                print("You can force a cashflow with passing force=True. This assumes the non-existent price at evaluation date to trade at par (=100).")

    
        all_dates = self.__coupon_dates().append(pd.DatetimeIndex([self.issue_date,evaluation_date,self.redem_date])).sort_values().unique()
        
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
        
    def ytm(self,evaluation_date:pd.Timestamp,dirty=True,daycount="act/365",force=False):
        """
        evaluation_date: pd.Timestamp: Date for which to evaluate the bond (fictional purchase day).
        dirty: bool: If true, the first cashflow includes accured interest for the days since the last coupon.
        daycount: str: The daycount convention to use for coupon payments; one of 'act/act', 'act/360', 'act/365'
        Solves for the internal rate in the sum of all discounted cashflows starting from evaluation_date to redemption date.
        -p + sum cp_t/(1+r)**(delta_d/365) + fv/(1+r)**(delta_d/365) = 0.
        """
        
        cfs = self.cashflows(evaluation_date,dirty=dirty,daycount=daycount,force=force)
        
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
            print(evaluation_date.strftime("%Y-%m-%d"), ": ",e)
    
        return r
    
    def estimate_ytm(self, evaluation_date:pd.Timestamp,daycount="act/365")->float:
        """
        If the solver doesn't converge, one can use an estimation:
        r = (c + (100-p_t)/(ttm*freq)) / (100+p_t)/2
        """
        c = self.coupon
        p = self.prices.loc[evaluation_date]
        freq = self.freq
        ttm = (self.redem_date-evaluation_date).days / self.__days_in_year(daycount) 
        n = ttm*freq
        
        return (c + (100-p)/n) / ((100+p)/2)
    
    def yield_curve(self, daycount: str="act/365") -> pd.DataFrame:
        """
        Returnes a pd.DataFrame with the yield to maturity and term to maturity for each date in the total observed runtime of the bond.
        In other words: Calcualates the YTM (self.ytm()) and the date difference TTM in years for every observed trading day of the bond in self.prices
        |date       |TTM    |YTM    |
        |01.05.1998 |4.753  |0.05763|
        |...        |...    |...    |
        """

        def ytm_for_row(row):
            date = row.name
            ytm = self.ytm(date)
            
            return ytm

        days_in_year = self.__days_in_year(daycount)
        #idx = self.prices.loc[self.prices.index<self.redem_date].index #nicht für das letzte datum, da da 0
        #df = pd.DataFrame(index = idx)
        df = pd.DataFrame(index = self.prices.index)
        df["TTM"] = (self.redem_date - df.index).days / days_in_year
        df["YTM"] = df.apply(ytm_for_row, axis=1)

        #df.loc[self.redem_date,["TTM","YTM"]] = [0,0]

        return df
        

class ILB(Bond):
    """
    ref_cpi_base: float: If no value is specified the reference CPI is calculated based on the issue date of the ILB.
    """
    def __init__(self,*args,ref_cpi_base:float=None,**kwargs):
        super().__init__(*args,**kwargs) #args und kwargs, die das parent braucht
        self.ref_cpi = RefCPI()
        if ref_cpi_base:
            self.ref_cpi_base = ref_cpi_base
        else:
            self.ref_cpi_base  = self.ref_cpi.ref_cpi(self.issue_date)
    
    def cashflows(self, evaluation_date:pd.Timestamp,dirty=True,daycount="act/365",force=False)->pd.Series:
        cfs_nom = super().cashflows(evaluation_date,dirty,daycount=daycount,force=force)
        
        irs = [self.ref_cpi.ref_cpi(date)/self.ref_cpi_base for date in cfs_nom.index] #jeden cashflow ausser den Kauf mit IR multiplizieren
        irs[0] = 1
        
        self.index_ratios = pd.Series(data = irs ,index=cfs_nom.index).round(decimals=5)
        return cfs_nom * self.index_ratios
    

if __name__ == "__main__":
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

    eval_date = pd.Timestamp("2018-07-23")

    #COUPON BOND
    bond = Bond(bnd_id,name,issue_date,redem_date,prices,coupon,coupon_freq=["AS-DEC","AS-JUN"])
    nominal_cfs = bond.cashflows(eval_date,dirty=True,daycount="act/365")
    print("EVALUATION AS NOMINAL COUPON BOND")
    print(nominal_cfs)
    print(bond.ytm(eval_date))
    print(bond.estimate_ytm(eval_date))
    print(bond.yield_curve())

    #ZERO BOND
    zb = Bond(bnd_id,name,issue_date,redem_date,prices,0)
    zb_cfs = zb.cashflows(eval_date)
    print("EVALUATION AS ZERO BOND")
    print(zb_cfs)

    #REAL RETURN COUPON BOND
    ilb = ILB(bnd_id,name,issue_date,redem_date,prices,coupon,coupon_freq=["AS-DEC","AS-JUN"])
    ilb_cfs = ilb.cashflows(eval_date)
    print("EVALUATION AS COUPON ILB")
    print(ilb_cfs)
    print(ilb.index_ratios)
    print(ilb.ytm(eval_date))

    #REAL RETURN ZERO BOND
    zb_ilb = ILB(bnd_id,name,issue_date,redem_date,prices,0)
    zb_ilb_cfs = zb_ilb.cashflows(eval_date)
    print("EVALUATION AS ZERO COUPON ILB")
    print(zb_ilb_cfs)