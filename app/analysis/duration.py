import data as ht_data
import colors

from module import Module
# def test(elem):
#     return elem["duration"]


# def find_long_durations(data, rate):
#     # Sort the list according to duration
#     sorted_list = sorted(data, key=lambda k : k['fields']['duration'], reverse = True)

#     # Find number of elements to keep (according the rate)
#     end = int(len(sorted_list)*rate)
    
#     # Return top slice of list
#     return sorted_list[0:end]

NAME = 'duration'
DESC = 'Look for Connections with Unusually Long Duration'
OPTS = {
        "customer": "",
        "result_type": 'duration'
        }

class DurationModule(Module):
    def __init__(self):
        super(DurationModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"], self.options["result_type"])



def write_data(data, customer, result_type):

    # Iterate over each item 
    for item in data:

        # format new entry
        entry = {}
        entry['customer'] = customer
        entry['src']      = item['fields']['src']
        entry['srcport']  = item['fields']['srcport']
        entry['dst']      = item['fields']['dst']
        entry['dstport']  = item['fields']['dstport']
        entry['duration'] = item['fields']['duration']
        entry['@timestamp'] = item['fields']['@timestamp']



        # write entry to elasticsearch
        ht_data.write_data(entry, result_type)
        

def run(customer, result_type = 'duration'):
    print(colors.bcolors.OKBLUE + '[-] Finding long connections for customer *' + customer + '* [-]')

    # searching for duration in log files, not results
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = ['src', 'srcport','dst','dstport', 'duration', '@timestamp']
    
    # restrict results to specified customer
    constraints = [{'customer':customer}]
    
    # anything we want to filter out
    ignore = []

    scroll_id = ""
    scroll_len = 1000

    scrolling = True

    # get number of total results available (scroll size)
    temp, scroll_size = ht_data.get_scroll_id_and_size( doc_type, fields, constraints, ignore, scroll_len )


    print('>>> Retrieving information from elasticsearch...')

    # YE OLDE JSON QUERY
    sort = 'duration:desc'

    results = []

    
    while scrolling:
        scroll_len = (scroll_size * THRESHOLD) - len(results)
        # Retrieve data
        hits, scroll_id = ht_data.get_data(doc_type,fields, constraints, ignore, scroll_id, scroll_len, sort)

        # # Find longest 2% of durations
        # longest = find_long_durations(hits, 0.02)

        

        if len(hits) < 1:
          break

        results.append(hits)

    # Write the results to elasticsearch
    print('>>> Writing results of analysis...' + colors.bcolors.ENDC)
    for res in results:        
        write_data(res, customer, result_type)


    print(colors.bcolors.OKGREEN + '[+] Finished checking long connections for customer *' + customer + '* [+]' + colors.bcolors.ENDC)



################################################
############### TESTING ########################
###############################################

#customer = 'test'

#run(customer)
