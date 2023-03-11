import os

import pytest
from videoserver.lib.storage.file_system_storage import FileSystemStorage


@pytest.mark.parametrize('filestreams', [('sample_0.mp4', 'sample_0.jpg', 'sample_1.jpg')], indirect=True)
def test_fs_storage_put(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream, jpg_stream_0, jpg_stream_1 = filestreams

    project_id = 'project_one'
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        thumbn_0_storage_id = storage.put(
            content=jpg_stream_0,
            filename='sample_1_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail'
        )
        thumbn_1_storage_id = storage.put(
            content=jpg_stream_1,
            filename='sample_2_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail'
        )
        assert os.path.exists(
            os.path.join(test_app.config['FS_MEDIA_STORAGE_PATH'], storage_id)
        )
        assert os.path.exists(
            os.path.join(test_app.config['FS_MEDIA_STORAGE_PATH'], thumbn_0_storage_id)
        )
        assert os.path.exists(
            os.path.join(test_app.config['FS_MEDIA_STORAGE_PATH'], thumbn_1_storage_id)
        )


@pytest.mark.parametrize('filestreams', [('sample_0.mp4', 'sample_0.jpg')], indirect=True)
def test_fs_storage_put_already_exist(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream, jpg_stream_0 = filestreams

    project_id = 'project_one'
    with test_app.app_context():
        with pytest.raises(ValueError, match="Argument 'project_id' is required when 'asset_type' is 'project'"):
            storage_id = storage.put(
                content=mp4_stream,
                filename='sample_video.mp4',
                asset_type='project'
            )
        with pytest.raises(ValueError, match="Argument 'storage_id' is required when 'asset_type' is not 'project'"):
            storage.put(
                content=jpg_stream_0,
                filename='sample_image.jpg',
                asset_type='thumbnail'
            )
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        storage.put(
            content=jpg_stream_0,
            filename='sample_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail'
        )
        with pytest.raises(Exception):
            storage.put(
                content=jpg_stream_0,
                filename='sample_image.jpg',
                storage_id=storage_id,
                asset_type='thumbnail',
                override=False
            )
        storage.put(
            content=jpg_stream_0,
            filename='sample_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail',
        )


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_fs_storage_get(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream = filestreams[0]
    project_id = 'project_one'
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        filestream = storage.get(storage_id)
        assert filestream == mp4_stream

        with pytest.raises(FileNotFoundError):
            storage.get(storage_id + '.random.png')


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_fs_storage_get_range(test_app, filestreams):
    storage = FileSystemStorage()
    project_id = 'project_one'
    mp4_stream = filestreams[0]
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        filestream = storage.get(storage_id)
        assert len(filestream) == 2617862

        filestream_range = storage.get_range(storage_id, 0, 1000000)
        assert len(filestream_range) == 1000000

        filestream_range = storage.get_range(storage_id, 1000000, 1000000)
        assert len(filestream_range) == 1000000

        filestream_range = storage.get_range(storage_id, 2000000, 1000000)
        assert len(filestream_range) == 617862

        filestream_range = storage.get_range(storage_id, 3000000, 1000000)
        assert len(filestream_range) == 0


@pytest.mark.parametrize('filestreams', [('sample_0.mp4', 'sample_0.jpg', 'sample_1.jpg')], indirect=True)
def test_fs_storage_replace(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream, jpg_stream_0, jpg_stream_1 = filestreams
    project_id = 'project_one'
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        thumbn_0_storage_id = storage.put(
            content=jpg_stream_0,
            filename='sample_1_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail'
        )
        storage.replace(
            content=jpg_stream_1,
            storage_id=thumbn_0_storage_id,
        )
        assert jpg_stream_1 == storage.get(thumbn_0_storage_id)


@pytest.mark.parametrize('filestreams', [('sample_0.mp4', 'sample_0.jpg')], indirect=True)
def test_fs_storage_delete(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream, jpg_stream_0 = filestreams
    project_id = 'project_one'
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        storage.delete(storage_id)
        with pytest.raises(FileNotFoundError):
            storage.get(storage_id)


@pytest.mark.parametrize('filestreams', [('sample_0.mp4', 'sample_0.jpg')], indirect=True)
def test_fs_storage_delete_dir(test_app, filestreams):
    storage = FileSystemStorage()
    mp4_stream, jpg_stream_0 = filestreams
    project_id = 'project_one'
    with test_app.app_context():
        storage_id = storage.put(
            content=mp4_stream,
            filename='sample_video.mp4',
            project_id=project_id,
            asset_type='project'
        )
        thumbn_0_storage_id = storage.put(
            content=jpg_stream_0,
            filename='sample_1_image.jpg',
            storage_id=storage_id,
            asset_type='thumbnail'
        )

        storage.delete_dir(storage_id)
        with pytest.raises(FileNotFoundError):
            storage.get(storage_id)
            storage.get(thumbn_0_storage_id)

        assert not os.path.exists(os.path.dirname(storage._get_file_path(storage_id)))
