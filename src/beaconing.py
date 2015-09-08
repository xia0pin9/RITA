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

# two lines below is something I saw in a suggestion, it takes away the 
# warning but segfaults when being run.
# import matplotlib
# matplotlib.use('Agg')

import pylab as P
from matplotlib.figure import Figure

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


import data as ht_data
import colors


TOTAL_TO_DO = Value('i', 1)
TIME_DICT = defaultdict(list)
CURR_DONE = 0
UNLIKELY_CURR = 0
CURR_DONE = Value('i', 0)
UNLIKELY_CURR = Value('i', 0)
CURR_DONE_LOCK = Lock()

MAR_NAMES_LIST = [  ('MAR_2SEC', 1/60.0, 1/2.0), 
                    ('MAR_60SEC', 0, 1/60.0) ]


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

    with CURR_DONE_LOCK:
        CURR_DONE.value += 1
        local_curr_done = CURR_DONE.value
        if (local_curr_done % 1000 == 0) or \
            (local_curr_done == TOTAL_TO_DO.value):
            total_done_percent = local_curr_done / float(TOTAL_TO_DO.value)
            total_done_percent *= 100.0
            print(colors.bcolors.OKGREEN + '[+] Performed Beaconing Analysis on ' \
                    '{0} Records ({1:.2f}%) [+]'.format(local_curr_done,
                                                    total_done_percent) + colors.bcolors.ENDC)
    vals = key.split('$$$')
    src = vals[0]
    dst = vals[1]
    dpt = vals[2]

    if len(TIME_DICT[key]) < 10:
        return None


    ts = sorted(TIME_DICT[key])
    
    if 0 < (ts[-1] - ts[0]):
        for idx in range(1, len(ts)):
            ts[idx] = ts[idx] - ts[0]

        ts[0] = 0
       
        n = scipy.zeros(ts[-1])
    
        for time_idx in ts:
            n[time_idx-1] = n[time_idx-1] + 1

        sample_sz = len(n)
        
        k = scipy.arange(sample_sz)
        freq = k/float(sample_sz)    
        freq = freq[:sample_sz//2]
        
        # Run Fast Fourier Transform on sample            
        Y = abs(np.fft.rfft(n)/sample_sz)
        Y = Y[:sample_sz//2]
            
        zero_len = min([len(Y), 10])
        
        for idx in range(zero_len):
            Y[idx] = 0
        
        mar_vals = ()

        for mar_name, min_hz, max_hz in MAR_NAMES_LIST:
            if len(Y) <= 1:
                return None
            curr_min_range = int( (len(Y) / 0.5) * min_hz + 0.5)
            curr_max_range = int( (len(Y) / 0.5) * max_hz + 0.5)
            
            tmp_Y = Y[curr_min_range:curr_max_range]

            if len(tmp_Y) <= 1:
                return None
        
            fft_avg = np.mean(tmp_Y)
            y_max = np.amax(tmp_Y)

            if fft_avg <= 0:
                return None

            max_avg_ratio = y_max / fft_avg
            mar_vals += (max_avg_ratio,)

        ret_vals = (src, dst, dpt) + mar_vals
        db_queue.put( ret_vals )

    return None

def write_data(data, customer, result_type):

    # format new entry
    entry = {}
    entry['customer'] = customer
    entry['proto']    = data[0]
    entry['src']      = data[1]
    entry['dst']      = data[2]
    entry['dstport']  = data[3]
    count = 0

    if result_type == 'beaconing':
        for i  in data[4:]:
            entry[MAR_NAMES_LIST[count][0]] = i
            count +=1
    elif result_type == 'likely_beacons' or result_type == 'unlikely_beacons':
        entry[MAR_NAMES_LIST[data[4]][0]] = data[5]
        entry['min_hz'] = MAR_NAMES_LIST[data[4]][1]
        entry['max_hz'] = MAR_NAMES_LIST[data[4]][2]
    
    entry['@timestamp'] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, result_type)

def analyze_fft_data(customer, proto, result_type):
    # print "IM IN THIS FUNCTION Yaaayyy"

    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE + '[-] Analyzing FFT Data for customer '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' with protocol '
          + colors.bcolors.HEADER + proto  
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)

    # Analysis will be done on results files, not logs
    doc_type = 'results'

    # restrict results to specified customer
    constraints = [{'customer':customer},{'proto':proto},{'result_type':result_type} ]
    
    # anything we want to filter out
    ignore = []

    print('>>> Retrieving information from elasticsearch...'+ colors.bcolors.ENDC)
    

    # Keep track of mar name index
    mar_index = 0

    # Find potential and unlikely beacons
    for mar_name, min_hz, max_hz in MAR_NAMES_LIST:

         # fields to return from elasticsearch query
        fields = ['src', 'dst', 'dstport', 'proto', '@timestamp', mar_name]


        scroll_id = ""
        scroll_len = 1000

        scrolling = True

        # Make a list to fold all results
        results = []

        max_val = 0.0

        while scrolling:

            # Retrieve data
            hits, scroll_id = ht_data.get_data(doc_type, fields, constraints, ignore, scroll_id, scroll_len)
            
            # Find maximum value in current max average ratio (MAR) category
            for i in hits:
                temp = []
                temp.append(i['fields']['proto'])
                temp.append(i['fields']['src'])
                temp.append(i['fields']['dst'])
                temp.append(i['fields']['dstport'])                
                try:
                    # verify that result has the current max averatio category
                    temp.append(mar_index)
                    float_mar = float(i['fields'][mar_name][0])
                    temp.append(float_mar)
                    if float_mar > max_val:
                        max_val = float_mar
                except:
                    # print "ERROR, MOTHERFUCKER"
                    continue
                # result will only be appended if it has the current MAR category
                results.append(temp)

            if len(hits) < 1:
              scrolling = False

        mar_index += 1

        # Calculate threshhold for likely beacons
        thresh = max_val * 0.40
        thresh_unlikely = max_val * 0.01
        
        if mar_index == (len(MAR_NAMES_LIST) - 1):
            print('>>> Writing results of analysis...')

        # Scroll through results and label beacons as likely or unlikely
        for res in results:
            if thresh <= res[5]:
                # print "MAYBE SOMETHING BAD 1 IS HAPPENING IDK"
                write_data(res, customer, 'likely_beacons')

            elif res[5] <= thresh_unlikely:
                # print "MAYBE SOMETHING BAD 2 IS HAPPENING IDK"
                write_data(res, customer, 'unlikely_beacons')
            else:
                # print "MAYBE SOMETHING BAD 3 IS HAPPENING IDK"
                write_data(res, customer, 'some_other_thing')

    print(colors.bcolors.OKGREEN + '[+] Completed FFT data analysis'
          +  ' [+]'
          + colors.bcolors.ENDC)

def get_datetimes(src, dst, dpt, customer, proto):
    # searching for beacons in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = ['@timestamp']
    
    # restrict results
    constraints = [{'customer':customer}, {'proto':proto}, 
                   {'src':src}, {'dst':dst}, {'dstport':dpt}]
    
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
      hits, scroll_id = ht_data.get_data(doc_type,fields, constraints, ignore, scroll_id, scroll_len)

      for entry in hits:
        dt = dt_parser.parse(entry['fields']['@timestamp'][0])
        ts = time.mktime(dt.timetuple())
        times.append(ts)

      if len(hits) < 1:
          scrolling = False

    return sorted(times)

def find_beacons_graph(customer, proto, result_type_target, result_type_category):
#    loggingDEBUG("Entering find_beacons_graph")

    analyze_fft_data(customer, proto, result_type_target)

    print(colors.bcolors.OKBLUE + '[-] Graphing potential beacons customer '
         + colors.bcolors.HEADER + customer
         + colors.bcolors.OKBLUE + ' with beaconing logs under result name '
         + colors.bcolors.HEADER + result_type_target
         + colors.bcolors.OKBLUE + ' of type '
         + colors.bcolors.HEADER + result_type_category
         + colors.bcolors.OKBLUE + ' with protocol '
         + colors.bcolors.HEADER + proto  
         + colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)

    # Make directory to store graphs
    save_dir = './data/' + str(result_type_category) + '/'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Create string to indentify type in image title
    save_string = str(result_type_category)

    # searching for beacons in log files, not results
    doc_type = 'results'

    # fields to return from elasticsearch query
    fields = ['src', 'dst', 'dstport', 'min_hz', 'max_hz', '@timestamp']
    
    # restrict results to specified customer
    constraints = [{'customer':customer}, {'proto':proto}, {'result_type':result_type_category}]
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    print('>>> Retrieving information from elasticsearch...')

    # start index for results
    count = 0

    # get number of total results available (scroll size)
    temp, scroll_size = ht_data.get_scroll_id_and_size( doc_type, fields, constraints, ignore, scroll_len )

    # Build a dictionary for beacon detection
    while scrolling:
      # Retrieve data
      hits, scroll_id = ht_data.get_data(doc_type,fields, constraints, ignore, scroll_id, scroll_len)
      
      for entry in hits:
        # Report progress
        if count % 10 == 0 or count == scroll_size:
            processed_percent = float(count) / scroll_size * 100.0
            print('>>> Generating' \
                    'Graphs... ({1:.2f}%)'.format(count,processed_percent))
        count += 1

        src = entry['fields']['src'][0]
        dst = entry['fields']['dst'][0]
        dpt = entry['fields']['dstport'][0]
        min_hz = entry['fields']['min_hz'][0]
        max_hz = entry['fields']['max_hz'][0]


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
            sub_fig.set_title(save_string + ' (histogram)--Customer: '
                              + customer+ '\nSrc: ' + src + ' Dest: ' + dst
                              + ' Proto: ' + proto + ' DstPort: ' + dpt)
            sub_fig.set_xlabel('Time Stamp (UNIT)')
            sub_fig.set_ylabel('Connection Attempts')
            P.gca().set_ylim(ymax=10)
            
            
            canvas.print_figure(save_dir + 'Src-'
                                + src.replace('.', '_') + '_Dst-'
                                + dst.replace('.', '_') + '_' + proto
                                + '_' + dpt + '_' + customer + '_histb.png')
            P.close(fig)

            sub_fig.clear()

            fig = Figure()
            canvas = FigureCanvas(fig)
            sub_fig = fig.add_subplot(111)
            sub_fig.plot(freq, abs(Y), '--')
            sub_fig.set_title(save_string +' (FFT)--Customer: ' + customer
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

    print(colors.bcolors.OKGREEN + '[+] Finished generating graphs '
         + '[+]' + colors.bcolors.ENDC)


def run(customer, proto, result_type = 'beaconing'):

    global TOTAL_TO_DO
    global CURR_DONE
    global TIME_DICT
    CURR_DONE.value = 0
    worker_pool = Pool(processes=None, maxtasksperchild=1)

    print(colors.bcolors.OKBLUE + '[-] Checking potential beacons for customer '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' with protocol '
          + colors.bcolors.HEADER + proto  
          + colors.bcolors.OKBLUE + ' [-]')


    # searching for beacons in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = ['src', 'dst', 'dstport', 'proto', '@timestamp']
    
    # restrict results to specified customer
    constraints = [{'customer':customer}, {'proto':proto}]
    
    # anything we want to filter out
    ignore = []

    # Get start time
    time_start = time.time()

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    print('>>> Retrieving information from elasticsearch...')
    print('>>> Building dictionary...')

    # Build a dictionary for beacon detection
    while scrolling:
      # Retrieve data
      hits, scroll_id = ht_data.get_data(doc_type,fields, constraints, ignore, scroll_id, scroll_len)

      for entry in hits:
        
        key =  entry['fields']['src'][0].encode('ascii', 'ignore') + '$$$' + \
               entry['fields']['dst'][0].encode('ascii', 'ignore') + '$$$' + \
               entry['fields']['dstport'][0].encode('ascii', 'ignore')

        #############################
        # TODO: look into utc stuff....#
        ############################

        dt = dt_parser.parse(entry['fields']['@timestamp'][0])
        ts = time.mktime(dt.timetuple())
        TIME_DICT[key].append(int(ts))


      if len(hits) < 1:
          scrolling = False

   
    arglist = []

    m = Manager()
    db_queue = m.Queue()
    n_cores = multiprocessing.cpu_count()
    print('>>> Found ' + str(n_cores) + ' core(s)!' + colors.bcolors.ENDC)

    for key in TIME_DICT:
        arglist.append((key, db_queue))

    # TOTAL_TO_DO.value = len(arglist)
    # worker_pool.map(perform_fft_mp, iterable=arglist, chunksize=1000)
    for i in arglist:
        perform_fft_mp(i)


    # Write results to elasticsearch    
    while not db_queue.empty():
        vals = []

        try:
            vals = db_queue.get()
            n_vals = len(list(vals))
            vals = (proto,) + vals
        except:
            break


        write_data(vals, customer, result_type)


    time_end = time.time()
    time_elapsed = time_end - time_start

    # print(colors.bcolors.OKGREEN + '[+] Finished finding potential beacons for customer '
    #       + colors.bcolors.HEADER + customer 
    #       + colors.bcolors.OKGREEN + ' with protocol '
    #       + colors.bcolors.HEADER + proto  
    #       + colors.bcolors.OKGREEN + ' [+]')

    print(colors.bcolors.OKGREEN + '[*] Time for FFT analysis: ' + str(time_elapsed) + ' [*]' + colors.bcolors.ENDC)

    # find_beacons_graph(customer, proto, result_type)



################################################
############### TESTING ########################
###############################################

customer = 'test2'
proto = 'http'
result_type_target = 'beaconing'
result_type_category = 'likely_beacons'

run(customer,proto)
find_beacons_graph(customer, proto, result_type_target, result_type_category)
