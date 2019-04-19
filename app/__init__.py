from flask import Flask
from . import errors
from . import routes

# create application instance
app = Flask(__name__)
