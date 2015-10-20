##########################################
#           EXTERNAL LIBRARIES           #    
##########################################

################################################################
# [!] KEEP FOLLOWING FOUR IMPORTS AT THE TOP AND IN ORDER [!]  #
# (This will force matplotlib to not use any Xwindows backend) #
################################################################
import matplotlib
matplotlib.use('Agg') 
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
################################################################

import os
import time
import datetime
from multiprocessing import Process, Pool, Value, Lock, Queue, Manager
import multiprocessing
from collections import defaultdict
import dateutil.parser as dt_parser
import numpy as np
import pylab as P

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
NAME = 'TBD'
DESC = 'Find some beacons in a cool new way. Maybe.'

##### Fucking Global variables for multiprocessing shit #######
TOTAL_TO_DO = Value('i', 1)
TIME_DICT = defaultdict(list)
CURR_DONE = 0
UNLIKELY_CURR = 0
CURR_DONE = Value('i', 0)
UNLIKELY_CURR = Value('i', 0)
CURR_DONE_LOCK = Lock()

# Default save directory for generated graphs
POTENTIAL_TBD_SAVE_DIR = '../graphs/potential_cool_beacon/'

# Time interval for buckets (in seconds)
DEFAULT_BUCKET_SIZE = 1

# Threshold for difference in standard deviation that determines beaconing
TBD_THRESH = 2

# Default protocol
TBD_PROTO = ""

OPTS = {
        "customer": {
            "value": "",
            "type": "string"
            },
        "proto": {
            "value": TBD_PROTO,
            "type": "string"
            },
        "bucket_size": {
            "value": DEFAULT_BUCKET_SIZE,
            "type": "number"
        },
        "threshold": {
            "value": TBD_THRESH,
            "type": "number"
        },
        "graph": {
            "value": False,
            "type": "bool"
            },
        "potential_save_dir": {
            "value": POTENTIAL_TBD_SAVE_DIR,
            "type": "string"
            },
        "result_type": {
            "value": 'tbd',
            "type": "string"
            },       
        "server": {
            "value": "http://localhost:9200",
            "type": "string"
            }
        }

class TBDModule(Module):
    def __init__(self):
        super(TBDModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"],
            self.options["proto"]["value"],
            self.options["bucket_size"]["value"],
            self.options["threshold"]["value"],
            self.options["graph"]["value"],
            self.options["potential_save_dir"]["value"],
            self.options["result_type"]["value"],            
            self.options["server"]["value"])
##########################################
#           END MODULE SETUP             #    
##########################################


def write_data(data, customer, proto, result_type):
    # format new entry
    entry = {}
    entry[PROTOCOL]         = proto
    entry[SOURCE_IP]        = data[0]
    entry[DESTINATION_IP]   = data[1]
    entry[DESTINATION_PORT] = data[2]
    
    entry[TIMESTAMP] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type, refresh_index = True)

def tbd_graph(customer, buckets, proto, src, dst, dpt):

    # Make directory to store graphs
    save_dir = './data/' + customer + "/buckets/"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Create string to indentify type in image title
    save_string = 'src-' + src.replace('.','_') + '_dst-' + dst.replace('.','_') + '_dpt-' + str(dpt) + '_proto-' + proto 

    fig = Figure()
    sub_fig = fig.add_subplot(111)
    canvas = FigureCanvas(fig)
    sub_fig.plot(buckets, linewidth=2.0)    
    sub_fig.set_title(save_string)
    sub_fig.set_xlabel('Time Buckets')
    sub_fig.set_ylabel('Connections in time bucket')
    P.gca().set_ylim(ymax=10)
    canvas.print_figure(save_dir + save_string + '.png')
    P.close(fig)

    
# def tbd_serial(times, bucket_size, thresh):
#     # Sort the timestamps
#     times = sorted(times)

#     # Create a new dictionary to hold time buckets
#     buckets = {}

#     # Iterate over all the timestamps
#     for i in range(0, len(times)-1):

#         # Determine the number of seconds between two consecutive timestamps
#         key= times[i+1] - times[i]

#         # Count the number of times specific time differences occur
#         if key not in buckets.keys():
#             buckets[key] = 1
#         else:
#             buckets[key] += 1

#     if len(buckets.keys()) > 0:
#         return np.max(list(buckets.values())), len(buckets)
#     else:
#         return None

def tbd_mp(arglist):
    global MIN_TIMESTAMPS
    global CURR_DONE
    global UNLIKELY_CURR
    global TOTAL_TO_DO
    global CURR_DONE_LOCK

    # Report progress
    with CURR_DONE_LOCK:
        CURR_DONE.value += 1
        local_curr_done = CURR_DONE.value
        if (local_curr_done % 20 == 0) or (local_curr_done == TOTAL_TO_DO.value):
            progress_bar(local_curr_done, TOTAL_TO_DO.value)
    
    # Unpack arguments
    key, times, bucket_size, thresh, db_queue = arglist

    # Sort the timestamps
    times = sorted(times)

    # Create a new dictionary to hold time buckets
    buckets = {}

    # Iterate over all the timestamps
    for i in range(0, len(times)-1):

        # Determine the number of seconds between two consecutive timestamps
        freq = times[i+1] - times[i]

        # Count the number of times specific time differences occur
        if freq not in buckets.keys():
            buckets[freq] = 1
        else:
            buckets[freq] += 1

    if len(buckets.keys()) > 0:
        ret_vals = (key, np.max(list(buckets.values())), len(buckets))
        db_queue.put( ret_vals )

def TBD_analysis(customer, proto, bucket_size, thresh, graph, save_dir, result_type):
    # Multiprocessing prep
    global TOTAL_TO_DO
    global CURR_DONE
    global TIME_DICT
    CURR_DONE.value = 0
    worker_pool = Pool(processes=None, maxtasksperchild=1)

    # searching for beacons in log files
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT, TIMESTAMP]
    
    # restrict results to specified customer
    if proto != "":
        constraints = [{PROTOCOL:proto}]
    else:
        constraints = []
    
    # anything we want to filter out
    ignore = []

    
    scroll_id = ""
    scroll_len = 100

    scrolling = True

    print(colors.bcolors.OKBLUE + '>>> Retrieving information from elasticsearch and building dictionary...')

    # start index for progress bar
    count = 0
    error_count = 0

    # Build a dictionary for beacon detection
    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)

        for entry in hits:
            count += 1
            
            try:
                src = entry['fields'][SOURCE_IP][0]
                dst = entry['fields'][DESTINATION_IP][0]
                dpt = entry['fields'][DESTINATION_PORT][0]
                ts  = int(time.mktime((dt_parser.parse(entry['fields'][TIMESTAMP][0])).timetuple()))
            except:
                error_count += 1
                continue

            # create dictionary key 
            key =  (src, dst, dpt)

            TIME_DICT[key].append(ts)

        # Report progress
        progress_bar(count,scroll_size)

        # stop scrolling if no more hits
        if count == scroll_size:
            scrolling = False

    if not (len(TIME_DICT) == 0):
        # parallelize it
        m = Manager()
        db_queue = m.Queue()
        n_cores = multiprocessing.cpu_count()
        print('>>> Found ' + str(n_cores) + ' core(s)!')
        
        # create parameter list for threads and keys
        arglist = []
        for key in TIME_DICT:
            arglist.append((key, TIME_DICT[key], bucket_size, thresh, db_queue))

        # determine the total number of keys to be split up amongst threads
        TOTAL_TO_DO.value = len(arglist)

        # run shit
        print(">>> Running TBD analysis... ")
        worker_pool.map(tbd_mp, iterable=arglist, chunksize=1000)
        

        common_frequency_dict = {}
        frequency_count_dict = {}

        while not db_queue.empty():
            vals = []
            try:
                vals = db_queue.get()
                key = vals[0]
                common_frequency_dict[key] = vals[1]
                frequency_count_dict[key]  = vals[2]

            except:
                continue


        #     write_data(vals, customer, proto, result_type)


        # common_frequency_dict = {}
        # frequency_count_dict = {}


        # # for every source, destination, destination port pair get most common frequency that signal occurs at
        # # as well as the total number of different frequencies the signal happens at
        # for key in TIME_DICT:
        #     try:
        #         common_frequency, frequency_count = tbd_serial(TIME_DICT[key], bucket_size, thresh)
        #     except:
        #         continue
        #     common_frequency_dict[key] = common_frequency
        #     frequency_count_dict[key]  = frequency_count


        # Find the mean and standard deviation for each of the frequency dicts
        common_mean = np.mean(list(common_frequency_dict.values()))
        common_std = np.std(list(common_frequency_dict.values()))

        count_mean = np.mean(list(frequency_count_dict.values()))
        count_std = np.std(list(frequency_count_dict.values()))


        for key in TIME_DICT:
            if key in common_frequency_dict and key in frequency_count_dict:
                rating = ( abs(common_frequency_dict[key] - common_mean) / common_std ) + \
                         ( abs(frequency_count_dict[key]  - count_mean)  / count_std )

                if rating > thresh:
                    print (str(key) + " " + str(rating))



    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file!'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped!'+ colors.bcolors.ENDC)

    



def run(customer, proto, bucket_size, thresh, graph, save_dir, result_type, server):
    global ht_data
    ht_data = ESServer(server)

    print(colors.bcolors.OKBLUE + '[-] Checking potential beacons for customer '
          + colors.bcolors.HEADER + customer, end="")
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto, end="")
    print(colors.bcolors.OKBLUE + ' [-]' + colors.bcolors.ENDC)

    # Delete Previous Results
    ht_data.delete_results(customer, result_type)

    # Get start time
    time_start = time.time()

    TBD_analysis(customer, proto, bucket_size, thresh, graph, save_dir, result_type)

    # finish timing how long this whole business took to run
    time_end = time.time()
    time_elapsed = time_end - time_start

    print(colors.bcolors.OKGREEN + '[+] Finished checking potential beacons for '
          + colors.bcolors.HEADER + customer, end="")
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto, end="")
    print(colors.bcolors.OKGREEN + ' [+]' + colors.bcolors.ENDC)

    print(colors.bcolors.OKGREEN + '[*] Time for bucket analysis: ' + str(("%.1f") % time_elapsed) + ' seconds [*]' 
          + colors.bcolors.ENDC)

 
# run('bhis_test', '', 1, 2, False, '', 'test', 'localhost:9200')