import os

import pytest

from app import get_app


@pytest.fixture
def client():
    test_app = get_app()
    test_app.config['TESTING'] = True
    test_app.config['MONGO_DBNAME'] = 'superdesk_test'
    client = test_app.test_client()

    with test_app.app_context():
        yield client
    

@pytest.fixture
def test_path():
    test_path = os.path.dirname(os.path.abspath(__file__))
    return test_path


@pytest.fixture
def filestream():
    test_path = os.path.dirname(os.path.abspath(__file__))
    with open(f'{test_path}/storage/fixtures/sample.mp4', 'rb') as f:
        filestream = f.read()
    return filestream