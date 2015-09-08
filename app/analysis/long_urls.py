import data as ht_data
import colors
from module import Module

NAME = 'long_urls'
DESC = 'Search Logs for Unusually Long URLs'
THRESHOLD = 1000 # number of longest urls to retrieve
OPTS = {
        "threshold": THRESHOLD,
        "customer": "",
        "result_type": "long_urls"
        }

class LongUrlsModule(Module):
    def __init__(self):
        super(LongUrlsModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"], self.options["result_type"])


def write_data(data, customer, result_type):

    # Iterate over each item 
    for item in data:
        # format new entry
        entry = {}
        entry['customer'] = customer
        entry['src']      = item['fields']['src']
        entry['url']      = item['fields']['dst']
        entry['@timestamp'] = datetime.datetime.now()

        # write entry to elasticsearch
        ht_data.write_data(entry, result_type)
        

def run(customer, result_type = 'long_urls'):
    print(colors.bcolors.OKBLUE + '[-] Finding long URLs for customer *' + customer + '* [-]')

    # searching for duration in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = ['src', 'url']
    
    # restrict results to specified customer
    constraints = [{'customer':customer}]
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""

    scrolling = True

    print('>>> Retrieving information from elasticsearch...')

    # YE OLDE JSON QUERY
    sort = {
      "_script": {
         "script": "doc['url'].value.length()",
         "type": "number",
         "order": "desc"
        }
    }

    results = []

    while scrolling:
        scroll_len = THRESHOLD - len(results)
        # Retrieve data, which will come in sorted by longest entry for url field
        hits, scroll_id = ht_data.get_data(doc_type,fields, constraints, ignore, scroll_id, scroll_len, sort)
        
        if len(hits) < 1:
            break

        results.append(hits)

    
    # WRITE THE DATAS
    print('>>> Writing results of analysis...' + colors.bcolors.ENDC)
    for res in results:        
        write_data(res, customer, result_type)


    print(colors.bcolors.OKGREEN + '[+] Finished checking long URLs for customer *' + customer + '* [+]' + colors.bcolors.ENDC)
