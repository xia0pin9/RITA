# RITA
("John's mom" was already taken)

### Current Version 0.1

RITA is a toolkit which is intended to help approach the often overwhelming task of combing through piles of log data looking for suspect behavior.

RITA is inteded to help in the search for indicators of compromise in enterprise networks of varying size. The framework was instructed by it's engineers experience in penetration testing with the question of how they'd catch themselves, thus the analysis tends to looks specifically at the indicators their tools tend to leave behind.


## Running the tools
RITA was developed under Debian based Linux operating systems, and has not yet been tested anywhere else. Anyone who is interested in running it under other conditions is encouraged to contact the development team at dev-hunt@gmail.com.

#### On Debian based distrobutions start by installing at least these dependancies the command:

You will also need to install a full ELK stack. There's an excellent guide to installing Elasticsearch, Logstash, and Kibana over at [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-install-elasticsearch-logstash-and-kibana-4-on-ubuntu-14-04).

There's also a sizeable pile of system dependencies that help do math and parse logs:

`sudo apt-get install build-essential python-dev python-pip libatlas-dev libatlas3-base liblapack-dev gfortran libpng12-dev libfreetype6-dev libblas-dev liblapack.dev gfortran`

Also, you'll need a number of python specific dependencies.

`pip install < requirements.txt`

Start up the flask server.

`python run.py`

Then navigate to `http://localhost:5000` to use the interface. 

#### Some things to keep in mind

When you choose a customer name you must choose and *ALL LOWER CASE* customer name, otherwise Elasticsearch will stop working. This is due to the fact that the customer name field is being used as an index to Elasticsearch which has a REST style interface, and therefore refuses to load URL strings which wil have caps in them.

There is a specific way that data must be parsed into elasticsearch, look at app/analysis/field_names.py for the specific field names that the data must be mapped to.

This is a work in progress. Right now the "Results" page contains a link to kibana. Soon it will contain data. 

Once again, we're working on this, and we'd love to hear from you, suggestions, requests for bug fixes, and code are all welcome.

#### Planned Progress

1. Documentation. There needs to be explanation of how to use this framework, how to add to the framework, and how the framework works in general.
2. Better log parsing solutions. If you have logstash filters that work for your environment we'd love to hear about those filters, or add them to the framework with your permission.
3. Results, we'd like to see a results page that shows data on the fly as logs are being processed.
4. Add algorithms. Do you have ideas for finding interesting data in logs? Let us know! Do you have code that already does it? If you want to share, send us a merge and we'll look at getting it into the project.
