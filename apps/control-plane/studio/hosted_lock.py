"""Lifetime, nonblocking Linux flock for the single ACA worker on shared storage.

Acquire before constructing StudioService: recovery mutates persisted jobs.
Azure Files SMB must support flock (modern Linux CIFS); unsupported mounts fail
closed. Do not unlink the lock file: waiters must always lock the same inode.
"""

import os


class HostedWorkerLock:
    def __init__(self, config):
        self.config = config
        self._fd = None

    @property
    def acquired(self):
        return self._fd is not None

    def ready(self):
        if not self.acquired or not self.config.storage_ready():
            return False
        try:
            os.fsync(self._fd)
            return True
        except OSError:
            return False

    def __enter__(self):
        if self.acquired:
            raise RuntimeError("The ACA worker lock is already acquired.")
        try:
            import fcntl
        except ImportError:
            raise RuntimeError("ACA hosting requires Linux flock support.") from None
        path = self.config.data_root / ".studio-worker.lock"
        if path.is_symlink():
            raise RuntimeError("The ACA worker lock cannot be a symlink.")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.ftruncate(fd, 0)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.fsync(fd)
        except OSError as exc:
            os.close(fd)
            raise RuntimeError("Cannot acquire the ACA single-worker lock; another worker is active or storage does not support flock.") from exc
        self._fd = fd
        return self

    def __exit__(self, *_):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
