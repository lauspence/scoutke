import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from vercel_storage import blob


@deconstructible
class VercelBlobStorage(Storage):
    """Django storage backend for Vercel Blob, used for user-uploaded media."""

    def __init__(self, base_url=None):
        self.base_url = base_url or settings.VERCEL_BLOB_BASE_URL

    def _blob_url(self, name):
        return f"{self.base_url}/{name}"

    def _open(self, name, mode="rb"):
        response = requests.get(self._blob_url(name))
        response.raise_for_status()
        return ContentFile(response.content, name=name)

    def _save(self, name, content):
        content.seek(0)
        result = blob.put(
            pathname=name,
            body=content.read(),
            options={"no_suffix": True},
        )
        return result.get("pathname", name)

    def delete(self, name):
        blob.delete(self._blob_url(name), options={})

    def exists(self, name):
        try:
            blob.head(self._blob_url(name), options={})
            return True
        except Exception:
            return False

    def size(self, name):
        return blob.head(self._blob_url(name), options={})["size"]

    def url(self, name):
        return self._blob_url(name)
