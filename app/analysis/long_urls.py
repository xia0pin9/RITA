##########################################
#           EXTERNAL LIBRARIES           #    
##########################################
import datetime

##########################################
#           INTERNAL LIBRARIES           #    
##########################################
from yay_its_a_loading_bar import progress_bar
import colors
from data import ESServer
from field_names import *
from module import Module

##########################################
#              MODULE SETUP              #    
##########################################
NAME = 'long_urls'
DESC = 'Search Logs for Unusually Long URLs'

# Default number of longest urls to retrieve
LONG_URL_threshold = 1000

OPTS = {
        "customer": { 
            "value": "",
            "type": "string"
            },
        "threshold": {
            "value": LONG_URL_threshold,
            "type": "number"
            },
        "result_type": {
            "value": "long_urls",
            "type": "string"
            },
        "server": {
        "type": "string",
        "value": "http://localhost:9200"
        }
        }

class LongUrlsModule(Module):
    def __init__(self):
        super(LongUrlsModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"],
            self.options["threshold"]["value"], 
            self.options["result_type"]['value'], 
            self.options['server']['value'])
##########################################
#           END MODULE SETUP             #    
##########################################

def write_data(data, customer, result_type):
    # format new entry
    entry = {}
    entry[SOURCE_IP]      = data[SOURCE_IP]
    entry[URL]            = data[URL]
    entry[TIMESTAMP]      = datetime.datetime.now()

    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type)
        

def find_long_urls(customer, threshold, result_type):
    # searching for duration in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, URL]
    
    # restrict results to specified customer
    constraints = []
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""

    scroll_len = 1000

    scrolling = True

    print(colors.bcolors.OKBLUE + '>>> Retrieving information from elasticsearch...')

    url_dict = {}

    count = 0
    error_count = 0

    while scrolling:

        # Retrieve data, which will come in sorted by longest entry for url field
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)
              
        progress_bar(count, scroll_size)   
        for i in hits:
            count += 1

            try:
                url = i['fields'][URL][0]
                data = i['fields']
            except:
                error_count += 1
                continue

            key = len(url)

            # If key already exists, append the data, otherwise create new key with list that holds data
            if key in url_dict.keys():            
                url_dict[key].append(data)
            else:
                url_dict[key] = [data]

        

        if len(hits) < 1:
            scrolling = False

    # Get total number of keys (unique url lengths)
    total_keys = len(url_dict)

    # Verify that ES query actually returned some results
    if not total_keys == 0:
        print '>>> Finding the longest URLS... '
        final_res = []
        key_count = 0
        keys = sorted(url_dict.keys(), reverse=True)
        done = False

        # Get threshold amount of longest urls
        for url_length in keys:            
            if done == True:
                break
            for entry in url_dict[url_length]:
                if (key_count % 10 == 0) or (key_count == threshold):
                    progress_bar(key_count, threshold)
                key_count += 1
                if key_count > threshold:
                    done = True
                    break
                else:
                    final_res.append(entry)

        # WRITE THE DATA
        write_count = 0
        write_total = len(final_res)
        print '>>> Writing results of analysis...'
        for data in final_res:
            write_count += 1
            if (write_count % 10 == 0) or (write_count == write_total):        
                progress_bar(write_count, write_total)     
            write_data(data, customer, result_type)
            
            
    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file! [!]'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped! [!]'+ colors.bcolors.ENDC)

    

def run(customer, threshold, result_type, server):
    global ht_data
    ht_data = ESServer([server])

    print(colors.bcolors.OKBLUE + '[-] Finding long URLs for customer ' 
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)
    
    # Delete Previous Results
    ht_data.delete_results(customer, result_type)
    
    find_long_urls(customer, threshold, result_type)

    print(colors.bcolors.OKGREEN + '[+] Finished checking long URLs for customer ' 
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKGREEN + ' [+]'
          + colors.bcolors.ENDC)
    