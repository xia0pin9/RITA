from beaconing import BeaconingModule
from blacklisted import BlacklistedModule
from scan import ScanModule
from duration import DurationModule
from long_urls import LongUrlsModule
from concurrent import ConcurrentModule
from TBD import TBDModule

def Register():
    res = []
    
    beac = BeaconingModule()
    res.append(beac)

    tbd = TBDModule()
    res.append(tbd)

    blist = BlacklistedModule()
    res.append(blist)

    scan = ScanModule()
    res.append(scan)

    dur = DurationModule()
    res.append(dur)

    lu = LongUrlsModule()
    res.append(lu)

    cc = ConcurrentModule()
    res.append(cc)

    return res
