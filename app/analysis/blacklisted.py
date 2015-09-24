import urllib2
from multiprocessing import Process, Pool, Value, Lock, Queue, Manager
import multiprocessing
from collections import defaultdict
from field_names import *
import colors
from data import ESServer
from yay_its_a_loading_bar import progress_bar
import time
import datetime

from module import Module

###             ###
#   MODULE SETUP  #    
###             ###

NAME = 'blacklisted'
DESC = 'Find Blacklisted IPs in the Logs'

OPTS = {
    "customer": {
        "value": "",
        "type": "string"        
        },
    "result_type": { 
        "value": 'blacklisted',
        "type": "string"
        },
    "server": {
        "value": "http://localhost:9200",
        "type": "string"
        }
    }

class BlacklistedModule(Module):
    def __init__(self):
        super(BlacklistedModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"],
            self.options["result_type"]["value"],
            self.options["server"]["value"])


###                ###
#  END MODULE SETUP  #
###                ###



###                    ###
#   SHARED MEMORY SETUP  #    
###                    ###

TOTAL_TO_DO = Value('i', 1)
CURR_DONE = 0
UNLIKELY_CURR = 0
CURR_DONE = Value('i', 0)
UNLIKELY_CURR = Value('i', 0)
CURR_DONE_LOCK = Lock()

####                    ###
# END SHARED MEMORY SETUP #    
###                     ###


def write_data(data, customer, result_type):
    # format new entry
    entry = {}
    entry[SOURCE_IP]      = data[0]
    entry[DESTINATION_IP] = data[1]
    entry['times_seen']   = data[1]
    
    entry[TIMESTAMP] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type)

def filter_ip(ip_in):
    """
    Returns true if IP is an external ip
    """
    ret_val = False

    if ip_in[0] == '1':
        ip_split = ip_in.split('.')
        if (ip_split[0] != '10') and ((ip_split[0] + '.' + ip_split[1])
                                      != '192.168'):
            if ip_split[0] == '172':
                second_oct = int(ip_split[1])
                if (second_oct < 16) or (31 < second_oct):
                    ret_val = True
    else:
        ret_val = True

    return ret_val

def find_blacklisted_ipvoid_mp(arglist):
    global CURR_DONE
    global TOTAL_TO_DO

    check_list, customer, result_type = arglist

    # Get destination ip and list of sources it connected to
    dst      = check_list[0]
    src_list = check_list[1]

    # Report progress
    with CURR_DONE_LOCK:
        CURR_DONE.value += 1
        local_curr_done = CURR_DONE.value
        if (local_curr_done % 10 == 0) or (local_curr_done == TOTAL_TO_DO.value):
            progress_bar(local_curr_done, TOTAL_TO_DO.value)

    response = ""
    try:
        response = urllib2.urlopen('http://www.ipvoid.com/scan/' + dst)
    except:
        return

    html = response.read().decode('utf-8')
    if 'BLACKLISTED' in html:
        line_splt = html.split('BLACKLISTED ')
        times_seen = int(line_splt[1].split('/')[0])
        for src in src_list:
            write_data([src, dst, times_seen], customer, result_type)
    response.close()

def find_blacklisted_ipvoid(customer, result_type):
    global CURR_DONE
    global TOTAL_TO_DO

    CURR_DONE.value = 0

    # Analysis will be done on log files, not results
    doc_type = 'logs'

    # restrict results to specified customer
    constraints = []
    
    # anything we want to filter out
    ignore = []

    print(colors.bcolors.OKBLUE + '>>> Retrieving information from elasticsearch...')
    
    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP]


    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    count = 0
    error_count = 0

    # build dictionary for blacklist detection
    blacklist_dict = defaultdict(list)

    while scrolling:

        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len)
        
        progress_bar(count, scroll_size)

        # For every unique destination ip (used as dict key), find make a list of all
        # src ips that connect to it
        for entry in hits:
            count += 1
            try:
                dst =  entry['fields'][DESTINATION_IP][0]
                src =  entry['fields'][SOURCE_IP][0]
            except:
                error_count += 1
                continue

            # Verify that source IP is internal and that destination ip is external
            if len(dst) != 0 and len(src) != 0:
                if (filter_ip(src) == False) and (filter_ip(dst) == True):
                    # Check for duplicate source IPs
                    try:
                        if src not in blacklist_dict[dst]:
                            blacklist_dict[dst].append(src)
                    except:
                        continue
        
        if len(hits) < 1:
          scrolling = False

    # Get total number of keys (unique url lengths)
    total_keys = len(blacklist_dict)
    
    # Verify that ES query actually returned some results
    if not total_keys == 0:
        print('>>> Querying blacklist....')

        # Get the multiprocessing stuff ready
        TOTAL_TO_DO.value = len(blacklist_dict)
        workers = Pool(64)

        # create parameter list for threads and keys
        arglist = [(entry, customer, result_type) for entry in blacklist_dict.items()]
     
        # workers.map(find_blacklisted_ipvoid_mp, blacklist_dict.items())
        workers.map(find_blacklisted_ipvoid_mp, arglist)
    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file! [!]'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped! [!]'+ colors.bcolors.ENDC)


def run(customer, result_type, server):
    global BLACKLIST_COUNT
    global ht_data

    ht_data = ESServer([server])

    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE + '[-] Finding blacklisted URLS for customer '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)

    find_blacklisted_ipvoid(customer, result_type)

    print(colors.bcolors.OKGREEN + '[+] Finished finding blacklisted URLS for customer '
          + colors.bcolors.HEADER + customer
          + colors.bcolors.OKGREEN + ' [+]'
          + colors.bcolors.ENDC)

    hits, scroll_id, scroll_size = ht_data.get_data(customer, 'results', [], [{'result_type':result_type}], [], '', 1000)
    print(colors.bcolors.FAIL + '[!] Found ' + str(scroll_size) + ' connections to blacklisted URLs in log entries [!]'
          + colors.bcolors.ENDC)


