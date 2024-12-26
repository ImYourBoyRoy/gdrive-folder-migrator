# tools/FileManager.py

from googleapiclient.errors import HttpError
from typing import Dict, Optional, Any, List, Tuple
import logging
from .ProgressManager import ProgressManager
from .RateLimiter import rate_limited
from .APICache import APICache

class FileManager:
    """Handles file operations in Google Drive with rate limiting + caching."""

    def __init__(self, service: Any, logger: logging.Logger, progress_manager: ProgressManager = None):
        self.service = service
        self.logger = logger
        self.progress = progress_manager if progress_manager else ProgressManager()
        self.cache = APICache()

    @rate_limited
    def get_file_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file details (cached)."""
        cache_key = f'file_details_{file_id}'
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        try:
            details = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, md5Checksum'
            ).execute()
            self.cache.set(cache_key, details)
            return details
        except HttpError as error:
            self.logger.error(f"Error getting file details for {file_id}: {error}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in get_file_details({file_id}): {e}")
            return None

    @rate_limited
    def find_file_in_folder(self, folder_id: str, file_name: str) -> Optional[Dict[str, Any]]:
        """Find file by name in a given folder (cached)."""
        cache_key = f'file_in_folder_{folder_id}_{file_name}'
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        try:
            escaped_name = file_name.replace("'", "\\'")
            results = self.service.files().list(
                q=f"name = '{escaped_name}' and '{folder_id}' in parents",
                fields="files(id, name, mimeType, size, md5Checksum)",
                spaces='drive'
            ).execute()
            files = results.get('files', [])
            result = files[0] if files else None
            if result:
                self.cache.set(cache_key, result)
            return result
        except HttpError as error:
            self.logger.error(f"Error finding file '{file_name}' in folder {folder_id}: {error}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in find_file_in_folder: {e}")
            return None

    def copy_files(self, files: List[Tuple[str, str, str]]) -> List[bool]:
        """
        Copy multiple files with progress tracking and improved large folder handling.
        """
        results = []
        total = len(files)
        
        self.logger.info(f"Starting batch copy of {total} files")
        
        for idx, (file_id, dest_folder_id, file_name) in enumerate(files, start=1):
            self.logger.debug(
                f"[{idx}/{total}] Copying file '{file_name}' "
                f"(file_id={file_id}) to folder {dest_folder_id}"
            )
            
            success = self._copy_file(file_id, dest_folder_id, file_name)
            results.append(success)
            
            if success:
                # Invalidate stale cache
                self.cache.remove(f'file_in_folder_{dest_folder_id}_{file_name}')
            
            if idx % 10 == 0:  # Log progress every 10 files
                self.logger.info(
                    f"Processed {idx}/{total} files in current batch. "
                    f"Success rate: {(results.count(True)/len(results))*100:.1f}%"
                )
        
        return results

    @rate_limited
    def _copy_file(self, file_id: str, dest_folder_id: str, file_name: str) -> bool:
        """Single file copy with rate limiting and fallback error handling."""
        try:
            source_file = self.get_file_details(file_id)
            if not source_file:
                self.logger.warning(f"Skipping copy for {file_id}: no source_file details available.")
                self.progress.update_progress('failed_copies', file_name)
                return False

            # Check if destination already has identical file
            dest_file = self.find_file_in_folder(dest_folder_id, file_name)
            if dest_file and self._files_match(source_file, dest_file):
                self.logger.info(f"Skipping identical file '{file_name}'.")
                self.progress.update_progress('skipped_copies', file_name)
                return True

            # Attempt actual copy
            self.service.files().copy(
                fileId=file_id,
                body={'name': file_name, 'parents': [dest_folder_id]}
            ).execute()

            self.logger.info(f"Copied file: {file_name}")
            self.progress.update_progress('successful_copies', file_name)
            return True

        except HttpError as http_err:
            # Check if it's a known daily-limit error or a large-file error
            if "dailyLimitExceeded" in str(http_err) or "userRateLimitExceeded" in str(http_err):
                self.logger.error(
                    f"Daily limit or user rate limit exceeded when copying {file_name}: {http_err}"
                )
            else:
                self.logger.error(f"HttpError copying {file_name}: {http_err}")
            self.progress.update_progress('failed_copies', file_name)
            return False
        except Exception as e:
            self.logger.error(f"Error copying file '{file_name}': {e}")
            self.progress.update_progress('failed_copies', file_name)
            return False

    def _files_match(self, source_file: Dict[str, Any], dest_file: Dict[str, Any]) -> bool:
        """Compare two files by size + MD5 (and handle Google Docs)."""
        s_md5 = source_file.get('md5Checksum')
        d_md5 = dest_file.get('md5Checksum')
        s_size = source_file.get('size')
        d_size = dest_file.get('size')

        if s_md5 and d_md5 and s_md5 == d_md5 and s_size == d_size:
            return True

        # Handle Google Docs
        s_mime = source_file.get('mimeType', '')
        d_mime = dest_file.get('mimeType', '')
        if s_mime.startswith('application/vnd.google-apps.') and d_mime.startswith('application/vnd.google-apps.'):
            return s_mime == d_mime

        return False
