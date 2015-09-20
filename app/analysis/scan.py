import data as ht_data
import colors
import os
import time
from collections import defaultdict
import pylab as P
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from field_names import *
from yay_its_a_loading_bar import progress_bar
import datetime
from module import Module

# Threshold for lowest number of ports that indicate potential scan activity
SCAN_THRESH = 50

# Save directories yaaayyy
unlikely_save_dir = './data/unlikely_scan/'
potential_save_dir = './data/potential_scan/'


NAME = 'scan'
DESC = 'Find Machines Exhibiting Scanning Behavior'

OPTS = {
        "threshold": {
	    "type": "number",
	    "value": 50
	    },
        "unlikely_save_dir": {
            "type": "string",
            "value": '/var/ht/unlikely_scan/'
            },
        "potential_save_dir": {
            "value": '/var/ht/potential_scan/',
            "type": "string"
            },
        "customer": {
            "value": "",
            "type": "string"
            },
        "proto": {
            "value":"",
            "type": "string"
            }
        }

class ScanModule(Module):
    def __init__(self):
        super(ScanModule, self).__init__(NAME, DESC, OPTS)

    def RunModule():
        run(self.options["customer"], self.options["proto"])

# Threshold for lowest number of ports that indicate potential scan activity
SCAN_THRESH = 0

# Save directories yaaayyy
unlikely_save_dir = './data/unlikely_scan/'
potential_save_dir = './data/potential_scan/'


def write_data(src, dst, proto, customer, result_type):

    # format new entry
    entry = {}
    entry[CUSTOMER_NAME]   = customer
    entry[PROTOCOL]        = proto
    entry[SOURCE_IP]       = src
    entry[DESTINATION_IP]  = dst
    
    entry['@timestamp'] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type)


def run(customer, proto, result_type = 'scanning'):
    global SCAN_THRESH, unlikely_save_dir

    print(colors.bcolors.OKBLUE + '[-] Checking potential port scans for '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' with protocol '
          + colors.bcolors.HEADER + proto  
          + colors.bcolors.OKBLUE + ' [-]')


    # Create directory for unlikely scans if it doesn't exist already
    if not os.path.exists(unlikely_save_dir):
        os.makedirs(unlikely_save_dir)


    # Search will be conducted in log files
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT]
    
    # restrict results to specified customer      
    if proto != None and proto != 'web':
        constraints = [{PROTOCOL:proto}]
    else:
        constraints = []
    
    # anything we want to filter out
    ignore = []

    # Get start time
    time_start = time.time()

    scroll_id = ""
    scroll_len = 1000
    scrolling = True

    count = 0
    error_count = 0

    print('>>> Retrieving information from elasticsearch and building dictionary...')

    # build dictionary for scan detection
    scan_dict = defaultdict(list)

    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)

        progress_bar(count, scroll_size)

        for entry in hits:
            count += 1
            try:    
                    # Get source ip, destination ip, and port of current log entry
                    src = entry['fields'][SOURCE_IP][0]
                    dst = entry['fields'][DESTINATION_IP][0]
                    dpt = entry['fields'][DESTINATION_PORT][0]

            except:
                error_count += 1
                continue

            # Set up dictionary key as source and destination ip pair
            key =  (src, dst)

            # If user name has not been added to dictionary, add set login counts to 0
            # if key not in scan_dict:
            #     scan_dict[key] = []

            # Add unique destination ports
            if dpt not in scan_dict[key]:
                scan_dict[key].append(dpt)

        if len(hits) < 1:
          scrolling = False

   
    # Get total number of keys (unique source - destination pairs)
    total_keys = len(scan_dict)
    
    if not total_keys == 0:
        print('>>> Running scan analysis ... ')

        key_count = 0
        unlikely_found = 0

        # Iterate over all the keys...
        for key in scan_dict:
            if (key_count % 10 == 0) or (key_count == total_keys):
                progress_bar(key_count, total_keys)

            key_count += 1

            # Extract values from key string
            src = key[0]
            dst = key[1]

            # Get ports that match the source-destination pair
            ports = scan_dict[key]

            # If there are more than specified amount of ports, flag as likely scan
            if SCAN_THRESH < len(ports):
                write_data(src, dst, proto, customer, result_type)
            else:
                unlikely_found = unlikely_found + 1

                # if unlikely_found % 1000 == 0:
                #     # Create histogram, with port numbers as the "bins" and
                #     # connection attempts per port as the "counts" in the bins
                #     n, bins, patches = P.hist(ports, bins=65535, histtype='step',
                #                               normed=False)
                #     P.title('Unlikely Scan (Histogram)--Customer: ' + customer + '\nSrc: '
                #             + src + ' Dst: ' + dst + ' Proto: ' + proto)
                #     P.xlabel('Port Numbers')
                #     P.ylabel('Connection Attempts')
                #     P.savefig(unlikely_save_dir + 'Src-' + src.replace('.', '_')
                #               + '_Dst-' + dst.replace('.', '_') + '_' + proto + '_'
                #               + customer + '_hist.png')
                #     P.close()
    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your log configuration file! [!]'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped! [!]'+ colors.bcolors.ENDC)


    time_end = time.time()
    time_elapsed = time_end - time_start

    print(colors.bcolors.OKGREEN + '[+] Finished checking potential port scans for '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKGREEN + ' with protocol '
          + colors.bcolors.HEADER + proto  
          + colors.bcolors.OKGREEN + ' [+]')

    print(colors.bcolors.OKGREEN + '[+] Time for scan analysis: ' + str(time_elapsed) + ' [+]' + colors.bcolors.ENDC)


def graph_scans(customer, proto):

    global SCAN_THRESH, potential_save_dir

    print(colors.bcolors.OKBLUE + '[-] Graphing potential port scans for'
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' with protocol '
          + colors.bcolors.HEADER + proto  
          + colors.bcolors.OKBLUE + ' [-]')

    # Create directory for potential scan graphs if it doesn't exist already
    if not os.path.exists(potential_save_dir):
        os.makedirs(potential_save_dir)


     # searching for beacons in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT]
    
    # restrict results to specified customer        
    if proto != None and proto != 'web':
        constraints = [{PROTOCOL:proto}]
    else:
        constraints = []
    
    # anything we want to filter out
    ignore = []

    # Get start time
    time_start = time.time()

    # DO THE USUAL SCANNING TO RETRIEVE ELASTICSEARCH RESULTS
    # ADD {RESULT TYPE = POTENTIAL_SCANS} TO CONSTRAINTS
    # THESE RESULTS ARE SRC/DST CONNECTIONS THAT ACCESSED A LOT OF PORTS (POTENTIAL PORT SCANS) 
    # PUT RESULTS IN THIS FORMAT:
    # res[0] <- source ip
    # res[1] <- destination ip
    # res[2] <- destination port

    # AFTER GETTING RESULTS:
    # (loop over results (R)): 
        # DO ANOTHER ELASTICSEARCH QUERY
        # fields = destination_port
        # constraints = customer and proto from parameters...
        #               src and dst IP's from (R)
        # THIS WILL RETURN ALL THE PORTS FOR THE GIVEN SRC/DST IP'S
        # STORE THEM IN THE ports VARIABLE AND CREATE A HISTOGRAM WITH THE 
        # CODE ON THE BOTTOM OF THIS FUNCTION
        # THIS HISTOGRAM WILL SHOW THE PORTS THAT WERE ACCESSED ON THIS UNIQUE SRC/DST CONNECTION




    res_curr = 0
    res_total = len(results)
    for res in results:
        res_curr = res_curr + 1
        if res_curr % 10 == 0:
            print('Total Scan Graphs Done: ' + \
                    str(float(res_curr) / res_total * 100.0) + '%')

        src = res[0]
        dst = res[1]

        q1 = 'SELECT ' + DPT_DB + ' FROM ' + table + ' WHERE ' + SRC_DB
        q1 += ' = \'' + src + '\' AND ' + DST_DB + ' = \'' + dst + '\''
        
        if proto != None and proto != 'web':
            q1 += ' AND PROTO = \'' + proto + '\''

        curs.execute(q1)

        try:
            ports = [int(a[0]) for a in curs.fetchall()]
        except:
            continue

        # Create histogram, with port numbers as the "bins" and connection
        # attempts per port as the "counts" in the bins
        n, bins, patches = P.hist(ports, bins=65535, histtype='step',
                                  normed=False)
        P.gca().set_ylim(ymax=10)
        P.title('Potential Scan (Histogram)--Table: ' + table + '\nSrc: '
                + src + ' Dst: ' + dst + ' Proto: ' + proto)
        P.xlabel('Port Numbers')
        P.ylabel('Connection Attempts')
        P.savefig(potential_save_dir + 'Src-' + src.replace('.', '_')
                  + '_Dst-' + dst.replace('.', '_') + '_' + proto + '_'
                  + table + '_hist.png')
        P.close()

    conn.close()

    print('++Finished graphing potential port scans for: ' + table
          + ' with Protocol: ' + proto + '++')


################################################
############### TESTING ########################
###############################################

#customer = 'ht'
#proto = 'udp'
# result_type_target = 'beaconing'
# result_type_category = 'likely_beacons'

#run(customer,proto)
