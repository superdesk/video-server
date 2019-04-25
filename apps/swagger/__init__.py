from flask import Blueprint

bp = Blueprint('swagger', __name__, template_folder='templates', static_folder='static')

from . import routes # noqa


def init_app(app):
    app.register_blueprint(bp, url_prefix='/swagger')
