from flask import Blueprint

bp = Blueprint('projects', __name__)

from . import routes


def init_app(app):
    app.register_blueprint(bp, url_prefix='/projects')
