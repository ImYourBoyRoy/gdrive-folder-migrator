# tools/FolderManager.py

from googleapiclient.errors import HttpError
from typing import Dict, Optional, Any, List, Tuple
import logging
from .ProgressManager import ProgressManager
from .RateLimiter import rate_limited
from .APICache import APICache
from .FileManager import FileManager

class FolderManager:
    """Handles folder operations in Google Drive with rate limiting and caching."""

    def __init__(self, service: Any, logger: logging.Logger, progress_manager: ProgressManager = None):
        self.service = service
        self.logger = logger
        self.progress = progress_manager if progress_manager else ProgressManager()
        self.cache = APICache()
        self.file_manager = FileManager(service, logger, progress_manager)

    @rate_limited
    def _count_items(self, folder_id: str) -> int:
        cache_key = f'item_count_{folder_id}'
        cached_count = self.cache.get(cache_key)
        if cached_count is not None:
            return cached_count

        try:
            total = 0
            page_token = None
            while True:
                results = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, mimeType)",
                    pageToken=page_token,
                    pageSize=1000,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                items = results.get('files', [])
                total += len(items)
                
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        total += self._count_items(item['id'])
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            self.cache.set(cache_key, total)
            return total
        except Exception as e:
            self.logger.error(f"Error counting items: {str(e)}")
            return 0

    @rate_limited
    def get_folder_details(self, folder_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f'folder_details_{folder_id}'
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            details = self.service.files().get(
                fileId=folder_id,
                fields='id, name, mimeType, parents'
            ).execute()
            self.cache.set(cache_key, details)
            return details
        except HttpError as error:
            self.logger.error(f"Error getting folder details: {str(error)}")
            return None

    @rate_limited
    def create_folder(self, name: str, parent_id: str) -> Optional[str]:
        try:
            existing_id = self.find_folder_by_name(parent_id, name)
            if existing_id:
                self.logger.info(f"Folder '{name}' already exists (ID: {existing_id})")
                self.progress.update_progress('skipped_folders')
                return existing_id

            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name'
            ).execute()
            
            new_id = folder.get('id')
            if self.verify_folder_exists(new_id):
                self.logger.info(f"Created folder '{name}' (ID: {new_id})")
                self.progress.update_progress('created_folders')
                self.cache.remove(f'folder_contents_{parent_id}')
                return new_id
            return None
        except HttpError as error:
            self.logger.error(f"Error creating folder '{name}': {str(error)}")
            return None

    @rate_limited
    def verify_folder_exists(self, folder_id: str) -> bool:
        try:
            folder = self.service.files().get(fileId=folder_id, fields='id, name').execute()
            return bool(folder and folder.get('id'))
        except HttpError:
            return False

    @rate_limited
    def find_folder_by_name(self, parent_id: str, folder_name: str) -> Optional[str]:
        cache_key = f'folder_by_name_{parent_id}_{folder_name}'
        cached_id = self.cache.get(cache_key)
        if cached_id is not None:
            return cached_id

        try:
            escaped_name = folder_name.replace("'", "\\'")
            query = (
                f"name = '{escaped_name}' and '{parent_id}' in parents "
                "and mimeType = 'application/vnd.google-apps.folder'"
            )
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()
            files = results.get('files', [])
            folder_id = files[0]['id'] if files else None
            if folder_id:
                self.cache.set(cache_key, folder_id)
            return folder_id
        except HttpError as error:
            self.logger.error(f"Error finding folder: {str(error)}")
            return None

    @rate_limited
    def collect_folder_contents(self, folder_id: str, folder_type: str = "") -> Tuple[Dict[str, Dict], Dict[str, str]]:
        cache_key = f'folder_contents_full_{folder_id}'
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        files_dict = {}
        folders_dict = {}
        
        total_items = self._count_items(folder_id)
        processed_items = 0

        def process_items(f_id: str, path: str = ""):
            nonlocal processed_items
            page_token = None
            while True:
                try:
                    results = self.service.files().list(
                        q=f"'{f_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id, name, mimeType, size, md5Checksum)",
                        pageToken=page_token,
                        pageSize=1000,
                        spaces='drive',
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    ).execute()

                    items = results.get('files', [])
                    for item in items:
                        processed_items += 1
                        progress = (processed_items / total_items * 100) if total_items > 0 else 0
                        print(f"\rAnalyzing {folder_type} data: {progress:0.1f}% complete", end="", flush=True)
                        
                        current_path = f"{path}/{item['name']}" if path else item['name']
                        if item['mimeType'] == 'application/vnd.google-apps.folder':
                            folders_dict[current_path] = item['id']
                            self.progress.increment_folder_count()
                            process_items(item['id'], current_path)
                        else:
                            files_dict[current_path] = {
                                'id': item['id'],
                                'size': int(item.get('size', 0)),
                                'checksum': item.get('md5Checksum')
                            }

                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break

                except HttpError as error:
                    self.logger.error(f"Error collecting folder contents: {str(error)}")
                    break
        
        process_items(folder_id)
        print()
        data_tuple = (files_dict, folders_dict)
        self.cache.set(cache_key, data_tuple)
        return data_tuple

    @rate_limited
    def get_folder_contents(self, folder_id: str) -> List[Dict[str, Any]]:
        cache_key = f'folder_contents_{folder_id}'
        cached_contents = self.cache.get(cache_key)
        if cached_contents:
            return cached_contents

        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                orderBy="name",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            contents = results.get('files', [])
            self.cache.set(cache_key, contents)
            return contents
        except HttpError as error:
            self.logger.error(f"Error getting folder contents: {str(error)}")
            return []

    @rate_limited
    def get_total_file_count(self, folder_id: str) -> int:
        cache_key = f'total_file_count_{folder_id}'
        cached_val = self.cache.get(cache_key)
        if cached_val is not None:
            return cached_val

        try:
            total_files = 0
            page_token = None
            while True:
                results = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, mimeType)",
                    pageToken=page_token,
                    pageSize=1000,
                    spaces='drive',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                items = results.get('files', [])
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        total_files += self.get_total_file_count(item['id'])
                    else:
                        total_files += 1

                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            self.cache.set(cache_key, total_files)
            return total_files
        except Exception as e:
            self.logger.error(f"Error counting files: {str(e)}")
            return 0

    def print_folder_structure(self, folder_id: str, prefix: str = "") -> None:
        try:
            folder = self.get_folder_details(folder_id)
            if not folder:
                return
            print(f"{prefix}📁 {folder['name']}")

            items = self.get_folder_contents(folder_id)
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    self.print_folder_structure(item['id'], prefix + "  ")
                else:
                    print(f"{prefix}  📄 {item['name']}")
        except HttpError as error:
            self.logger.error(f"Error printing folder structure: {str(error)}")
