import json
from bson import ObjectId

import pytest
from flask import url_for


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_retrieve_project_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # retrieve project
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.get(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '200 OK'
        assert '_id' in resp_data
        assert 'filename' in resp_data
        assert 'storage_id' in resp_data
        assert 'create_time' in resp_data
        assert resp_data['mime_type'] == 'video/mp4'
        assert resp_data['request_address'] == '127.0.0.1'
        assert resp_data['original_filename'] == project['original_filename']
        assert resp_data['version'] == 1
        assert resp_data['parent'] is None
        assert resp_data['processing'] == {'video': False, 'thumbnail_preview': False, 'thumbnails_timeline': False}
        assert resp_data['thumbnails'] == {'timeline': [], 'preview': {}}
        assert resp_data['url'] == url_for('projects.get_raw_video', project_id=resp_data["_id"], _external=True)
        assert resp_data['metadata']['codec_name'] == 'h264'
        assert resp_data['metadata']['codec_long_name'] == 'H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10'
        assert resp_data['metadata']['width'] == 1280
        assert resp_data['metadata']['height'] == 720
        assert resp_data['metadata']['r_frame_rate'] == '25/1'
        assert resp_data['metadata']['bit_rate'] == 1045818
        assert resp_data['metadata']['nb_frames'] == 375
        assert resp_data['metadata']['duration'] == 15.0
        assert resp_data['metadata']['format_name'] == 'mov,mp4,m4a,3gp,3g2,mj2'
        assert 'size' in resp_data['metadata']


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_retrieve_project_404(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # retrieve project
        url = url_for('projects.retrieve_edit_destroy_project', project_id="definitely_not_object_id")
        resp = client.get(url)
        assert resp.status == '404 NOT FOUND'

        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        client.delete(url)
        resp = client.get(url)
        assert resp.status == '404 NOT FOUND'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_destroy_project_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.delete(url)
        assert resp.status == '204 NO CONTENT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_destroy_project_fails(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        client.delete(url)
        resp = client.delete(url)
        assert resp.status == '404 NOT FOUND'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_409_response(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
        # it means next request will return a finshed result,
        # since we want to test 409 response, we must set processing flag in db directly
        test_app.mongo.db.projects.find_one_and_update(
            {'_id': ObjectId(project['_id'])},
            {'$set': {'processing.video': True}}
        )

        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        trim = '2.0,6.0'
        resp = client.put(
            url,
            data=json.dumps({
                "trim": trim
            }),
            content_type='application/json'
        )
        assert resp.status == '409 CONFLICT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_no_edit_rules_provided(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_version_1(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        trim = '2.0,6.0'
        resp = client.put(
            url,
            data=json.dumps({
                "trim": trim
            }),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_trim_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 6.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "%s,%s" % (start, end)
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert not resp_data['processing']['video']
        assert resp_data['metadata']['duration'] == end - start
        # edit request have trim end greater than duration
        old_duration = resp_data['metadata']['duration']
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 6.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "%s,%s" % (start, end)
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert not resp_data['processing']['video']
        assert resp_data['metadata']['duration'] == old_duration - start


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_trim_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # incorrect type
        resp = client.put(
            url,
            data=json.dumps({
                "trim": 123
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ["must be of string type"]}

        # malformed format
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "x,y"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ["value does not match regex '^\\d+\\.?\\d*,\\d+\\.?\\d*$'"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "6.0,2.0"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ["'start' value must be less than 'end' value"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "0,1"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ['Trimmed video duration must be at least 2 seconds']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "0,15"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ["'end' value of trim is duplicating an entire video"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "-1,3"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ['start time must be greater than 0']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": "0,0"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ['end time must be greater than 1']}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_rotate_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 90
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 720
        assert resp_data['metadata']['height'] == 1280


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_rotate_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 70
            }),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_crop_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,0,640,480"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 480


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_crop_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # incorrect type
        resp = client.put(
            url,
            data=json.dumps({
                "crop": 1
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["must be of string type"]}

        # malformed format
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "x,y,w,h"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["value does not match regex '^\\d+,\\d+,\\d+,\\d+$'"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "2000,0,640,480"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['x is less than minimum allowed crop width']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,1000,640,480"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['y is less than minimum allowed crop height']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "300,0,1000,480"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["width of crop's frame is outside a video's frame"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,200,640,600"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["height of crop's frame is outside a video's frame"]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,200,10000,600"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['width 10000 is greater than maximum allowed crop width (3840)']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,0,300,600"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['width 300 is less than minimum allowed crop width (320)']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": "0,0,640,100"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['height 100 is less than minimum allowed crop height (180)']}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 640
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 360


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 0
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'scale': [f'min value is {test_app.config.get("MIN_VIDEO_WIDTH")}']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 5000
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'scale': [f'max value is {test_app.config.get("MAX_VIDEO_WIDTH")}']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1280
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': ['video and crop option have exactly the same width']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1440
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {
            'trim': ['interpolation is permitted only for videos which have width less than 1280px']
        }

        # edit request
        test_app.config['ALLOW_INTERPOLATION'] = False
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1440
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {
            'trim': ['interpolation of pixels is not allowed']
        }


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_and_crop_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 640,
                "crop": "0,0,400,400"
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 640


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_remove_thumbnails(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture 3 timeline thumbnails
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=timeline&amount=3'
        client.get(url)
        # capture preview thumbnail
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=preview&position=2'
        client.get(url)
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 90
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)

        assert resp_data['thumbnails']['timeline'] == []
        # we keep preview thumbnail
        assert resp_data['thumbnails']['preview'] is not None
