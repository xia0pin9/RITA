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

import time
import datetime
import dateutil.parser as dt_parser
import scipy
import scipy.fftpack
import numpy as np
from multiprocessing import Process, Pool, Value, Lock, Queue, Manager
import multiprocessing
from collections import defaultdict
import os
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
NAME = "beaconing"
DESC = "Analyze Logs for Beaconing Behavior"

##### Global variables for multiprocessing stuff #######
TOTAL_TO_DO = Value('i', 1)
TIME_DICT = defaultdict(list)
CURR_DONE = 0
UNLIKELY_CURR = 0
CURR_DONE = Value('i', 0)
UNLIKELY_CURR = Value('i', 0)
CURR_DONE_LOCK = Lock()

MAR_NAMES_LIST = [  ('MAR_2SEC', 1/60.0, 1/2.0), # frequencies once between 2 sec and once between 60 sec
                    ('MAR_60SEC', 0, 1/60.0) ]

# Default threshold for max average ratio
MAR_THRESH_LIKELY = 40
MAR_THRESH_UNLIKELY = 20

BEACON_PROTO = ""

POTENTIAL_SAVE_DIR = '/var/ht/potential_beacon/'
UNLIKELY_SAVE_DIR = '/var/ht/unlikely_beacon/'

OPTS = {
        "customer": {
            "type": "string",
            "value": ""
            },
        "proto": {
            "type": "string",
            "value": BEACON_PROTO
            },
        "graph_likely": {
            "type": "bool",
            "value": False
            },
        "graph_unlikely": {
            "type": "bool",
            "value": False
            },
        "threshold_likely": {
            "type": "number",
            "value": MAR_THRESH_LIKELY
            },
        "threshold_unlikely": {
            "type": "number",
            "value": MAR_THRESH_UNLIKELY
            },
        "potential_save_dir": {
            "value": POTENTIAL_SAVE_DIR,
            "type": "string"
            },
        "unlikely_save_dir": {
            "value": UNLIKELY_SAVE_DIR,
            "type": "string"
            },
        "result_type": {
            "type": "string",
            "value": "beaconing"
            },
        "server": {
            "type": "string",
            "value": "http://localhost:9200/"
            }
        }

class BeaconingModule(Module):
    def __init__(self):
        super(BeaconingModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"], 
            self.options["proto"]["value"],
            self.options["threshold_likely"]["value"],
            self.options["threshold_unlikely"]["value"],
            self.options["graph_likely"]["value"],
            self.options["graph_unlikely"]["value"],
            self.options["potential_save_dir"]["value"],
            self.options["unlikely_save_dir"]["value"],
            self.options["result_type"]["value"],
            self.options["server"]["value"])
        return
##########################################
#           END MODULE SETUP             #    
##########################################


def perform_fft_mp(arglist):
    """
    Use fourier transform to look for beacons in a dataset specified in arg list
    make a table and mark those beacons in the database.
    """
    global CURR_DONE
    global UNLIKELY_CURR
    global TOTAL_TO_DO
    global TIME_DICT
    global CURR_DONE_LOCK

    key, db_queue = arglist

    # Mutex lock to update number of items completed so far
    with CURR_DONE_LOCK:
        CURR_DONE.value += 1
        local_curr_done = CURR_DONE.value

        # Draw a progress bar
        if (local_curr_done % 1000 == 0) or (local_curr_done == TOTAL_TO_DO.value):
            progress_bar(local_curr_done, TOTAL_TO_DO.value)
    

    src = key[0]  # Source IP
    dst = key[1]  # Destination IP
    dpt = key[2]  # Destination Port

    # Return if the sample size is too small
    if len(TIME_DICT[key]) < 10:
        return None

    # Sort the list of timestamps for this connection
    ts = sorted(TIME_DICT[key])
    
    # Make sure the last timestep is greater than the first
    if 0 < (ts[-1] - ts[0]):

        # Change the timestamp from seconds since the epoch to seconds since timestamp_0
        for idx in range(1, len(ts)):
            ts[idx] = ts[idx] - ts[0]
        ts[0] = 0
       
        # Create an array of seconds from 0 to the greatest timestep
        n = scipy.zeros(ts[-1])
        # For each timestamp, increment the count for that particular time in 
        # the n array
        for time_idx in ts:
            n[time_idx-1] = n[time_idx-1] + 1

        sample_sz = len(n)
 
        # Create a range of numbers, 0 to the length of n       
        k = scipy.arange(sample_sz)

        # Create a list of frequencies by dividing each element in k
        # by the length of k... ie k=1 -> freq=1/60
        freq = k/float(sample_sz)

        # Only look at the first half of the frequency range    
        freq = freq[:sample_sz//2]
        
        # Run Fast Fourier Transform on sample
        # Only look at positive frequencies from 0 to half the sample size            
        Y = abs(np.fft.rfft(n)/sample_sz)
        Y = Y[:sample_sz//2]
            
        # Get rid of high frequencies...
        zero_len = min([len(Y), 10])
        for idx in range(zero_len):
            Y[idx] = 0
        
        mar_vals = ()

        for mar_name, min_hz, max_hz in MAR_NAMES_LIST:

            if len(Y) <= 1:
                return None

            # Determine range of frequencies to examine
            curr_min_range = int( (len(Y) / 0.5) * min_hz + 0.5)
            curr_max_range = int( (len(Y) / 0.5) * max_hz + 0.5)
            tmp_Y = Y[curr_min_range:curr_max_range]

            if len(tmp_Y) <= 1:
                return None
        
            # Determine average and max value for frequencies in
            # the desired range
            fft_avg = np.mean(tmp_Y)
            y_max = np.amax(tmp_Y)

            if fft_avg <= 0:
                return None

            # Save max/average for the frequency range
            max_avg_ratio = y_max / fft_avg
            mar_vals += (max_avg_ratio,)

        ret_vals = (src, dst, dpt) + mar_vals
        db_queue.put( ret_vals )

    return None

def write_data(data, customer, proto, result_type):

    # format new entry
    entry = {}

    if proto != "":
        entry[PROTOCOL]     = proto

    entry[SOURCE_IP]        = data[0]
    entry[DESTINATION_IP]   = data[1]
    entry[DESTINATION_PORT] = data[2]
    
    count = 0

    if result_type == 'beaconing':
        for i  in data[3:]:
            entry[MAR_NAMES_LIST[count][0]] = i
            count +=1

    elif result_type == 'likely_beacons' or result_type == 'unlikely_beacons':
        entry[MAR_NAMES_LIST[data[3]][0]] = data[4]
        entry['min_hz'] = MAR_NAMES_LIST[data[3]][1]
        entry['max_hz'] = MAR_NAMES_LIST[data[3]][2]
    
    entry[TIMESTAMP] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type, refresh_index = True)

def analyze_fft_data(customer, proto, threshold_likely, threshold_unlikely, result_type):
    # print "IM IN THIS FUNCTION Yaaayyy"

    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE + '[-] Analyzing FFT Data for customer '
          + colors.bcolors.HEADER + customer),
    if proto != "":
          print(colors.bcolors.OKBLUE + ' with protocol '
                + colors.bcolors.HEADER + proto),
    print( colors.bcolors.OKBLUE + ' [-]' + colors.bcolors.ENDC)

    # Analysis will be done on results files, not logs
    doc_type = 'results'

    # restrict results to specified customer
    if proto != "":
        constraints = [{PROTOCOL:proto}, {'result_type':result_type}]
    else:
        constraints = [{'result_type':result_type}]
    
    # anything we want to filter out
    ignore = []

    print('>>> Retrieving information from elasticsearch...'+ colors.bcolors.ENDC)
    

    # Keep track of mar name index
    mar_index = 0

    # Find potential and unlikely beacons
    for mar_name, min_hz, max_hz in MAR_NAMES_LIST:

         # fields to return from elasticsearch query
        fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT, TIMESTAMP, mar_name]


        scroll_id = ""
        scroll_len = 1000

        scrolling = True

        # Make a list to hold all results
        results = []

        max_val = 0.0

        count = 0
        error_count = 0

        while scrolling:

            # Retrieve data
            hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len)
            
            # Find maximum value in current max average ratio (MAR) category
            for i in hits:
                try:
                    src = i['fields'][SOURCE_IP]
                    dst = i['fields'][DESTINATION_IP]
                    dpt = i['fields'][DESTINATION_PORT]
                    float_mar = float(i['fields'][mar_name][0])

                except:
                    error_count += 1
                    continue

                temp = [src, dst, dpt, mar_index, float_mar]
                if float_mar > max_val:
                    max_val = float_mar

                # result will only be appended if it has the current MAR category
                results.append(temp)

            if len(hits) < 1:
                scrolling = False

        if error_count > 0:
            print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' results entries with misnamed or missing field values skipped!'+ colors.bcolors.ENDC)


        # Scroll through results and label beacons as likely or unlikely
        for res in results:
            if threshold_likely <= res[4]:
                write_data(res, customer, proto, 'likely_beacons')

            elif res[4] <= threshold_unlikely:
                write_data(res, customer, proto, 'unlikely_beacons')

        # increment mar index
        mar_index += 1

    print(colors.bcolors.OKGREEN + '[+] Completed FFT data analysis' + ' [+]'
          + colors.bcolors.ENDC)

def get_datetimes(src, dst, dpt, customer, proto):
    # searching for beacons in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [TIMESTAMP]
    
    # restrict results
    if proto != "":
        constraints = [{PROTOCOL:proto}, {SOURCE_IP:src}, {DESTINATION_IP:dst}, {DESTINATION_PORT:dpt}]
    else:
        constraints = [{SOURCE_IP:src}, {DESTINATION_IP:dst}, {DESTINATION_PORT:dpt}]

    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    # Make a list to hold the datetime values
    times= []

    # Build a dictionary for beacon detection
    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)

        for entry in hits:
            dt = dt_parser.parse(entry['fields'][TIMESTAMP][0])
            ts = time.mktime(dt.timetuple())
            times.append(ts)

        if len(hits) < 1:
            scrolling = False

    return sorted(times)

def find_beacons_graph(customer, proto, category, save_dir):

    # Make directory to store graphs
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)


    # searching for beacons in log files, not results
    doc_type = 'results'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT, 'min_hz', 'max_hz', TIMESTAMP]
    
    # restrict results to specified customer
    if proto != "":
        constraints = [{PROTOCOL:proto}, {'result_type':category}]
        proto_temp = proto
    else:
        constraints = [{'result_type':category}]
        proto_temp = "All Protocols"
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    print('>>> Retrieving information from elasticsearch...')

    # start index for results
    count = 0
    error_count = 0

    # Build a dictionary for beacon detection
    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)

        for entry in hits:

            count += 1
            progress_bar(count, scroll_size)
            
            try:
                src = entry['fields'][SOURCE_IP][0]
                dst = entry['fields'][DESTINATION_IP][0]
                dpt = entry['fields'][DESTINATION_PORT][0]
                min_hz = entry['fields']['min_hz'][0]
                max_hz = entry['fields']['max_hz'][0]
            except:
                error_count += 1
                continue


            times = get_datetimes(src, dst, dpt, customer, proto)

            if not len(times) > 10:
                return None

            span = times[-1] - times[0]
            if span > 0:
                n_times = len(times)

                for idx in range(1, n_times):
                    times[idx] = times[idx] - times[0]

                times[0] = 0
                
                n = scipy.zeros(times[-1] + 1)

                for time_idx in times:
                    n[time_idx] += 1

                fig = Figure()
                sub_fig = fig.add_subplot(111)

                span_6_hours = min([len(n), 21600])
                times_6_hours = n[:span_6_hours]            

                #n, bins, patches = sub_fig.hist(times, span, normed=0,
                #                                histtype='step',
                #                                linestyle='dashed')
                
                sample_sz = len(n)
                k = scipy.arange(sample_sz)

                freq = k/float(sample_sz)
                freq = freq[:sample_sz//2]

                Y = abs(np.fft.rfft(n)/sample_sz)

                Y = Y[:sample_sz//2]
                zero_len = min([len(Y), 10])
                for idx in range(zero_len):
                    Y[idx] = 0

                curr_min_range = int( (len(Y) / 0.5) * min_hz + 0.5)
                curr_max_range = int( (len(Y) / 0.5) * max_hz + 0.5)
                Y = Y[curr_min_range:curr_max_range]
                freq = freq[curr_min_range:curr_max_range]

                canvas = FigureCanvas(fig)
            
                #P.setp(patches, 'facecolor', 'g', 'alpha', 0.75)
                sub_fig.plot(times_6_hours)    
                sub_fig.set_title(category + ' (histogram)--Customer: '
                                  + customer+ '\nSrc: ' + src + ' Dest: ' + dst
                                  + ' Proto: ' + proto_temp + ' DstPort: ' + dpt)
                sub_fig.set_xlabel('Time Stamp (UNIT)')
                sub_fig.set_ylabel('Connection Attempts')
                P.gca().set_ylim(ymax=10)
                
                
                canvas.print_figure(save_dir + 'Src-'
                                    + src.replace('.', '_') + '_Dst-'
                                    + dst.replace('.', '_') + '_' + proto_temp
                                    + '_' + dpt + '_' + customer + '_histb.png')
                P.close(fig)

                sub_fig.clear()

                fig = Figure()
                canvas = FigureCanvas(fig)
                sub_fig = fig.add_subplot(111)
                sub_fig.plot(freq, abs(Y), '--')
                sub_fig.set_title(category +' (FFT)--Customer: ' + customer
                                  + '\nSrc: ' + src + ' Dest: ' + dst
                                  + ' Proto: ' + proto + ' DstPort: ' + dpt)
                sub_fig.set_xlabel('Freq (HZ)')
                sub_fig.set_ylabel('|Y(FREQ)|')
                canvas.print_figure(save_dir + 'Src-'
                                    + src.replace('.', '_') + '_Dst-'
                                    + dst.replace('.', '_') + '_' + proto + '_'
                                    + dpt + '_' + customer+ '_fft.png')
                P.close(fig)

        

        if len(hits) < 1:
            scrolling = False

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + 
                ' results entries with misnamed or missing field values skipped!'+ colors.bcolors.ENDC)


    print(colors.bcolors.OKGREEN + '[+] Finished generating graphs '
         + '[+]' + colors.bcolors.ENDC)


def beacon_analysis(customer, proto, result_type):

    global TOTAL_TO_DO
    global CURR_DONE
    global TIME_DICT
    CURR_DONE.value = 0
    worker_pool = Pool(processes=None, maxtasksperchild=1)


    # searching for beacons in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT, PROTOCOL, TIMESTAMP]
    
    if proto != "":
        # restrict results to specified customer
        constraints = [{PROTOCOL:proto}]
    else:
        constraints = []
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    print(colors.bcolors.OKBLUE + '>>> Retrieving information from elasticsearch and building a dictionary... ')

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
                # create dictionary key 
                key =  (entry['fields'][SOURCE_IP][0], 
                        entry['fields'][DESTINATION_IP][0],
                        entry['fields'][DESTINATION_PORT][0])

                # append timestamp to dictionary under unique key
                dt = dt_parser.parse(entry['fields'][TIMESTAMP][0])
                ts = time.mktime(dt.timetuple())
                TIME_DICT[key].append(int(ts))

            except:
                error_count += 1
                continue

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
            arglist.append((key, db_queue))

        # determine the total number of keys to be split up amongst threads
        TOTAL_TO_DO.value = len(arglist)

        # run the fft mapping
        print ">>> Running beacon analysis... "
        worker_pool.map(perform_fft_mp, iterable=arglist, chunksize=1000)
        
        # Write results to elasticsearch
        while not db_queue.empty():
            vals = []
            try:
                vals = db_queue.get()
                n_vals = len(list(vals))
            except:
                break                
            write_data(vals, customer, proto, result_type)
    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file!'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped!'+ colors.bcolors.ENDC)


    

def run(customer, proto, threshold_likely, threshold_unlikely, graph_likely, graph_unlikely, potential_save_dir, unlikely_save_dir, result_type, server):
    global ht_data
    ht_data = ESServer(server)

    print(colors.bcolors.OKBLUE + '[-] Checking potential beacons for customer '
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto ),
    print(colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)

    # Get start time
    time_start = time.time()

    beacon_analysis(customer, proto, result_type)

    analyze_fft_data(customer, proto, threshold_likely, threshold_unlikely, result_type)

    if graph_likely:
        category = 'likely_beacons'
        print(colors.bcolors.OKBLUE + '[-] Graphing potential beacons customer '
         + colors.bcolors.HEADER + customer
         + colors.bcolors.OKBLUE + ' with beaconing logs under result name '
         + colors.bcolors.HEADER + result_type
         + colors.bcolors.OKBLUE + ' of type '
         + colors.bcolors.HEADER + category),
        if proto != "":
            print(colors.bcolors.OKBLUE + ' with protocol '
                  + colors.bcolors.HEADER + proto ),
        print(colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)
        find_beacons_graph(customer, proto, category, potential_save_dir)

    if graph_unlikely:
        category = 'unlikely_beacons'
        print(colors.bcolors.OKBLUE + '[-] Graphing potential beacons customer '
         + colors.bcolors.HEADER + customer
         + colors.bcolors.OKBLUE + ' with beaconing logs under result name '
         + colors.bcolors.HEADER + result_type
         + colors.bcolors.OKBLUE + ' of type '
         + colors.bcolors.HEADER + category),
        if proto != "":
            print(colors.bcolors.OKBLUE + ' with protocol '
                  + colors.bcolors.HEADER + proto ),
        print(colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)
        find_beacons_graph(customer, proto, category, unlikely_save_dir)

    time_end = time.time()
    time_elapsed = time_end - time_start

    print(colors.bcolors.OKGREEN + '[+] Finished checking potential beacons for '
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto ),
    print(colors.bcolors.OKGREEN + '[+]' + colors.bcolors.ENDC)

    print(colors.bcolors.OKGREEN + '[+] Time for scan analysis: ' + str(time_elapsed) + ' [+]' + colors.bcolors.ENDC)
