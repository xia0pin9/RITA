from flask import Flask
from flask.ext.cors import CORS
import os


app = Flask("HT")
CORS(app)

from app import routes
