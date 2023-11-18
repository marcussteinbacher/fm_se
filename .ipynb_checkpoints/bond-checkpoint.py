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
    prices (optional): pd.Series: The timeseries of market prices where the respective index of type pd.DatetimeIndex. 
        Prices can also be set via the self.prices attribute and are needed for the calculation of the historical yields.
    coupon: float (nominal coupon)
    coupon_dates (optional): list of strings: e.g.['AS-JUN','AS-DEC']: annually on the first of June and first of December. See pd.date_range! 
        If the list is empty, the bond ist calculated as a zero coupon bond.
    """
    @staticmethod
    def parse_coupon_dates(s:str,format="%d/%m",sep=",")->list[str,]:
        vals = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
        trans_dict = {k:v for k,v in enumerate(vals,start=1)}
        months = []
        if s and type(s)==str: #wenn leer, dann ist np.nan, aber bool(np.nan) = True
            for cp_dt in s.split(sep):
                ts = pd.to_datetime(cp_dt,format=format)
                months.append("AS-"+trans_dict[ts.month])
        return months
 
    
    def __init__(self,issue_date:pd.Timestamp,redem_date:pd.Timestamp,coupon:float,coupon_freq:list[str,]=[],id:str=None,name:str=None,prices:pd.Series=None):
        self.id = id
        self.name = name
        self.issue_date = issue_date
        self.redem_date = redem_date
        self.prices = prices
        self.coupon = coupon
        self.freq = len(coupon_freq)
        self.coupon_freq = coupon_freq

    def __days_in_year(self,date:pd.Timestamp,daycount: str="act/365") -> int:
        """
        Returns the days in one year depending on the chosen day count convention.
        daycount: str: one of 'act/365','act/360'.
        """
        if daycount == "act/365":
            days_in_year = 365
        elif daycount == "act/360":
            days_in_year = 360
        elif daycount == "act/act":
            last_day_of_year = date.replace(day=31,month=12)
            days_in_year = last_day_of_year.day_of_year
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
    
    def cashflows(self, evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365")->pd.Series:
        """
        A chronologically ordered series of cashflows that starts with the negative price at evaluation date (=settlement_date).
        dirty: bool: If True, calculates the accrued interest and adds it to the first cashflow (purchase).
        """
        p = price

        all_dates = self.__coupon_dates().append(pd.DatetimeIndex([self.issue_date,evaluation_date,self.redem_date])).unique().sort_values()

        cf_dates = all_dates[all_dates>=evaluation_date] # incl settlement day und alle cfs danach
        cp_dates = self.__coupon_dates()[self.__coupon_dates()>=evaluation_date] # nur tage, an denen coupon kommt; wenn settlement_day = coupon zahlung, ann an diesem tag keine coupon zahlung

        cfs = pd.Series(data=0.0,index=cf_dates)

        #Accrued interest evaluation for dirty price
        acc_interest = 0
        days_between_cps = self.__days_in_year(evaluation_date,daycount)/2
            
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


    def current_yield(self,price:float)->float:
        """
        Returns the current yield of the bond if it was purchased at price p:
        p/coupon
        """
        return self.coupon/price

    def current_yield_curve(self, prices=None)->pd.DataFrame:
        """
        Returns a pd.Dataframe with the current yield for every trading day in the history of the bond.

        |date       |P      |CY     |
        |01.05.1998 |84.75  |0.0371 |
        |...        |...    |...    |
        """
        if not prices is None:
            df = prices.to_frame(name="P")
        elif not self.prices is None: #wenn preise nicht direkt übergeben, dann checkne ob bei initialisierung übergeben wurden
            df = self.prices.to_frame(name="P")
        else:
            raise ValueError("Prices must be specified! Either set an instance attribute or function argument.")

        df = df.loc[self.issue_date:self.redem_date,:].dropna()
        df["CY"] = df["P"].map(lambda p: self.current_yield(p))
        return df

    def ytm(self,evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365"):
        """
        evaluation_date: pd.Timestamp: Date for which to evaluate the bond (fictional purchase day).
        dirty: bool: If true, the first cashflow includes accured interest for the days since the last coupon.
        daycount: str: The daycount convention to use for coupon payments; one of 'act/act', 'act/360', 'act/365'
        Solves for the internal rate of return in the sum of all discounted cashflows to zero starting from the purchase at 
            market price on evaluation_date to redemption date.

        -p + sum cp_t/(1+r)**(delta_d/365) + fv/(1+r)**(delta_d/365) = 0.
        """
        
        cfs = self.cashflows(evaluation_date,price,dirty=dirty,daycount=daycount)

        delta_days = cfs.index - evaluation_date #series of date differences

        def pv(r):
            s = 0
            for date,cf, dd in zip(cfs.index,cfs.values,delta_days.days):
                days_in_year = self.__days_in_year(date,daycount=daycount)
    
                s += cf/(1+r)**(dd/days_in_year)
            return s

        r = np.nan
        try:
            r = sp.optimize.newton(pv,self.coupon/100)
        except RuntimeError as e:
            print(self.id,": ",evaluation_date.strftime("%Y-%m-%d"), ": ",price,": ",e)
    
        return r
    
    
    def yield_curve(self,prices:pd.Series=None, daycount: str="act/365") -> pd.DataFrame:
        """
        Returnes a pd.DataFrame with the yield to maturity and term to maturity for each date in the total observed runtime of the bond.
        In other words: Calcualates the YTM (self.ytm()) and the date difference TTM in years for every observed trading day of the bond in self.prices
        
        |date       |P      |TTM    |YTM    |
        |01.05.1998 |95.3   |4.753  |0.05763|
        |...        |...    |...    |...
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
    def __init__(self,*args,cpi_base:float=None,**kwargs):
        super().__init__(*args,**kwargs) #args und kwargs, die das parent braucht
        self.cpi = RefCPI(online=False) #initialisierung einer RefCPI instanz zur berechnung der referenz cpis für ein best datum
        if cpi_base:
            self.cpi_base = cpi_base
        else:
            self.cpi_base  = self.cpi.ref_cpi(self.issue_date)
        #maximalmögliches redemption date, um cashflows mit aufgetretenem cpi zu skalieren:
        # redemption date muss KLEINER sein als das letzte CPI Datum + 3 monate und der monats-erste
        self.max_poss_redem_date = max(self.cpi.series.index) + pd.DateOffset(months=3,day=1)
    
    def cashflows(self, evaluation_date:pd.Timestamp,price:float,dirty=True,daycount="act/365")->pd.Series:
        
        assert self.redem_date < self.max_poss_redem_date, f"Maximum possible redemption date to scale the future cashflows with historical index ratios is {(self.max_poss_redem_date - pd.DateOffset(days=1)).strftime('%d/%m/%Y')} while this ILB's redemption date is {self.redem_date.strftime('%d/%m/%Y')}."

        #nominal cashflows
        cfs_nom = super().cashflows(evaluation_date,price,dirty=dirty,daycount=daycount)
        
        #index ratios für jeden cashflow
        irs = [self.cpi.ref_cpi(date)/self.cpi_base for date in cfs_nom.index] #jeden cashflow ausser den ersten (Kauf) mit IR multiplizieren
        irs[0] = 1 #erster cashflow (Kauf zu pv) nicht mit IR skalieren
        
        self.index_ratios = pd.Series(data = irs ,index=cfs_nom.index).round(decimals=5)
        return cfs_nom * self.index_ratios
    

if __name__ == "__main__":
    issue_date= pd.Timestamp("1995-01-03")
    redem_date = pd.Timestamp("2023-06-01") #Um den tatsächlichen CF für einen ILB zu berechnen darf das redemption date nicht größer sein als da maximale datum der historischen CPIs
    coupon = 4
    eval_date = pd.Timestamp("2020-05-01")

    #COUPON BOND
    ilb = ILB(issue_date,redem_date,coupon,coupon_freq=["AS-DEC","AS-JUN"])
    print(ilb)
    print("Maximal mögliches Redemption Date: ",ilb.max_poss_redem_date)

    cfs = ilb.cashflows(eval_date,100,dirty=True,daycount="act/365")
    print(cfs)

    print("YTM: ",ilb.ytm(eval_date,100))
    print("Index Ratios: ",ilb.index_ratios)