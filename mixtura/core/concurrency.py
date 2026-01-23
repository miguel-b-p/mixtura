"""
Concurrency primitives for Mixtura.

This module provides thread synchronization tools, specifically a Read-Write lock
that allows multiple providers to run in parallel (shared mode) but enables
a provider to request exclusive access (exclusive mode), effectively pausing others.
"""

import threading
from contextlib import contextmanager
from typing import Generator, Dict


class ProviderLock:
    """
    A Reader-Writer lock with support for lock escalation.
    
    In shared mode (readers), multiple threads can acquire the lock.
    In exclusive mode (writer), only one thread can hold the lock.
    
    This implementation tracks reader threads to allow "lock escalation":
    If a thread holding a shared lock requests exclusive access, it temporarily
    releases its shared lock, acquires exclusive, and then restores shared lock.
    This prevents deadlocks where a thread waits for itself to release the read lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._readers_ok = threading.Condition(self._lock)
        self._writers_ok = threading.Condition(self._lock)
        
        self._active_readers = 0
        self._active_writers = 0
        self._waiting_writers = 0
        
        # Track which threads are reading and how many times (reentrancy)
        self._reader_threads: Dict[int, int] = {}

    def acquire_shared(self) -> None:
        """
        Acquire the lock in shared mode.
        """
        tid = threading.get_ident()
        with self._lock:
            # If we are already a reader, just increment
            if tid in self._reader_threads:
                self._reader_threads[tid] += 1
                return

            # Wait while there is an active writer or waiting writers
            while self._active_writers > 0 or self._waiting_writers > 0:
                self._readers_ok.wait()
            
            self._active_readers += 1
            self._reader_threads[tid] = 1

    def release_shared(self) -> None:
        """Release the lock from shared mode."""
        tid = threading.get_ident()
        with self._lock:
            if tid not in self._reader_threads:
                raise RuntimeError("Thread does not hold shared lock")
                
            self._reader_threads[tid] -= 1
            if self._reader_threads[tid] == 0:
                del self._reader_threads[tid]
                self._active_readers -= 1
                if self._active_readers == 0:
                    self._writers_ok.notify_all()

    def acquire_exclusive(self) -> None:
        """
        Acquire the lock in exclusive mode.
        If current thread holds shared lock, it WILL DEADLOCK unless used via `exclusive()` context manager
        which handles escalation, or if manual escalation is done.
        
        Standard implementation: blocks until no readers/writers.
        """
        with self._lock:
            self._waiting_writers += 1
            try:
                while self._active_readers > 0 or self._active_writers > 0:
                    self._writers_ok.wait()
                self._active_writers += 1
            finally:
                self._waiting_writers -= 1

    def release_exclusive(self) -> None:
        """Release the lock from exclusive mode."""
        with self._lock:
            self._active_writers -= 1
            self._writers_ok.notify_all()
            self._readers_ok.notify_all()

    @contextmanager
    def shared(self) -> Generator[None, None, None]:
        """Context manager for shared access."""
        self.acquire_shared()
        try:
            yield
        finally:
            self.release_shared()

    @contextmanager
    def exclusive(self) -> Generator[None, None, None]:
        """
        Context manager for exclusive access with automatic escalation.
        
        If the current thread holds a shared lock, it temporarily releases it,
        acquires exclusive lock, and re-acquires shared lock on exit.
        """
        tid = threading.get_ident()
        is_reader = False
        reader_count = 0
        
        # Check if we need escalation
        with self._lock:
            if tid in self._reader_threads:
                is_reader = True
                reader_count = self._reader_threads[tid]
        
        if is_reader:
            # Escalation path
            # 1. Release shared lock completely
            for _ in range(reader_count):
                self.release_shared()
                
            try:
                # 2. Acquire exclusive
                self.acquire_exclusive()
                try:
                    yield
                finally:
                    self.release_exclusive()
            finally:
                # 3. Restore shared lock
                for _ in range(reader_count):
                    self.acquire_shared()
        else:
            # Normal exclusive path
            self.acquire_exclusive()
            try:
                yield
            finally:
                self.release_exclusive()


# Global instance
global_provider_lock = ProviderLock()
