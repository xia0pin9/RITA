##########################################
#           EXTERNAL LIBRARIES           #    
##########################################
import datetime
from collections import defaultdict

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
NAME = "cross-analysis"
DESC = "Look for machines that were flagged for exhibiting multiple indicators of compromise"
CROSSREF_BEHAVIORS = ['likely_beacons','dns','concurrent', 'blacklisted','urls', 'scanning', 'useragent']

OPTS = {
        "customer": {
            "type": "string",
            "value": ""
            },
        "result_type": {
            "type": "string",
            "value": "cross_analysis"
            },
        "server": {
            "value": "http://localhost:9200",
            "type": "string"
            }
        }

class CrossrefModule(Module):
    def __init__(self):
        super(CrossrefModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"],
            self.options["result_type"]["value"],
            self.options["server"]["value"])
##########################################
#           END MODULE SETUP             #    
##########################################

def write_data(src, data, customer, result_type):
    # format new entry
    entry = {}
    entry[SOURCE_IP]   = src
    entry['count']     = len(data)
    entry['behaviors'] = data
    entry[TIMESTAMP]   = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type)

def find_cross_analysis(customer, result_type):
    # Search will be conducted in log files
    doc_type = 'results'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, 'result_type']
    
    # restrict results to specified customer and eventId to list of possible IDs
    constraints = []
    
    # anything we want to filter out
    ignore = []

    sort = ""

    # create dictionary to store user login info
    crossref_dict = defaultdict(dict)

    scroll_id = ""

    scrolling = True

    scroll_len = 1000

    count = 0
    error_count = 0

    print(colors.bcolors.OKBLUE +'>>> Retrieving information from elasticsearch...')
    
    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len, sort)

        # For every unique username (used as dict key), make a dictionary of event activity
        for entry in hits:
            try:
                src_list = entry['fields'][SOURCE_IP]
                behavior = entry['fields']['result_type'][0]

                if behavior not in CROSSREF_BEHAVIORS:
                    continue              
            except:
                error_count += 1
                continue

            for src in src_list:
                # If src has not been added to dictionary, add it
                if src not in crossref_dict:
                    crossref_dict[src] = []

                if behavior not in crossref_dict[src]:
                    crossref_dict[src].append(behavior)
            

        # stop scrolling if no more hits
        if len(hits) < 1:
          scrolling = False
        else:
            count += len(hits)
            # Report progress
            if (count % 10 == 0) or (count == scroll_size):
                progress_bar(count, scroll_size)

    crossref_dict_len = len(crossref_dict)
    if not (crossref_dict_len == 0):
        num_found = 0
        print('>>> Performing cross-analysis and writing results to elasticsearch... '+ colors.bcolors.ENDC)

        # Record all src ips with multiple behaviors
        count = 0
        for src in sorted(crossref_dict, key=lambda src: len(crossref_dict[src]), reverse=True):
            # Report progress
            progress_bar(count, crossref_dict_len)
            count += 1
            if len(crossref_dict[src]) > 1:
                num_found += 1
                write_data(src, crossref_dict[src], customer, result_type)

        print(colors.bcolors.WARNING + '[+] ' + str(num_found) + ' source IPs with multiple malicious behaviors found! [+]'+ colors.bcolors.ENDC)
    else:
        print (colors.bcolors.WARNING + '\nQuerying elasticsearch failed - Verify that you have ran the other modules first!'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped! [!]'+ colors.bcolors.ENDC)

def run(customer, result_type, server):
    global ht_data
    ht_data = ESServer(server)

    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE   + '[-] Finding concurrent logins for customer '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)

    # Delete Previous Results
    ht_data.delete_results(customer, result_type)
    
    find_cross_analysis(customer, result_type)

    print(colors.bcolors.OKGREEN   + '[+] Finished finding concurrent logins for customer '
          + colors.bcolors.HEADER  + customer
          + colors.bcolors.OKGREEN + ' [+]'
          + colors.bcolors.ENDC)

