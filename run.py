#!flask/bin/python
from flask import Flask, jsonify

app = Flask(__name__)

modules = [
        {
            'id': 1,
            'name': u'beaconing',
            'description': u'Detect Beacons',
            'checked': False
        },
        {
            'id': 2,
            'name': u'blacklisted',
            'description': u'Search for Blacklisted IPs',
            'checked': False
        },
        {
            'id': 3,
            'name': u'concurrent',
            'description': u'Analyze Concurrent Logins',
            'checked': False
        },
        {
            'id': 4,
            'name': u'long_urls',
            'description': u'Analyze Url Length',
            'checked': False
        },
        {
            'id': 5,
            'name': u'scanning',
            'description': u'Look for Network Scans',
            'checked': False
        },
    ]

@app.route('/api/v1.0/modules/list')
def get_modules_list():
    return jsonify({'modules': modules})

if __name__ == "__main__":
    app.run(debug=True)

