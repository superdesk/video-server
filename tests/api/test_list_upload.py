import json
from io import BytesIO
from unittest import mock

import pytest
from flask import url_for
from pymongo.errors import ServerSelectionTimeoutError


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_upload_project_success(test_app, client, filestreams):
    mp4_stream = filestreams[0]
    filename = 'sample_0.mp4'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.post(
            url,
            data={
                'file': (BytesIO(mp4_stream), filename)
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)

        assert resp.status == '201 CREATED'
        assert '_id' in resp_data
        assert 'filename' in resp_data
        assert 'storage_id' in resp_data
        assert 'create_time' in resp_data
        assert resp_data['mime_type'] == 'video/mp4'
        assert resp_data['request_address'] == '127.0.0.1'
        assert resp_data['original_filename'] == filename
        assert resp_data['version'] == 1
        assert resp_data['parent'] is None
        assert resp_data['processing'] == {'video': False, 'thumbnail_preview': False, 'thumbnails_timeline': False}
        assert resp_data['thumbnails'] == {'timeline': [], 'preview': {}}
        assert resp_data['url'] == url_for('projects.get_raw_video', project_id=resp_data["_id"], _external=True)


@pytest.mark.parametrize('filestreams', [('sample_0.jpg',)], indirect=True)
def test_upload_project_wrong_codec(test_app, client, filestreams):
    jpg_stream = filestreams[0]
    filename = 'sample_0.jpg'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.post(
            url,
            data={
                'file': (BytesIO(jpg_stream), filename)
            },
            content_type='multipart/form-data'
        )

        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data['file'] == ["Codec: 'mjpeg' is not supported."]


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_upload_project_bad_request(test_app, client, filestreams):
    mp4_stream = filestreams[0]
    filename = 'sample_0.mp4'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.post(
            url,
            data={
                'files': (BytesIO(mp4_stream), filename)
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'file': ['required field']}


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_upload_project_wrong_contenttype(test_app, client, filestreams):
    mp4_stream = filestreams[0]
    filename = 'sample_0.mp4'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.post(
            url,
            data={
                'file': (BytesIO(mp4_stream), filename)
            },
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'file': ['required field']}


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
@mock.patch('pymongo.collection.Collection.insert_one',
            side_effect=ServerSelectionTimeoutError('Timeout error'))
def test_upload_project_cant_set_storage_id(mock_insert_one, test_app, client, filestreams):
    mp4_stream = filestreams[0]
    filename = 'sample_0.mp4'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.post(
            url,
            data={
                'file': (BytesIO(mp4_stream), filename)
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '500 INTERNAL SERVER ERROR'
        assert resp_data == {'error': 'Timeout error'}
        assert list(test_app.mongo.db.projects.find()) == []


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_list_projects(test_app, client, filestreams):
    mp4_stream = filestreams[0]
    filename = 'sample_0.mp4'

    with test_app.test_request_context():
        url = url_for('projects.list_upload_project')
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data == {
            '_items': [],
            '_meta': {
                'page': 1,
                'max_results': test_app.config.get('ITEMS_PER_PAGE'),
                'total': 0
            }
        }
        # create 3 projects
        for i in range(3):
            client.post(
                url,
                data={
                    'file': (BytesIO(mp4_stream), filename)
                },
                content_type='multipart/form-data'
            )
        # list projects (1st page)
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert resp_data['_meta'] == {
            'page': 1,
            'max_results': test_app.config.get('ITEMS_PER_PAGE'),
            'total': 3
        }
        assert len(resp_data['_items']) == test_app.config.get('ITEMS_PER_PAGE')
        assert '_id' in resp_data['_items'][0]
        assert 'filename' in resp_data['_items'][0]
        assert 'storage_id' in resp_data['_items'][0]
        assert 'create_time' in resp_data['_items'][0]
        assert resp_data['_items'][0]['mime_type'] == 'video/mp4'
        assert resp_data['_items'][0]['request_address'] == '127.0.0.1'
        assert resp_data['_items'][0]['original_filename'] == filename
        assert resp_data['_items'][0]['version'] == 1
        assert resp_data['_items'][0]['parent'] is None
        assert resp_data['_items'][0]['processing'] == {
            'video': False,
            'thumbnail_preview': False,
            'thumbnails_timeline': False
        }
        assert resp_data['_items'][0]['thumbnails'] == {'timeline': [], 'preview': {}}
        assert resp_data['_items'][0]['url'] == url_for('projects.get_raw_video',
                                                        project_id=resp_data["_items"][0]["_id"], _external=True)
        # list 1nd page explicitly
        resp = client.get(url, query_string={'page': 1})
        resp_data = json.loads(resp.data)
        assert resp_data['_meta'] == {
            'page': 1,
            'max_results': test_app.config.get('ITEMS_PER_PAGE'),
            'total': 3
        }
        # list 2nd page explicitly
        resp = client.get(url, query_string={'page': 2})
        resp_data = json.loads(resp.data)
        assert len(resp_data['_items']) == 1
        assert resp_data['_meta'] == {
            'page': 2,
            'max_results': test_app.config.get('ITEMS_PER_PAGE'),
            'total': 3
        }
