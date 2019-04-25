import os

import pytest

from app import get_app


@pytest.fixture(scope='session')
def test_app():
    test_app = get_app()
    test_app.config['TESTING'] = True
    test_app.config['MONGO_DBNAME'] = 'sd_video_editor_test'
    test_app.config['MONGO_URI'] = 'mongodb://localhost:27017/sd_video_editor_test'
    test_app.config['FS_MEDIA_STORAGE_PATH'] = os.path.join(os.path.dirname(__file__), 'media', 'projects')
    test_app.init_db()

    return test_app


@pytest.fixture(scope='session')
def client(test_app):
    client = test_app.test_client()

    with test_app.app_context():
        yield client


@pytest.fixture(scope='session')
def filestream():
    test_path = os.path.dirname(os.path.abspath(__file__))
    with open(f'{test_path}/storage/fixtures/sample.mp4', 'rb') as f:
        filestream = f.read()
    return filestream
