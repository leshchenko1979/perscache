import datetime as dt
from abc import ABC, abstractmethod
from pathlib import Path


class CacheExpired(Exception):
    ...


class Storage(ABC):
    @abstractmethod
    def read(self, path: str, deadline: dt.datetime) -> bytes:
        """Read the file at the given path and return its contents as bytes.
        If the file does not exist, raise FileNotFoundError. If the file is
        older than the given deadline, raise CacheExpired.
        """
        ...

    @abstractmethod
    def write(self, path: str, data: bytes) -> None:
        """Write the file at the given path."""
        ...


class LocalFileStorage(Storage):
    def __init__(self, location: str = ".cache", max_size: int = None):
        self.location = Path(location)
        self.max_size = max_size

    def __repr__(self) -> str:
        return f"<LocalFileStorage(location='{self.location}', max_size={self.max_size})>"

    def read(self, path: str, deadline: dt.datetime) -> bytes:
        final_path = self.location / path

        if deadline is not None and final_path.stat().st_mtime < deadline.timestamp():
            raise CacheExpired

        with open(self.location / path, "rb") as f:
            return f.read()

    def write(self, path: str, data: bytes) -> None:
        final_path = self.location / path

        if not final_path.parent.exists():
            final_path.parent.mkdir(parents=True)

        if self.max_size and self.location.stat().st_size + len(data) > self.max_size:
            self.remove_least_recently_used(target_size=self.max_size)

        with open(final_path, "wb") as f:
            f.write(data)

    def remove_least_recently_used(self, target_size: int) -> None:
        """Removes the least recently used file from the cache.
        The least recently used file is the one with the smallest last access time.
        """
        files = sorted(
            self.location.iterdir(), key=lambda f: f.stat().st_atime, reverse=True
        )

        # find the set of most recently accessed files whose total size
        # is smaller than the target size
        i, size = 0, 0
        while size < target_size and i < len(files):
            size += files[i].stat().st_size
            i += 1

        # remove remaining files
        for f in files[i - 1 :]:
            f.unlink()
