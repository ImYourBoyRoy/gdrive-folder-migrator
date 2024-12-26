# tools/MigrationManager.py

from typing import Dict, Any, Tuple, List, Optional
import logging
from .FolderManager import FolderManager
from .FileManager import FileManager
from .ValidationManager import ValidationManager
from .ProgressManager import ProgressManager
from .RateLimiter import rate_limited, RateLimiter
from .APICache import APICache
import os

class MigrationManager:
    """
    Manages the migration process between Google Drive folders with rate limiting and caching.
    Includes a new 'execute_sync_migration()' that enumerates entire source & destination,
    compares them, and then only copies missing/different files.
    """

    def __init__(
        self,
        service: Any,
        config: Dict[str, Any],
        logger: logging.Logger,
        test_mode: bool = False,
        progress_manager: ProgressManager = None
    ):
        self.service = service
        self.config = config
        self.logger = logger
        self.test_mode = test_mode
        self.cache = APICache()
        
        self.progress_manager = progress_manager if progress_manager else ProgressManager()
        
        # RateLimiter from config
        performance_cfg = self.config.get("performance", {})
        user_rate_limit = performance_cfg.get("user_rate_limit", 12000)
        user_time_window = performance_cfg.get("user_time_window", 60)
        limiter = RateLimiter()
        limiter.configure_rate_limits(
            rate_limit=user_rate_limit,
            time_window=user_time_window
        )
        
        # Initialize managers
        self.folder_manager = FolderManager(service, logger, self.progress_manager)
        self.file_manager = FileManager(service, logger, self.progress_manager)
        self.validation_manager = ValidationManager(service, logger, self.progress_manager)

        # Migration-related flags
        migration_cfg = self.config.get("migration", {})
        self.auto_fix_missing = migration_cfg.get("auto_fix_missing", True)
        self.final_validation = migration_cfg.get("final_validation", True)
        self.batch_size = migration_cfg.get("batch_size", 100)
        self.max_retries = migration_cfg.get("max_retries", 3)
        # Possibly also handle "timeout_seconds", "validate_checksums", etc.

    @rate_limited
    def execute_sync_migration(self) -> bool:
        """
        New approach:
          1) Preliminary tests
          2) Enumerate entire source + entire destination
          3) Diff them to find missing/different files
          4) Create missing subfolders in destination
          5) Copy all missing/different files in one pass
          6) (Optionally) final validation
        """
        if not self.run_preliminary_tests():
            self.logger.error("Preliminary tests failed.")
            return False

        source_id = self.config['source']['folder_id']
        dest_id = self.config['destination']['folder_id']

        # 1) Enumerate entire source
        self.logger.info("Collecting entire source structure...")
        source_files, source_folders = self.folder_manager.collect_folder_contents(source_id, "source-full")
        self.logger.info(f"Found {len(source_files)} files, {len(source_folders)} folders in source.")

        # 2) Enumerate entire destination
        self.logger.info("Collecting entire destination structure...")
        dest_files, dest_folders = self.folder_manager.collect_folder_contents(dest_id, "destination-full")
        self.logger.info(f"Found {len(dest_files)} files, {len(dest_folders)} folders in destination.")
        
        # Set initial totals in progress manager
        self.progress_manager.set_total_counts(len(source_files), len(source_folders))

        # 3) Diff the file sets
        to_copy = []  # list of (source_file_id, relative_path)
        for path, s_info in source_files.items():
            if path not in dest_files:
                # missing in destination
                to_copy.append((s_info['id'], path))
            else:
                # if sizes or checksums differ, copy as well
                d_info = dest_files[path]
                if s_info['size'] != d_info['size'] or (
                    s_info.get('checksum') and d_info.get('checksum') and s_info['checksum'] != d_info['checksum']
                ):
                    to_copy.append((s_info['id'], path))

        self.logger.info(f"Need to copy {len(to_copy)} files (missing or different).")

        # 4) Create missing subfolders in destination
        self.logger.info("Creating subfolders that are missing in destination.")
        self._create_subfolders(source_folders, dest_folders, dest_id)

        # 5) Copy those files
        success = self._copy_missing_files(to_copy, source_files, dest_folders, dest_id)
        if not success:
            self.logger.error("Some files failed to copy in sync approach.")
            return False

        # 6) Optionally final validation
        if self.final_validation:
            self.logger.info("Performing final validation after sync migration.")
            validated = self.validation_manager.validate_migration(source_id, dest_id, is_test=self.test_mode)
            if not validated:
                self.logger.error("Validation failed after sync migration.")
                return False
        
        self.logger.info("Sync migration completed successfully!")
        return True

    def _create_subfolders(self, source_folders: Dict[str, str], dest_folders: Dict[str, str], dest_root_id: str):
        """
        For every folder path in source_folders that doesn't exist in dest_folders,
        create it in the destination, replicating the entire path.
        """
        # Sort by depth so we create parent folders before children
        all_paths = sorted(source_folders.keys(), key=lambda p: p.count('/'))
        
        for path in all_paths:
            if path in dest_folders:
                # already exists
                continue
            folder_name = path.split('/')[-1]
            parent_path = '/'.join(path.split('/')[:-1])
            if parent_path == "":
                parent_id = dest_root_id
            else:
                if parent_path not in dest_folders:
                    self.logger.warning(
                        f"Missing parent folder path '{parent_path}' in destination while creating '{path}'."
                    )
                    continue
                parent_id = dest_folders[parent_path]

            # Create subfolder
            new_id = self.folder_manager.create_folder(folder_name, parent_id)
            if new_id:
                self.logger.info(f"Created subfolder '{path}' in destination (ID={new_id}).")
                dest_folders[path] = new_id
            else:
                self.logger.error(f"Failed to create subfolder '{path}' in destination.")

    def _copy_missing_files(
        self,
        to_copy: List[Tuple[str, str]],
        source_files: Dict[str, Dict[str, Any]],
        dest_folders: Dict[str, str],
        dest_root_id: str
    ) -> bool:
        """
        Actually copies the set of missing/different files from 'to_copy'.
         each to_copy item => (source_file_id, relative_path).
        We locate the correct parent subfolder in destination, and do the copy via file_manager.
        """
        total = len(to_copy)
        success = True

        for idx, (src_id, path) in enumerate(to_copy, start=1):
            # parse path => subfolders, filename
            path_parts = path.split('/')
            *folders, file_name = path_parts
            current_parent = dest_root_id

            # Step through subfolders in the path
            prefix_path = ""
            for subfolder in folders:
                prefix_path = prefix_path + "/" + subfolder if prefix_path else subfolder
                if prefix_path in dest_folders:
                    current_parent = dest_folders[prefix_path]
                else:
                    # fallback if missing in subfolders
                    self.logger.warning(
                        f"Subfolder '{prefix_path}' not found in dest_folders. Attempting creation."
                    )
                    new_id = self.folder_manager.create_folder(subfolder, current_parent)
                    if new_id:
                        dest_folders[prefix_path] = new_id
                        current_parent = new_id
                    else:
                        self.logger.error(f"Unable to create or locate subfolder '{prefix_path}' in dest.")
                        success = False
                        continue

            self.logger.info(f"[{idx}/{total}] Copying '{path}' to parent_id={current_parent}")
            # Actual copy
            copy_ok = self.file_manager._copy_file(src_id, current_parent, file_name)
            if not copy_ok:
                self.logger.error(f"Failed copying '{path}'.")
                success = False

        return success

    def run_preliminary_tests(self) -> bool:
        """
        Checks that source/dest folders exist & are accessible before migration.
        """
        tests = [
            ("Source folder access",
             lambda: self.folder_manager.verify_folder_exists(self.config['source']['folder_id'])),
            ("Destination folder access",
             lambda: self.folder_manager.verify_folder_exists(self.config['destination']['folder_id'])),
        ]
        for test_name, test_fn in tests:
            self.logger.info(f"Running {test_name}...")
            if not test_fn():
                self.logger.error(f"{test_name} failed.")
                return False
            self.logger.info(f"{test_name} passed.")
        return True