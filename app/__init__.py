from flask import Flask
from flask.ext.cors import CORS
from celery import Celery
import os


app = Flask("HT")
CORS(app)

from app import routes
