import json
from elasticsearch import Elasticsearch
from field_names import *

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

def get_data( customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len, sort = ""):
	# get elasticsearch handle
	global es

	# If this is the first call, build a query
	if scroll_id == "":
		# make a query
		query = build_query( constraints, ignore )

		# Initialize the page (Representation of the query that you want to search)
		page = es.search(
			index = customer, 
			doc_type = doc_type,            
			fields = fields,        # Comma-separated list of fields to return as part of a hit 
			scroll = '1m',          # How long the server will keep data for the next scroll event
			#search_type = 'scan',  # Scan search type disables sorting and just scans everything
			size = scroll_len,      # Number of search results to return (default: 10)
			sort = sort,            # Sort the returned information
			body = query)           # Your query (clientip:... = search for specific ip)
	else:
		# Get chunk of data!
		page = es.scroll( scroll_id = scroll_id, scroll = '1m')

	# Update the scroll id to keep track of where you are in your results
	scroll_id = page['_scroll_id']

	# Get total # of results on page and set scroll size to that number
	scroll_size = page['hits']['total']

	# Return the current page hits and updated scroll id
	return page['hits']['hits'], scroll_id, scroll_size


def write_data(data, customer, result_type, refresh_index = False):
	# Label results with type of analysis performed
	data['result_type'] = result_type

	# Write results to elasticsearch
	try:
		es.index(index = customer, doc_type="results", body=data, refresh = refresh_index )
	except:
		print "Error writing to elasticsearch"
