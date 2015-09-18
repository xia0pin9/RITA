import abc
import json
from elasticsearch import Elasticsearch, helpers
from os import listdir
from os.path import isfile


class Importer(object):
    def __init__(self, file_type, name, description, options={}):
        """
        Initialize an importer object.
        
        file_type: String discription of the filetype this module is intended
        to import. Note that this will dictate where in the import directory 
        we will look for this file: ht/import/<file_type>/*

        server: Location of the Elasticsearch server which you plan to import data to
        defaults to [http://localhost:9200], note that it must be a list.
        
        customer: We'll be using this to build the standard convention name in the es
        server.
        """
        self.global_options = ["customer", "server"]
        self.options = options
        self.file_type = file_type
        self.fields = ['@timestamp','dst','dpt','src','spt','proto']
        self.name = name
        self.description = description

        self.options["customer"] = ""
        self.options["path"] = ""

        self.options["server"] = ["http://localhost:9200"]
    
    def ListFiles(self):
        return [  f 
                for f in listdir(self.options["path"]) ]

    def SetOption(self, key, value):
        """
        Set one of the object options
        """
        if key in self.options:
            self.options[key] = value
            return True
        return False

    def GetOptions(self):
        ret = {}
        for opt in self.options:
            if opt not in self.global_options:
                ret[opt] = self.options[opt]
        return ret

    def Write(self, data, chunk=10000):
        """
        Write a pile of records to Elasticsearch; data is a list of 
        dictionaries.
        """
        self.es = Elasticsearch(self.options["server"], timeout=600)
        
        # Create the index if it's not already there
        if not self.es.indices.exists(self.options["customer"]):
            res = self.es.indices.create(index=self.options["customer"])
            print("Create index response: ", res)

        all_records = len(data)
        bulk_data = []
        count = 0
        total = 0
        for item in data:
            count += 1
            temp = {
                "index": {
                    "_index": self.options["customer"],
                    "_type": 'logs'
                    }
                }
            bulk_data.append(temp)
            bulk_data.append(item)
            if (count % chunk) == 0:
                res = self.es.bulk(index=self.options["customer"], 
                        body=bulk_data, refresh=True)
                bulk_data = []
                total += count
                count = 0
                print("{0} out of {1} records processed".format(total, all_records)) 
            self.es.bulk(index=self.options["customer"],
                    body=bulk_data, refresh=True)

        pass

    @abc.abstractmethod
    def Read(self):
        """
        Read in from the file with the given path parsing data into structures to be 
        written to elasticsearch.
        """
