from flask import current_app as app
from flask import render_template, jsonify
from flask_swagger import swagger

from . import bp


@bp.route('/spec')
def spec_data():
    swag = swagger(app)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Video editor API"
    return jsonify(swag)


@bp.route('/')
def swag():
    return render_template('index.html')
