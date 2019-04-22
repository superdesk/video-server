from . import fs_media_storage


class MediaStorage():
    def get_media_storage(self, name):
        if str.lower(name) == 'filesystem':
            return fs_media_storage.FileSystemMediaStorage
        if str.lower(name) == 'amazon':
            return None
        return None




