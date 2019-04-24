from . import errors
from . import routes
from media import blueprint
from .routes import bp


def init_app(app):
    blueprint(bp, app)
