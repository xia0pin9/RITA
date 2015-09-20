import datetime
from field_names import *
import colors
import data as ht_data

from module import Module

LOG_ON =  '4624' # logged on successfully
LOG_OFF = '4634' # logged off successfully
# 4674 : an operation was attempted on a privileged object

### Module Setup ###

NAME = "concurrent"
DESC = "Look for multiptle concurrent logins"
OPTS = {
        "customer": {
            "type": "string",
            "value": ""
            },
        "result_type": {
            "type": "string",
            "value": "concurrent"
            }
        }

class ConcurrentModule(Module):
    def __init__(self):
        super(ConcurrentModule, self).__init__(NAME, DESC, OPTS)

    def RunModule(self):
        run(self.options["customer"])

### End Module Setup ###

def write_data(user, data, customer, result_type):
    # format new entry
    entry = {}
    entry[CUSTOMER_NAME] = customer
    entry[USER_NAME]     = user
    entry[SOURCE_IP]     = data['src_list']  
    entry[TIMESTAMP]     = datetime.datetime.now()
    
    # write entry to elasticsearch
    ht_data.write_data(entry, customer, result_type)

def find_concurrent(customer, result_type):
    # Search will be conducted in log files
    doc_type = 'logs'

    # fields to return from elasticsearch query
    fields = [EVENT_ID, USER_NAME, SOURCE_IP, TIMESTAMP]
    
    # restrict results to specified customer and eventId to list of possible IDs
    constraints = []
    
    # anything we want to filter out
    ignore = []

    # Sort results by timestamp
    sort = TIMESTAMP + ':asc'

    # create dictionary to store user login info
    concurrent_dict = {}

    scroll_id = ""

    scrolling = True

    scroll_len = 1000

    print(colors.bcolors.OKBLUE +'>>> Retrieving information from elasticsearch...')
    
    while scrolling:
        # Retrieve data
        hits, scroll_id, scroll_size = ht_data.get_data(customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len, sort)
   
        # For every unique username (used as dict key), make a dictionary of event activity
        for entry in hits:
            user =  entry['fields'][USER_NAME][0]
            event = entry['fields'][EVENT_ID][0]
            src = entry['fields'][SOURCE_IP][0]
            
            # If user name has not been added to dictionary, add set login counts to 0
            if user not in concurrent_dict:
                concurrent_dict[user] = {}
                concurrent_dict[user]['logged_on'] = False
                concurrent_dict[user]['concurrent'] = 0
                concurrent_dict[user]['max_concurrent'] = 0
                concurrent_dict[user]['src_list'] = []
            
            # Add only unique source ips
            if src not in concurrent_dict[user]['src_list']:
                concurrent_dict[user]['src_list'].append(src)

            # If event id indicates a logon mark the user as such, and add to the concurrent count if
            # the user is already logged on
            if event == LOG_ON:
                if concurrent_dict[user]['logged_on'] == True:
                    concurrent_dict[user]['concurrent'] += 1
                    if concurrent_dict[user]['max_concurrent'] < concurrent_dict[user]['concurrent']:
                        concurrent_dict[user]['max_concurrent'] = concurrent_dict[user]['concurrent']
                else:
                    concurrent_dict[user]['logged_on'] = True

            # If the even id indicates a logoff reduce the concurrent count and, if the concurrent count is 
            # now zero, mark the user as logged off
            elif event == LOG_OFF:
                if 0 < concurrent_dict[user]['concurrent']:
                    concurrent_dict[user]['concurrent'] -= 1
                if concurrent_dict[user]['concurrent'] == 0:
                    concurrent_dict[user]['logged_on'] = False

        # stop scrolling if no more hits
        if len(hits) < 1:
          scrolling = False

    num_found = 0

    if len(concurrent_dict) == 0:
        print (colors.bcolors.WARNING + 'Querying elasticsearch failed - Verify your log configuration file!'+ colors.bcolors.ENDC)
        return

    print('>>> Checking for concurrent logins and writing results to elasticsearch... '+ colors.bcolors.ENDC)

    # record all users with concurrent logins
    for user, data in concurrent_dict.iteritems():
        if data['max_concurrent'] > 0:
            num_found += 1
            write_data(user, data, customer, result_type)

    print(colors.bcolors.WARNING + '[+] ' + str(num_found) + ' concurrent logins found! [+]'+ colors.bcolors.ENDC)

   
def run(customer, result_type = 'concurrent'):
    # Yaaayyy, colors
    print(colors.bcolors.OKBLUE   + '[-] Finding concurrent logins for customer '
          + colors.bcolors.HEADER + customer 
          + colors.bcolors.OKBLUE + ' [-]'
          + colors.bcolors.ENDC)

    find_concurrent(customer, result_type)

    print(colors.bcolors.OKGREEN   + '[+] Finished finding concurrent logins for customer '
          + colors.bcolors.HEADER  + customer
          + colors.bcolors.OKGREEN + ' [+]'
          + colors.bcolors.ENDC)

#run('fakecon')
