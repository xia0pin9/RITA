from generic_csv import Generic_CSV
from generic_silk import Generic_SiLK

def Register():
    ret = []
    
    csv = Generic_CSV()
    ret.append(csv)

    silk = Generic_SiLK
    ret.append(silk)

    return ret
