from elasticsearch import Elasticsearch

es = Elasticsearch()

# Initialize the page (Representation of the query that you want to search)
page = es.search(
  index = 'logstash-ht', # This identifies the log you want to search
  scroll = '2m',                 # How long the server will keep data for the next scroll event
  search_type = 'scan',          # Scan search type disables sorting and just scans everything
  size = 50,                   # Number of search results to return (default: 10)
  body = "")                       # Your query (clientip:... = search for specific ip)

# Get current scroll id (this tells you where you are in the search)
sid = page['_scroll_id']

# Get total number results on page and set scroll size to that number
scroll_size = page['hits']['total']
print "Total number of results: " + str(scroll_size)

# Scroll through page until no more results found
while (scroll_size > 0):
  print "Scrolling..."
  print sid
  page = es.scroll(scroll_id = sid, scroll = '2m')
  # Update the scroll ID
  sid = page['_scroll_id']
   # Get the number of results that we returned in the last scroll
  scroll_size = len(page['hits']['hits'])
  print "scroll size: " + str(scroll_size)
  # Do something with the obtained data
#  for hit in page['hits']['hits']:
#    print hit['_source']['customer']
