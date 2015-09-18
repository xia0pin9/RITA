from importer import Importer

import csv

NAME = "Generic CSV"
DESC = "Read in a CSV to Elasitcsearch with formatting set for hunt teaming"
OPTS = {
        "delimiter": ',',
        "quotechar": '"',
        "chunk_size": 10000
        }

class Generic_CSV(Importer):
    def __init__(self):
        super(Generic_CSV, self).__init__("generic_csv", NAME, DESC, OPTS)

    def Read(self):
        flist = self.ListFiles()
        print(flist)
        for fpath in flist:
            if self.options["path"][-1] == '/':
                fpath = self.options["path"] + fpath
            else:
                fpath = self.options["path"] + "/" + fpath
            if ".csv" not in fpath:
                continue
            with open(fpath, 'r') as f:
                print("Reading data...")
                syntax_line = f.readline()
                if syntax_line[0] != '!':
                    continue
                syntax_line = syntax_line[1:]
                syntax_list = [x.strip() for x in syntax_line.split(',')]
                
                rdr = csv.reader(f, delimiter=',', quotechar='"')
                
                bunch = []
                for data in rdr:
                    d = dict(zip(syntax_list, data))
                    bunch.append(d)
                print("Writing data...")
                self.Write(bunch, chunk= int(self.options["chunk_size"]))
                print("Write completed")

if __name__ == "__main__":
    r = Generic_CSV()
    r.SetOption("path", "/home/rat/lawrence-python-ht/app/import/")
    r.SetOption("customer", "testing")
    r.SetOption("server", "http://192.168.1.100:9200/")
    r.Read()
