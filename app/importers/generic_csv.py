from importer import Importer
import time

import csv

NAME = "Generic CSV"
DESC = "Read in a CSV to Elasitcsearch with formatting set for hunt teaming"
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

class Generic_CSV(Importer):
    """
    This is an importer for an edge router log replacement. It was designed around the idea of sending
    all network traffic to a tshark script which pulls off just the syn sequences and encodes them to 
    csv. That script is (roughly) as follows:

    $ tshark -T fields -e frame.time -e eth.src -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport \ 
    -e _ws.col.Protocol -e tcp.flags -E header=n -E separator=, -E quote=d -E occurrence=f \
    1>test5.csv -w test5.pcap -ni en1 -f 'tcp[tcpflags] & (tcp-syn|(tcp-syn & tcp-ack)) !=0'

    Then place this at the path for Generic_CSV and add a line at the top of the CSV file containing
    the field names which starts with a !, so something like this:

    ! @timestamp, src_mac, src, spt, dst, dpt, proto

    Remember that how you name these fields counts! The fields will be added to the elasticsearch DB with
    the names you gave them, the analysis framework depends on these fields having certian names 
    (see analysis/field_names for the names used).
    """
    def __init__(self):
        super(Generic_CSV, self).__init__("generic_csv", NAME, DESC, OPTS)

    def Read(self):
        flist = self.ListFiles()
        print(flist)
        for fpath in flist:
            if self.options["path"]["value"][-1] == '/':
                fpath = self.options["path"]["value"] + fpath
            else:
                fpath = self.options["path"]["value"] + "/" + fpath
            if ".csv" not in fpath:
                continue
            with open(fpath, 'r') as f:
                print("Reading data...")
                syntax_line = f.readline()
                if syntax_line[0] != '!':
                    continue
                syntax_line = syntax_line[1:]
                syntax_list = [x.strip() for x in syntax_line.split(',')]
                
                rdr = csv.reader(f, delimiter=self.options["delimiter"]["value"], 
                        quotechar=self.options["quotechar"]["value"])
                
                bunch = []
                for data in rdr:
                    tmptime = time.strptime(data[0].split('.')[0], "%b %d, %Y %H:%M:%S")
                    data[0] = time.strftime("%Y-%m-%dT%H:%M:%S", tmptime) + ".000Z"            
                    d = dict(zip(syntax_list, data))
                    bunch.append(d)
                print("Writing data...")
                res = self.Write(bunch, chunk= int(self.options["chunk_size"]["value"]))
                print("Write completed")
        return res

if __name__ == "__main__":
    r = Generic_CSV()
    r.SetOption("path", "")
    r.SetOption("customer", "testing")
    r.SetOption("server", "")
    r.Read()
