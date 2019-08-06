#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk Video Server.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import importlib
import os

from flask import Flask, jsonify
from flask_pymongo import PyMongo
from werkzeug.exceptions import HTTPException, default_exceptions

from . import settings
from .lib.logging import configure_logging
from .lib.storage import get_media_storage
from .celery_app import init_celery


if os.environ.get('NEW_RELIC_LICENSE_KEY'):
    try:
        import newrelic.agent

        newrelic.agent.initialize(os.path.abspath(os.path.join(os.path.dirname(__file__), 'newrelic.ini')))
    except ImportError:
        pass


def get_app(config=None):
    """App factory.

    :param config: configuration that can override config from `settings.py`
    :return: a new SuperdeskEve app instance
    """
    app = Flask(__name__)

    if config is None:
        config = {}

    config['APP_ABSPATH'] = os.path.abspath(os.path.dirname(__file__))

    for key in dir(settings):
        if key.isupper():
            config.setdefault(key, getattr(settings, key))

    app.config.update(config)

    #: init storage
    media_storage = get_media_storage(app.config.get('MEDIA_STORAGE'))
    app.fs = media_storage

    installed = set()

    def install_app(module_name):
        if module_name in installed:
            return
        installed.add(module_name)
        app_module = importlib.import_module(module_name)
        if hasattr(app_module, 'init_app'):
            app_module.init_app(app)

    for module_name in app.config.get('CORE_APPS', []):
        install_app(f'videoserver.{module_name}')
    #: logging
    configure_logging(app.config['LOG_CONFIG_FILE'])

    # pymongo
    # https://flask-pymongo.readthedocs.io
    def init_db():
        app.mongo = PyMongo(app)

    app.init_db = init_db
    app.init_db()

    init_celery(app)

    def make_json_error(ex):
        message = ex.description if hasattr(ex, 'description') else ex

        if type(message) is not dict:
            message = {'error': message}

        response = jsonify(message)
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)

        return response

    for code in default_exceptions:
        app.register_error_handler(code, make_json_error)

    return app


if __name__ == '__main__':
    debug = True
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', '5050'))
    app = get_app()
    app.run(host=host, port=port)
