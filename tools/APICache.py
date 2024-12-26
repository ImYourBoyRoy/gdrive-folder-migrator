# tools/APICache.py

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import threading

class APICache:
    """
    Thread-safe caching system for API responses to reduce redundant API calls.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(APICache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        self.cache_duration = timedelta(minutes=30)  # Cache entries expire after 30 minutes
        self._initialized = True

    def get(self, cache_key: str) -> Optional[Any]:
        """Retrieve a value from cache if it exists and hasn't expired."""
        with self._cache_lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if datetime.now() - entry['timestamp'] < self.cache_duration:
                    return entry['value']
                else:
                    # Expired
                    del self._cache[cache_key]
        return None

    def set(self, cache_key: str, value: Any):
        """Store a value in the cache with current timestamp."""
        with self._cache_lock:
            self._cache[cache_key] = {
                'value': value,
                'timestamp': datetime.now()
            }

    def clear(self):
        """Clear all cached entries."""
        with self._cache_lock:
            self._cache.clear()

    def remove(self, cache_key: str):
        """Remove a specific cache entry."""
        with self._cache_lock:
            self._cache.pop(cache_key, None)
