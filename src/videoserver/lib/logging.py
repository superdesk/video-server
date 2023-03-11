# -*- coding: utf-8; -*-
#
# This file is part of Superdesk Video Server.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import logging.config

import yaml
from yaml import Loader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('video-server')

# set default levels
logging.getLogger('apps').setLevel(logging.INFO)


def configure_logging(file_path):
    """
    Configure logging.

    :param file_path: file path to log config file
    :type file_path: str
    """
    if not file_path:
        return

    try:
        with open(file_path, 'r') as f:
            logging_dict = yaml.load(f, Loader=Loader)

        logging.config.dictConfig(logging_dict)
    except Exception:
        logger.warning('Cannot load logging config. File: %s', file_path)
