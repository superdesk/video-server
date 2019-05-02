import sys
import os

from flask import current_app as app

from lib.video_editor.ffmpeg import FFMPEGVideoEditor

editor = FFMPEGVideoEditor()


def test_ffmpeg_video_editor_cut_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_cut_video.mp4', None,
        video_cut={'start': 2, 'end': 10}
    )

    assert metadata['width'] == '640'
    assert metadata['height'] == '480'
    assert metadata['duration'] == '8.027031'
    assert metadata['size'] == '666985'
    assert metadata['bit_rate'] == '332180'


def test_ffmpeg_video_editor_crop_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_crop_video.mp4', None,
        video_crop={'width': 500, 'height': 400, 'x': 10, 'y': 10}
    )

    assert metadata['width'] == '500'
    assert metadata['height'] == '400'
    if sys.platform == 'linux':
        assert metadata['bit_rate'] == '553486'
        assert metadata['size'] == '2353910'


def test_ffmpeg_video_editor_rotate_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_rotate_video.mp4', None,
        video_rotate={'degree': 90}
    )

    assert metadata['width'] == '480'
    assert metadata['height'] == '640'


def test_ffmpeg_video_editor_generate_thumbnails(client, filestream):
    metadata = editor.get_meta(filestream)
    filename = 'test_ffmpeg_video_editor_generate_thumbnails'
    for index, thumb in enumerate(
        editor.capture_list_timeline_thumnails(
            filestream,
            filename,
            metadata,
            app.config.get('AMOUNT_FRAMES', 40))
    ):
        app.fs.put(thumb[0], f'test_generate_thumbnails/filename_{index}.png')
    list_files = os.listdir(app.config['FS_MEDIA_STORAGE_PATH'] + f'/test_generate_thumbnails')
    list_files = [fi for fi in list_files if fi.startswith(f'filename_')]

    assert len(list_files) == 41
