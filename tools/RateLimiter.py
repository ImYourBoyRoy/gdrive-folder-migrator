# tools/RateLimiter.py

from datetime import datetime, timedelta
import time
from typing import Any
import logging
from functools import wraps
import threading
import random

class RateLimiter:
    """
    Singleton rate limiter for Google Drive API requests.
    Dynamically configurable from external config (e.g. 12000 requests per 60 seconds).
    Also includes truncated exponential backoff for certain 4xx/5xx errors.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RateLimiter, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self.request_times = []
        # Default: 1000 requests / 60 seconds (overridden by configure_rate_limits())
        self.rate_limit = 1000
        self.time_window = 60 
        self.logger = logging.getLogger(__name__)
        self._initialized = True
        self._request_lock = threading.Lock()

    def configure_rate_limits(self, rate_limit: int, time_window: int):
        """
        Optionally call this after creating RateLimiter() 
        to override default limits with config-based values.
        Example: (12000 requests, 60 seconds).
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.logger.info(
            f"RateLimiter configured: {self.rate_limit} requests per {self.time_window}s."
        )

    def wait_if_needed(self):
        """Thread-safe global rate-limiting logic (token bucket style)."""
        with self._request_lock:
            now = datetime.now()
            # Drop timestamps older than our window
            self.request_times = [
                t for t in self.request_times
                if (now - t) < timedelta(seconds=self.time_window)
            ]
            if len(self.request_times) >= self.rate_limit:
                oldest_timestamp = self.request_times[0]
                sleep_time = self.time_window - (now - oldest_timestamp).total_seconds()
                if sleep_time > 0:
                    self.logger.debug(
                        f"Rate limit reached. Sleeping {sleep_time:.2f}s to comply."
                    )
                    time.sleep(sleep_time)
                    now = datetime.now()
                    # Clean up after sleep
                    self.request_times = [
                        t for t in self.request_times
                        if (now - t) < timedelta(seconds=self.time_window)
                    ]
            self.request_times.append(now)

    def execute_with_retry(
            self, func, *args, 
            max_retries=10, 
            max_backoff=64.0, 
            **kwargs
        ):
        """
        Execute 'func' with truncated exponential backoff 
        for HTTP status 403, 429, 500, 503.
        """
        base_delay = 1.0  # initial wait
        retry_count = 0

        while True:
            try:
                self.wait_if_needed()
                return func(*args, **kwargs)
            except Exception as e:
                status = getattr(getattr(e, 'resp', None), 'status', None)
                # only certain status codes are retriable
                if status not in [403, 429, 500, 503]:
                    # non-retriable -> re-raise
                    raise
                if retry_count >= max_retries:
                    # too many attempts
                    self.logger.error(
                        f"Max retries ({max_retries}) reached. Giving up on {func.__name__}"
                    )
                    raise

                # truncated exponential backoff: min((2^retry_count), max_backoff)
                delay = min(base_delay * (2 ** retry_count), max_backoff)
                # add random jitter (0..1s)
                jitter = random.uniform(0, 1)
                sleep_time = delay + jitter
                retry_count += 1

                self.logger.warning(
                    f"Request failed with status={status}. "
                    f"Retry {retry_count}/{max_retries} in {sleep_time:.1f}s. Error: {e}"
                )
                time.sleep(sleep_time)

def rate_limited(func):
    """
    Decorator for applying RateLimiter + exponential backoff to any method.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        limiter = RateLimiter()
        return limiter.execute_with_retry(func, *args, **kwargs)
    return wrapped
