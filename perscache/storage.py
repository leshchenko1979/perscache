import datetime as dt
from abc import ABC, abstractmethod
from pathlib import Path

from beartype import beartype
from beartype.typing import Iterator, Optional, Union


class CacheExpired(Exception):
    ...


class Storage(ABC):
    @abstractmethod
    def read(self, path: Union[str, Path], deadline: dt.datetime) -> bytes:
        """Read the file at the given path and return its contents as bytes.
        If the file does not exist, raise FileNotFoundError. If the file is
        older than the given deadline, raise CacheExpired.
        """
        ...

    @abstractmethod
    def write(self, path: Union[str, Path], data: bytes) -> None:
        """Write the file at the given path."""
        ...


class FileStorage(Storage):
    @beartype
    def __init__(
        self,
        location: Optional[Union[str, Path]] = ".cache",
        max_size: Optional[int] = None,
    ):
        self.location = Path(location)
        self.max_size = max_size

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(location={self.location}, max_size={self.max_size})>"

    def read(self, path: Union[str, Path], deadline: dt.datetime) -> bytes:
        final_path = self.location / path

        if deadline is not None and self.mtime(final_path) < deadline:
            raise CacheExpired

        return self.read_file(self.location / path)

    def write(self, path: Union[str, Path], data: bytes) -> None:
        final_path = self.location / path

        self.ensure_path(final_path.parent)

        if self.max_size and self.size(self.location) + len(data) > self.max_size:
            self.delete_least_recently_used(target_size=self.max_size)

        self.write_file(final_path, data)

    def delete_least_recently_used(self, target_size: int) -> None:
        """Removes the least recently used file from the cache.
        The least recently used file is the one with the smallest last access time.

        Args:
            target_size: The target size of the cache.
        """
        files = sorted(
            self.iterdir(self.location), key=lambda f: self.atime(f), reverse=True
        )

        # find the set of most recently accessed files whose total size
        # is smaller than the target size
        i, size = 0, 0
        while size < target_size and i < len(files):
            size += self.size(files[i])
            i += 1

        # remove remaining files
        for f in files[i - 1 :]:
            self.delete(f)

    def clear(self) -> None:
        for f in self.iterdir(self.location):
            self.delete(f)
        self.rmdir(self.location)

    @abstractmethod
    def read_file(self, path: Union[str, Path]) -> bytes:
        ...

    @abstractmethod
    def write_file(self, path: Union[str, Path]) -> bytes:
        ...

    @abstractmethod
    def ensure_path(self, path: Union[str, Path]) -> None:
        ...

    @abstractmethod
    def iterdir(self, path: Union[str, Path]) -> Iterator[Path]:
        ...

    @abstractmethod
    def rmdir(self, path: Union[str, Path]) -> None:
        ...

    @abstractmethod
    def mtime(self, path: Union[str, Path]) -> dt.datetime:
        ...

    @abstractmethod
    def atime(self, path: Union[str, Path]) -> dt.datetime:
        ...

    @abstractmethod
    def size(self, path: Union[str, Path]) -> int:
        ...

    @abstractmethod
    def delete(self, path: Union[str, Path]) -> None:
        ...


class LocalFileStorage(FileStorage):
    def read_file(self, path: Union[str, Path]) -> bytes:
        return path.read_bytes()

    def write_file(self, path: Union[str, Path], data: bytes) -> None:
        path.write_bytes(data)

    def ensure_path(self, path: Union[str, Path]) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def iterdir(self, path: Union[str, Path]) -> Iterator[Path]:
        return path.iterdir()

    def rmdir(self, path: Union[str, Path]) -> None:
        path.rmdir()

    def mtime(self, path: Union[str, Path]) -> dt.datetime:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)

    def atime(self, path: Union[str, Path]) -> dt.datetime:
        return dt.datetime.fromtimestamp(path.stat().st_atime, tz=dt.timezone.utc)

    def size(self, path: Union[str, Path]) -> int:
        return path.stat().st_size

    def delete(self, path: Union[str, Path]) -> None:
        path.unlink()


class GoogleCloudStorage(FileStorage):
    @beartype
    def __init__(
        self,
        location: Optional[Union[str, Path]] = ".cache",
        max_size: Optional[int] = None,
        storage_options: Optional[dict] = None,
    ) -> None:
        super().__init__(location, max_size)

        import gcsfs

        self.fs = (
            gcsfs.GCSFileSystem(**storage_options)
            if storage_options
            else gcsfs.GCSFileSystem()
        )

    def read_file(self, path: Union[str, Path]) -> bytes:
        with self.fs.open(path, "rb") as f:
            return f.read()

    def write_file(self, path: Union[str, Path], data: bytes) -> None:
        with self.fs.open(path, "wb") as f:
            f.write(data)

    def ensure_path(self, path: Union[str, Path]) -> None:
        if not self.fs.exists(path):
            self.fs.makedirs(path, exist_ok=True)

    def iterdir(self, path: Union[str, Path]) -> Iterator[Path]:
        return self.fs.ls(path)

    def rmdir(self, path: Union[str, Path]) -> None:
        self.fs.rm(path)

    def mtime(self, path: Union[str, Path]) -> dt.datetime:
        mtime = self.fs.info(path)["updated"]
        ts = dt.datetime.strptime(mtime.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        ts = ts.replace(tzinfo=dt.timezone.utc, microsecond=int(mtime[-4:-1]))
        return ts

    def atime(self, path: Union[str, Path]) -> dt.datetime:
        return self.mtime(path)

    def size(self, path: Union[str, Path]) -> int:
        return self.fs.info(path)["size"]

    def delete(self, path: Union[str, Path]) -> None:
        self.fs.rm(path)

    def clear(self):
        self.fs.rm(self.location.as_posix())
