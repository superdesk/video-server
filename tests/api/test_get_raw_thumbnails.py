import pytest
from flask import url_for


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_timeline_thumbnail_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture timeline thumbnails
        amount = 3
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        client.get(url)
        # get raw timeline thumbnail
        url = url_for('projects.get_raw_timeline_thumbnail', project_id=project['_id'], index=1)
        resp = client.get(url)

        assert resp.status == '200 OK'
        assert resp.mimetype == 'image/png'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_timeline_thumbnail_wrong_index(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture timeline thumbnails
        amount = 3
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        client.get(url)
        # get raw timeline thumbnail
        url = url_for('projects.get_raw_timeline_thumbnail', project_id=project['_id'], index=10)
        resp = client.get(url)

        assert resp.status == '404 NOT FOUND'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_preview_thumbnail_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture preview thumbnail
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=preview&position=5'
        client.get(url)
        # get raw preview thumbnail
        url = url_for('projects.get_raw_preview_thumbnail', project_id=project['_id'])
        resp = client.get(url)

        assert resp.status == '200 OK'
        assert resp.mimetype == 'image/png'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_preview_thumbnail_404(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.get_raw_preview_thumbnail', project_id=project['_id'])
        resp = client.get(url)

        assert resp.status == '404 NOT FOUND'
