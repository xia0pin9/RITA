##########################################
#           EXTERNAL LIBRARIES           #    
##########################################
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import os
import time
import datetime
from collections import defaultdict
import numpy as np
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
NAME = 'scanning'
DESC = 'Find Machines Exhibiting Scanning Behavior'

# Default threshold for lowest number of ports that indicate potential scan activity
SCAN_THRESH = 60

# Default threshold for lowest number of ports that will require graphing
GRAPH_THRESH = 100

# Default save directory for generated graphs
POTENTIAL_SCAN_SAVE_DIR = '/var/RITA/potential_scan/'

# Default protocol
SCAN_PROTO = ""

OPTS = {
        "customer": {
            "value": "",
            "type": "string"
            },
        "proto": {
            "value": SCAN_PROTO,
            "type": "string"
            },
        "threshold": {
    	    "value": SCAN_THRESH,
    	    "type": "number"
	        },
        "graph": {
            "value": False,
            "type": "bool"
            },
        "graph_thresh": {
            "value": GRAPH_THRESH,
            "type": "number"
            },
        "potential_save_dir": {
            "value": POTENTIAL_SCAN_SAVE_DIR,
            "type": "string"
            },
        "result_type": {
            "value": 'scanning',
            "type": "string"
            },       
        "server": {
            "value": "http://localhost:9200",
            "type": "string"
            }
        }

class ScanModule(Module):
    def __init__(self):
        super(ScanModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"]["value"],
            self.options["proto"]["value"],
            self.options["threshold"]["value"],
            self.options["graph"]["value"],
            self.options["graph_thresh"]["value"],
            self.options["potential_save_dir"]["value"],
            self.options["result_type"]["value"],            
            self.options["server"]["value"])
##########################################
#           END MODULE SETUP             #    
##########################################


def write_data(src, dst, ports_list, num_unique_ports, num_total_ports, proto, customer, result_type):
    # format new entry
    entry = {}

    # Check if user opted to restrict by protocol
    if proto != "":
        entry[PROTOCOL]       = proto

    entry[SOURCE_IP]          = src
    entry[DESTINATION_IP]     = dst
    entry['ports']            = ports_list       # list of unique ports in potential scan
    entry['num_unique_ports'] = num_unique_ports # number of unique ports in potential scan (no repetition)
    entry['num_total_ports']  = num_total_ports  # number of total ports in potential scan (with repetition)

    
    entry['@timestamp'] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type, True)


def scan_analysis(customer, proto, threshold, graph, graph_thresh, potential_save_dir, result_type):
    # Search will be conducted in log files
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [SOURCE_IP, DESTINATION_IP, DESTINATION_PORT]
    
    # restrict results to specified customer      
    if proto != "" and proto != 'web':
        constraints = [{PROTOCOL:proto}]
    else:
        constraints = []
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000
    scrolling = True

    count = 0
    error_count = 0

    print(colors.bcolors.OKBLUE + '>>> Retrieving information from elasticsearch and building dictionary...')

    # build dictionary for scan detection
    scan_dict = defaultdict(list)

    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type,fields, constraints, ignore, scroll_id, scroll_len)

        # Report progress
        if (count % 10 == 0) or (count == scroll_size):
            progress_bar(count, scroll_size)

        for entry in hits:
            count += 1
            try:    
                # Get source ip, destination ip, and port of current log entry
                src = entry['fields'][SOURCE_IP][0]
                dst = entry['fields'][DESTINATION_IP][0]
                dpt = entry['fields'][DESTINATION_PORT][0]

                if dpt == '':
                    error_count += 1
                    continue

            except:
                error_count += 1
                continue

            # Set up dictionary key as source and destination ip pair
            key =  (src, dst)

            # Add all destination ports
            scan_dict[key].append(dpt)

        

        if len(hits) < 1:
          scrolling = False

   
    # Get total number of keys (unique source - destination pairs)
    total_keys = len(scan_dict)

    if not total_keys == 0:
        print('>>> Running scan analysis ... ')

        key_count = 0
        unlikely_found = 0
        likely_found = 0

        # Iterate over all the keys...
        for key in scan_dict:
            key_count += 1

            if (key_count % 20 == 0) or (key_count == total_keys):
                progress_bar(key_count, total_keys)

            # Extract values from key string
            src = key[0]
            dst = key[1]

            # Get ports that match the source-destination pair
            ports = scan_dict[key]

            # Get number of unique destination ports
            num_unique_ports = len(set(ports))

            # Get total number ports
            num_total_ports = len(ports)

            # If there are more than specified amount of ports, flag as likely scan
            if num_unique_ports > threshold:
                if graph and (num_unique_ports > graph_thresh):
                    ports = [int(i) for i in scan_dict[key]]
                    graph_scans(customer, src, dst, proto, ports, threshold, potential_save_dir)
                write_data(src, dst, ports, num_unique_ports, num_total_ports, proto, customer, result_type)
                likely_found += 1
            else:
                unlikely_found += 1

        # Report number of potential scans found    
        print(colors.bcolors.FAIL + '[!] Found ' + str(likely_found) + ' potential port scans [!]'
              + colors.bcolors.ENDC)
    else:
        print (colors.bcolors.WARNING + '[!] Querying elasticsearch failed - Verify your protocol choice or log configuration file! [!]'+ colors.bcolors.ENDC)

    if error_count > 0:
        print (colors.bcolors.WARNING + '[!] ' + str(error_count) + ' log entries with misnamed or missing field values skipped! [!]'+ colors.bcolors.ENDC)


def graph_scans(customer, src, dst, proto, ports, threshold, potential_save_dir):
    # Create directory for potential scan graphs if it doesn't exist already
    if not os.path.exists(potential_save_dir):
        os.makedirs(potential_save_dir)

    if proto != "":
        proto_temp = proto
    else:
        proto_temp = "none specified"

    # Create histogram, with port numbers as the "bins" and connection
    # attempts per port as the "counts" in the bins
    n, bins, patches = plt.hist(ports, bins=51000, histtype='step',
                              normed=False, color='lightseagreen')

    plt.gca().set_ylim(ymax=5)
    plt.title('Potential Scan for [Customer: ' + customer + ']\n[src: ' + str(src) + 
        '] [dst: ' + dst + '] [Proto: ' + proto_temp + '] [Threshold: ' + str(threshold) + "]")
    plt.xlabel('Port Numbers')
    plt.ylabel('Connection Attempts')
    plt.savefig(potential_save_dir + 'src_' + src.replace('.','_') + '__' + 'dst_' + dst.replace('.','_') + '.png')
    # plt.show()  # uncomment if you want graphs to pop up
    plt.close()


    # Alternative scatter plot heat map thingie.
    # d = {}

    # for i in ports:
    #     if i in d.keys():
    #         d[i] += 1
    #     else:
    #         d[i] = 1

    # x = d.keys()
    # y = d.values()

    # xy = np.vstack([x,y])
    # z = gaussian_kde(xy)(xy)

    # fig, ax = plt.subplots()
    # ax.scatter(x,y,c=z,s=5,edgecolor='')
    # plt.show()
    


def run(customer, proto, threshold, graph, graph_thresh, potential_save_dir, result_type, server):
    global ht_data
    ht_data = ESServer(server)
    print(colors.bcolors.OKBLUE + '[-] Checking potential port scans for '
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto ),
    print(colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)

    # Get start time
    time_start = time.time()

    # Delete Previous Results
    ht_data.delete_results(customer, result_type)

    scan_analysis(customer, proto, threshold, graph, graph_thresh, potential_save_dir, result_type)

    time_end = time.time()
    time_elapsed = time_end - time_start

    print(colors.bcolors.OKGREEN + '[+] Finished checking potential port scans for '
          + colors.bcolors.HEADER + customer),
    if proto != "":
        print(colors.bcolors.OKBLUE + ' with protocol '
              + colors.bcolors.HEADER + proto ),
    print(colors.bcolors.OKBLUE + '[-]' + colors.bcolors.ENDC)

    print(colors.bcolors.OKGREEN + '[+] Time for scan analysis: ' + str(time_elapsed) + ' [+]' + colors.bcolors.ENDC)
