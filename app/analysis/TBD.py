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


def write_data(key, data, customer, proto, result_type):
    # format new entry
    entry = {}

    if proto != "":
    	entry[PROTOCOL]     = proto

    entry[SOURCE_IP]        = key[0]
    entry[DESTINATION_IP]   = key[1]
    entry[DESTINATION_PORT] = key[2]
    
    for i in data:
        entry[i[0]] = i[1]

    entry[TIMESTAMP]        = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type, refresh_index = True)

def tbd_graph(customer, buckets, proto, src, dst, dpt):
    # Make directory to store graphs
    save_dir = './data/' + customer + "/buckets/"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Create string to indentify type in image title
    save_string = 'src-' + src.replace('.','_') + '_dst-' + dst.replace('.','_') + '_dpt-' + str(dpt) + '_proto-' + proto 

    tbuckets = []
    for i in range(0, max(buckets.keys())+5):
        if i in buckets.keys():
            tbuckets.append(buckets[i])
        else:
            tbuckets.append(0)

    fig = Figure()
    sub_fig = fig.add_subplot(111)
    canvas = FigureCanvas(fig)
    sub_fig.plot(tbuckets, linewidth=2.0)    
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

    spread = times[-1]-times[0]

    # Create a new dictionary to hold time buckets
    buckets = {}

    time_buckets = {}

    dt_list = []

    # Iterate over all the timestamps
    for i in range(0, len(times)-1):

        # Determine the number of seconds between two consecutive timestamps
        freq = times[i+1] - times[i]

        bucket = int(times[i] / 5000)

        if bucket not in time_buckets.keys():
            time_buckets[bucket] = 1
        else:
            time_buckets[bucket] += 1


        # dt_list.append(freq)

        # Count the number of times specific time differences occur
        if freq not in buckets.keys():
            buckets[freq] = 1
        else:
            buckets[freq] += 1

    s = sum(buckets.values())
    

    # vals = sorted(buckets.values())
    keys = sorted(buckets.keys())
    l = len(keys)

    if s > 30:
        best = 10000000
        av = [0]
        if (len(keys) is 1):
            best = 1
            av = [keys[0]]
        for i in range(l-1):
            m_sum = buckets[keys[i]]
            r = 1
            if (float(m_sum)/s > 0.85) and r < best:
                best = r
                av = [keys[i]]
            for j in range(i+1,l):
                m_sum += buckets[keys[j]]
                r = keys[j]-keys[i]
                if (float(m_sum)/s > 0.85) and r < best:
                    best = r
                    av = [keys[i],keys[j]]
                
                

        ret_vals = (key, best, len(times), av, len(time_buckets.keys()), spread)
        db_queue.put( ret_vals )
        # tbd_graph('test', buckets, 'none', key[0], key[1], key[2])

    # Experimental...
    # try:
    # 	del(buckets[0])
    # except:
    # 	a = 1

    # if len(buckets.keys()) > 0:
    #     bucket_max = np.max(list(buckets.values()))
    #     bucket_len = len(buckets)
    #     # bucket_mean = np.mean(list(buckets.values()))
    #     s = float(sum(buckets.values()))
    #     mean = s / max(buckets.values())
    #     mar = bucket_max / mean

    # if mar > 0.9 and len(times) > 20:
    

    
    # if len(dt_list) > 1:
        # h = np.histogram(dt_list, density = True)
        # print h
        # ret_vals = (key, mar)
        # db_queue.put( ret_vals )
    # ret_vals = (key, bucket_max, bucket_len, mar)
    

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
                dtime = dt_parser.parse(entry['fields'][TIMESTAMP][0])
                ts  = int(time.mktime(dtime.timetuple())*1e3 + dtime.microsecond/1e3)
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
        # worker_pool.map(tbd_mp, iterable=arglist, chunksize=1000)
        for i in arglist:
            tbd_mp(i)
        

        common_frequency_dict = {}
        frequency_count_dict = {}
        mar_dict = {}
        var_dict = {}
        size_dict = {}
        av_dict = {}
        fill_dict = {}
        spread_dict = {}

        while not db_queue.empty():
            vals = []
            try:
                vals = db_queue.get()
                key = vals[0]
                var_dict[key] = vals[1]
                size_dict[key] = vals[2]
                av_dict[key] = vals[3]
                fill_dict[key] = vals[4]
                spread_dict[key] = vals[5]
                # common_frequency_dict[key] = vals[1]
                # frequency_count_dict[key]  = vals[2]
                # mar_dict[key] = vals[3]

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

        # print common_frequency_dict


        # Find the mean and standard deviation for each of the frequency dicts
        # common_mean = np.mean(list(common_frequency_dict.values()))
        # common_std = np.std(list(common_frequency_dict.values()))

        # count_mean = np.mean(list(frequency_count_dict.values()))
        # count_std = np.std(list(frequency_count_dict.values()))

        # mar_mean = np.mean(list(mar_dict.values()))
        # mar_std = np.std(list(mar_dict.values()))

        var_mean = np.mean(list(var_dict.values()))
        var_std = np.std(list(var_dict.values()))

        size_mean = np.mean(list(size_dict.values()))
        size_std = np.std(list(size_dict.values()))

        averages = {}
        for i in av_dict.keys():
            averages[i] = np.mean(av_dict[i])

        av_mean = np.mean(list(averages.values()))
        av_std = np.std(list(averages.values()))

        fill_mean = np.mean(list(fill_dict.values()))
        fill_std = np.std(list(fill_dict.values()))

        spread_mean = np.mean(list(spread_dict.values()))
        spread_std = np.std(list(spread_dict.values()))

        var_max = max(list(var_dict.values()))
        size_max = max(list(size_dict.values()))

        data = []
        

        for key in TIME_DICT:
            do_write = False
            # if key in common_frequency_dict and key in frequency_count_dict:
                # rating = ( abs(common_frequency_dict[key] - common_mean) / common_std ) + \
                #          ( abs(frequency_count_dict[key]  - count_mean)  / count_std )
            # if key in common_frequency_dict:
            #     val = (abs(common_frequency_dict[key] - common_mean) / common_std)
            #     data.append(("max_std", val))
            #     if val > thresh:
            #         do_write = True

            # if key in frequency_count_dict:
            #     val = (abs(frequency_count_dict[key] - count_mean) / count_std)
            #     data.append(("count_std", val ))
            #     if val > thresh:
            #         do_write = True

            # if key in mar_dict:
            #     val = (abs(mar_dict[key] - mar_mean) / mar_std)
            #     data.append(("mar_std", val))
            #     if val > thresh:
            #         do_write = True
            if key in var_dict and key in size_dict and key in av_dict and key in fill_dict:
                r = var_dict[key]
                data.append(("range", r))
                s = size_dict[key]
                data.append(("size", s))
                av = str(av_dict[key][0])
                if len(av_dict[key]) > 1:
                    av = str(av_dict[key][0]) + '--' + str(av_dict[key][1])
                data.append(('range_vals',av))
                f = fill_dict[key]
                data.append(('fill',f))
                spread = spread_dict[key]
                data.append(('spread',spread))
                # rank = -1 * (var_dict[key] - var_mean) / var_std
                # rank += (size_dict[key] - size_mean) / size_std
                # rank += (np.mean(av_dict[key]) - av_mean) / av_std
                # rank += ((fill_dict[key] - fill_mean) / fill_std)/10
                # rank += (abs(spread_dict[key] - spread_mean) / spread_std)
                # rank *= 1000
                # rank = int(rank)
                data.append(('rank',rank))
                # r = var_max - r
                # rank = (10000*r)+float(s/size_max)*100
                # rank = int(rank)
                # r_thresh = 500 
                # s_thresh = 10000
                # r = float(r_thresh-r) / r_thresh
                # r *= 20000
                # s = float(s) / s_thresh
                # s *= 10000
                # rank = int(r+s)
                # data.append(("rank",rank))
            	write_data(key, data, customer, proto, result_type)



    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file!'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped!'+ colors.bcolors.ENDC)

    



def run(customer, proto, bucket_size, thresh, graph, save_dir, result_type, server):
    global ht_data
    ht_data = ESServer(server)

    print(colors.bcolors.OKBLUE + '[-] Checking potential beacons for customer '
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto),
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
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto),
    print(colors.bcolors.OKGREEN + ' [+]' + colors.bcolors.ENDC)

    print(colors.bcolors.OKGREEN + '[*] Time for bucket analysis: ' + str(("%.1f") % time_elapsed) + ' seconds [*]' 
          + colors.bcolors.ENDC)

run('test_customer','',1,1.0,True,'/home/joe/Documents/TBD/','test_tbd','localhost:9200')