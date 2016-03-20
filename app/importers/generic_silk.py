from importer import Importer
import time

from silk import *

NAME = "Generic SiLK"
DESC = "Read in SiLK records to Elasitcsearch with formatting set for hunt teaming"
OPTS = {
        "delimiter": {
            "value": ',',
            "type": "string"
            },
        "quotechar": { 
            "value": '"',
            "type": "string"
            },
        "chunk_size": {
            "value": 40000,
            "type": "number"
            }
        }

class Generic_SiLK(Importer):
    """
    This is an importer for an edge router log replacement. It was designed to pull off 
    just the syn sequences and insert them to ES.

    By default, the included field names are as follows:
    @timestamp, src, spt, dst, dpt, proto, duration

    Remember that how you name these fields counts! The fields will be added to the elasticsearch DB with
    the names you gave them, the analysis framework depends on these fields having certian names 
    (see analysis/field_names for the names used).
    """
    def __init__(self):
        super(Generic_SiLK, self).__init__("generic_silk", NAME, DESC, OPTS)

    def Read(self):
        flist = self.ListFiles()
        print(flist)
        syntax_list = ["@timestamp", "src", "spt", "dst", "dpt", "proto", "duration"]

        for fpath in flist:
            if self.options["path"]["value"][-1] == '/':
                fpath = self.options["path"]["value"] + fpath
            else:
                fpath = self.options["path"]["value"] + "/" + fpath
            
            infile = SilkFile(fpath, READ)
            bunch = []
            print("Reading data...")
            for rec in infile:
                if res.tcpflags & TCPFlags("S"):
                    data = []
                    data.append(rec.stime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]+"Z")
                    data.append(rec.sip)
                    data.append(rec.sport)
                    data.append(rec.dip)
                    data.append(rec.dport)
                    data.append(rec.protocol)
                    data.append(rec.duration)
                    d = dict(zip(syntax_list, data))
                    bunch.append(d)
            print("Writing data...")
            res = self.Write(bunch, chunk= int(self.options["chunk_size"]["value"]))
            print("Write completed")
        return res

if __name__ == "__main__":
    r = Generic_SiLK()
    r.SetOption("path", "")
    r.SetOption("customer", "testing")
    r.SetOption("server", "")
    r.Read()
