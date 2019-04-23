from . import routes
from media import blueprint


def init_app(app):
    blueprint(routes.bp, app)
