#!flask/bin/python
from app import app
import sys
import argparse


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-p','--port', type=int, help='Set port to use')
    parser.add_argument('-d','--debug', action='store_true', help='Turn Debugging on')
    parser.add_argument('-t','--no_threads', action='store_false', help='Turn off threading')
    args = parser.parse_args()

    app.run(debug=args.debug, threaded=args.no_threads, port=args.port)
