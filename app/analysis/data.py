import json
from elasticsearch import Elasticsearch
es = Elasticsearch()


def build_query ( constraints, ignore ):
	# Initialize the body of the query
	response = {'query': {'filtered':{'filter':{'bool':{}},'query':{'match_all':{}}}}}
	
	# Add any constraints (match specific terms in search)
	if constraints:
		response['query']['filtered']['filter']['bool']['must'] = []
		for term in constraints:
			response['query']['filtered']['filter']['bool']['must'].append( {'term': term} )

	# Add NOT constraints (match items that do not have specific term)
	if ignore:
                response['query']['filtered']['filter']['bool']['must_not'] = []
                for term in ignore:
                        response['query']['filtered']['filter']['bool']['must_not'].append( {'term': term} )
	
	if not ignore and not constraints:
		del response['query']['filtered']['filter']

	# return the query
	return response

def get_scroll_id_and_size ( doc_type, fields, constraints, ignore, scroll_len, sort_data):
	
	# make a query
	query = build_query( constraints, ignore )

	# get elasticsearch handle
	global es

	# Initialize the page (Representation of the query that you want to search)
	page = es.search(
		index = 'logstash-ht', 
		doc_type = doc_type,            
		fields = fields,        # Comma-separated list of fields to return as part of a hit 
		scroll = '1m',          # How long the server will keep data for the next scroll event
		search_type = 'scan',   # Scan search type disables sorting and just scans everything
		size = scroll_len,      # Number of search results to return (default: 10)
		sort = sort_data,       # Sort the returned information
		body = query)           # Your query (clientip:... = search for specific ip)

	# Get current scroll id (this tells you where you are in the search)
	scroll_id = page['_scroll_id']
	
	# Get total # of results on page and set scroll size to that number
	scroll_size = page['hits']['total']

	# Return '_scroll_id' and 'total' fields
	return scroll_id, scroll_size


def get_data( doc_type, fields, constraints, ignore, scroll_id, scroll_len, sort = ""):
	
	# If this is the first call, build a query
	if scroll_id == "":
		# Get scroll id and scroll size from query
		scroll_id, scroll_size = get_scroll_id_and_size( doc_type, fields, constraints, ignore, scroll_len, sort )

	# Get elasticsearch handle
	global es

	# Get chunk of data!
	page = es.scroll( scroll_id = scroll_id, scroll = '1m')

	# Update the scroll id to keep track of where you are in your results
	scroll_id = page['_scroll_id']

	# Return the current page hits and updated scroll id
	return page['hits']['hits'], scroll_id


def write_data(data, result_type):
	# Label results with type of analysis performed
	data['result_type'] = result_type

	# Write results to elasticsearch
	try:
		es.index(index="logstash-ht", doc_type="results", body=data)
	except:
		print "Error writing to elasticsearch"




################################################
############### TESTING ########################
###############################################

# fields = ['datetime','src','dst'] 

# customer = 'test'
# constraints = [{'customer':'test'}]
# ignore=[]

# scroll_id = ""
# scroll_len = 12

# count = 0

# scrolling = True
# while scrolling:
	
# 	hits, scroll_id = get_data(fields, constraints, ignore, scroll_id, scroll_len)

# 	print "Scroll ", count, "... "
# 	for h in hits:
# 		print h['fields']

# 	if len(hits) < 1:
# 		scrolling = False
	
# 	count += 1

# data = '''{
#     "message": "",
#     "@version": "1",
#     "@timestamp": "2015-07-22T16:58:35.000Z",
#     "datetime": "Jul 22, 2015 12:58:35 PM",
#     "duration": "1.0",
#     "dst": "192.168.1.0",
#     "dstport": "100",
#     "src": "192.168.1.1",
#     "srcport": "90",
#     "proto": "lmnop",
#     "customer": "test3"
# }'''
# write_data(data, "test3")


##################################################
################ EXAMPLE CODE ####################
##################################################

#from elasticsearch import Elasticsearch
#
#es = Elasticsearch()
#
## Initialize the page (Representation of the query that you want to search)
#page = es.search(
#  index = 'logstash-2015.07.22', # This identifies the log you want to search
#  scroll = '2m',                 # How long the server will keep data for the next scroll event
#  search_type = 'scan',          # Scan search type disables sorting and just scans everything
#  size = 1000,                   # Number of search results to return (default: 10)
#  q = "*")                       # Your query (clientip:... = search for specific ip)
#
## Get current scroll id (this tells you where you are in the search)
#sid = page['_scroll_id']
#
## Get total number results on page and set scroll size to that number
#scroll_size = page['hits']['total']
#print "Total number of results: " + str(scroll_size)
#
## Scroll through page until no more results found
#while (scroll_size > 0):
#  print "Scrolling..."
#  page = es.scroll(scroll_id = sid, scroll = '2m')
#  # Update the scroll ID
#  sid = page['_scroll_id']
#   # Get the number of results that we returned in the last scroll
#  scroll_size = len(page['hits']['hits'])
#  print "scroll size: " + str(scroll_size)
#  # Do something with the obtained data
#  for hit in page['hits']['hits']:
#    print hit['_source']['clientport']

	 
