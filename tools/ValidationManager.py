# tools/ValidationManager.py

from typing import Dict, Any, Tuple, List, Optional
import logging
from .FolderManager import FolderManager
from .FileManager import FileManager
from .ProgressManager import ProgressManager
from .RateLimiter import rate_limited
from .APICache import APICache

class ValidationManager:
    """
    Handles validation of file transfers with caching + rate limiting.
    Validates each file’s size + MD5 and optionally checks for missing folders.
    """

    def __init__(self, service: Any, logger: logging.Logger, progress_manager: ProgressManager = None):
        self.service = service
        self.logger = logger
        self.progress = progress_manager if progress_manager else ProgressManager()
        self.folder_manager = FolderManager(service, logger, self.progress)
        self.file_manager = FileManager(service, logger, self.progress)
        self.cache = APICache()

    @rate_limited
    def validate_file_transfer(self, source_id: str, dest_id: str, path: str) -> Tuple[bool, str]:
        """
        Validates a single file by comparing size + MD5 (if available).
        Returns (True, "") if identical, else (False, "reason").
        Uses caching so subsequent validations of the same IDs won't re-fetch from Drive.
        """
        cache_key = f'validation_{source_id}_{dest_id}'
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            # If we previously validated this exact pair of file IDs,
            # return the same result without another API call
            return cached_result

        try:
            source_file = self.file_manager.get_file_details(source_id)
            dest_file = self.file_manager.get_file_details(dest_id)

            if not source_file or not dest_file:
                result = (False, f"Failed to retrieve file details for {path}")
                self.cache.set(cache_key, result)
                return result

            # Compare sizes
            if source_file.get('size') != dest_file.get('size'):
                result = (False, (
                    f"Size mismatch for {path}: "
                    f"src={source_file.get('size','0')}, dest={dest_file.get('size','0')}"
                ))
                self.cache.set(cache_key, result)
                return result

            # Compare MD5 checksums, if present
            src_md5 = source_file.get('md5Checksum')
            dst_md5 = dest_file.get('md5Checksum')
            if src_md5 and dst_md5 and src_md5 != dst_md5:
                result = (False, f"Checksum mismatch for {path}")
                self.cache.set(cache_key, result)
                return result

            result = (True, "")
            self.cache.set(cache_key, result)
            return result

        except Exception as e:
            result = (False, f"Error validating {path}: {e}")
            self.cache.set(cache_key, result)
            return result

    def validate_migration(self, source_id: str, dest_id: str, is_test: bool = False) -> bool:
        """
        Validates the entire migration by:
          1) Listing source/dest files + folders
          2) Checking for missing or size/MD5 mismatches
          3) Logging errors
        Caches major steps to reduce repeated API calls.
        """
        print("\nStarting migration validation...")
        
        validation_cache_key = f'migration_validation_{source_id}_{dest_id}'
        cached_result = self.cache.get(validation_cache_key)
        if cached_result is not None:
            # If we already computed a result for this exact folder pair, skip
            return cached_result

        try:
            self.logger.info("Collecting source folder contents for validation...")
            source_files, source_folders = self.folder_manager.collect_folder_contents(
                source_id, folder_type="source-validation"
            )

            self.logger.info("Collecting destination folder contents for validation...")
            dest_files, dest_folders = self.folder_manager.collect_folder_contents(
                dest_id, folder_type="destination-validation"
            )

            errors: List[str] = []
            source_paths = list(source_files.keys())
            total_source = len(source_paths)

            # We'll batch progress prints every 50 files
            batch_size = 50
            for idx, path in enumerate(source_paths, start=1):
                if idx % batch_size == 0:
                    print(f"Validated {idx}/{total_source} source files...", end="\r")

                if path not in dest_files:
                    errors.append(f"Missing file in destination: {path}")
                    continue

                s_info = source_files[path]
                d_info = dest_files[path]

                # Quick size check, skip deeper check if sizes differ
                if s_info['size'] != d_info['size']:
                    errors.append(
                        f"Size mismatch for {path}: src={s_info['size']}, dest={d_info['size']}"
                    )
                    continue

                # MD5 check
                success, err_msg = self.validate_file_transfer(s_info['id'], d_info['id'], path)
                if not success:
                    errors.append(err_msg)

            # Check for missing subfolders
            missing_folders = set(source_folders.keys()) - set(dest_folders.keys())
            for folder_path in missing_folders:
                errors.append(f"Missing folder in destination: {folder_path}")

            validation_passed = (len(errors) == 0)
            self.cache.set(validation_cache_key, validation_passed)

            if validation_passed:
                print("\nValidation Passed: All files/folders transferred correctly!")
                self.logger.info("Validation passed. All files/folders match.")
            else:
                print("\nValidation Failed:")
                for e in errors[:10]:
                    print(f" - {e}")
                if len(errors) > 10:
                    print(f"...and {len(errors) - 10} more errors.")

                if is_test:
                    print("\nTest migration validation failed - please check logs.")
                else:
                    print("\nFull migration validation failed - please check logs.")

                for e in errors:
                    self.logger.error(e)

            return validation_passed

        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            return False

    def get_missing_files_list(self, source_id: str, dest_id: str) -> List[str]:
        """
        Return a list of file paths present in source but NOT in destination.
        Ignores size/MD5 mismatches, purely presence-based.
        """
        cache_key = f'missing_files_{source_id}_{dest_id}'
        cached_missing = self.cache.get(cache_key)
        if cached_missing is not None:
            return cached_missing

        self.logger.debug("Collecting missing files for possible re-copy.")
        source_files, _ = self.folder_manager.collect_folder_contents(
            source_id, folder_type="source-missingcheck"
        )
        dest_files, _ = self.folder_manager.collect_folder_contents(
            dest_id, folder_type="dest-missingcheck"
        )

        missing_paths = [path for path in source_files if path not in dest_files]
        self.cache.set(cache_key, missing_paths)
        return missing_paths