from collections import defaultdict

CUSTOMER = ""
RESULT_TYPE = 'blacklisted'

def write_data(data, customer, result_type):

    # format new entry
    entry = {}
    entry['customer'] = customer
    entry['src']      = data[0]
    entry['dst']      = data[1]
    entry['times_seen']      = data[1]
    
    entry['@timestamp'] = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, result_type)

def filter_ip(ip_in):
    """
    Returns true if IP is not an internal address
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


def find_blacklisted_ipvoid_mp(check_list):
    global CURR_DONE
    global TOTAL_TO_DO

    global CUSTOMER
    global RESULT_TYPE

    dst_ip = check_list[0]
    src_list = check_list[1]

    with CURR_DONE_LOCK:
        if CURR_DONE.value % 100 == 0:
            print('Total done: ' + str(
                float(CURR_DONE.value) / TOTAL_TO_DO.value * 100.0) + '%')

        CURR_DONE.value += 1

    try:
        response = urllib.request.urlopen('http://www.ipvoid.com/scan/' + dst_ip)
        html = response.read().decode('utf-8')
        if 'BLACKLISTED' in html:
            print(dst_ip)
            line_splt = html.split('BLACKLISTED ')
            times_seen = int(line_splt[1].split('/')[0])
            for src_ip in src_list:
                write_data([src_ip, dst_ip, times_seen], customer, RESULT_TYPE)

        response.close()
    except:
        pass

def find_blacklisted_ipvoid(customer):
    global CUSTOMER

    CUSTOMER = customer
    # print "IM IN THIS FUNCTION Yaaayyy"

    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE + '[-] Finding blacklisted URLS for customer '
          + colors.bcolors.HEADER + CUSTOMER 
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)
    

    global CURR_DONE
    global TOTAL_TO_DO

    CURR_DONE.value = 0

    SRC_IDX = 0
    DST_IDX = 1
   
    

    # Analysis will be done on log files, not results
    doc_type = 'logs'

    # restrict results to specified customer
    constraints = [{'customer':CUSTOMER},{'proto':proto},{'result_type':result_type} ]
    
    # anything we want to filter out
    ignore = []

    print('>>> Retrieving information from elasticsearch...'+ colors.bcolors.ENDC)
    
    # fields to return from elasticsearch query
    fields = ['src', 'dst']


    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    # build dictionary for blacklist detection
    blacklist_dict = defaultdict(list)

    while scrolling:

        # Retrieve data
        hits, scroll_id = ht_data.get_data(doc_type, fields, constraints, ignore, scroll_id, scroll_len)
        
        # For every unique destination ip (used as dict key), find make a list of all
        # src ips that connect to it
        for i in hits:
            key =  entry['fields']['dst'][0]

            # Verify that source IP is internal and that destination ip is external
            if (filter_ip(src) == False) and (filter_ip(dst) == True):
                # Check for duplicate source IPs
                try:
                    if entry['fields']['src'][0] not in blacklist_dict[key]:
                        blacklist_dict[key].append(entry['fields']['src'][0])
                except:
                    continue
                
        if len(hits) < 1:
          scrolling = False

       

    print('>>> Querying blacklist....')

    TOTAL_TO_DO.value = total_keys

    workers = Pool(64)

    workers.map(find_blacklisted_ipvoid_mp, blacklist_dict.items())


    print('++Finished finding blacklisted URLS for: ' + CUSTOMER + '++')