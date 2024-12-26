# tools/ComparisonManager.py

from typing import Dict, Any, List, Tuple
import logging
from .FolderManager import FolderManager
from .FileManager import FileManager
from datetime import datetime

class ComparisonManager:
    """Handles comparison operations between source and destination folders (synchronous)."""

    def __init__(self, service: Any, logger: logging.Logger):
        self.service = service
        self.logger = logger
        self.folder_manager = FolderManager(service, logger)
        self.file_manager = FileManager(service, logger)

    def compare_folders(self, source_id: str, dest_id: str, detail_level: str = 'basic') -> Dict[str, Any]:
        print("\nStarting folder comparison (synchronous)...")
        start_time = datetime.now()
        
        try:
            print("\nAnalyzing source folder...")
            source_files, source_folders = self.folder_manager.collect_folder_contents(source_id, "source")
            
            print("\nAnalyzing destination folder...")
            dest_files, dest_folders = self.folder_manager.collect_folder_contents(dest_id, "destination")
            
            comparison = self._generate_comparison_report(
                source_files, source_folders,
                dest_files, dest_folders,
                detail_level
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()
            total_file_ops = len(source_files) + len(dest_files)
            comparison['performance'] = {
                'elapsed_time': elapsed_time,
                'files_per_second': (total_file_ops / elapsed_time) if elapsed_time > 0 else 0
            }
            return comparison
        except Exception as e:
            self.logger.error(f"Error during folder comparison: {str(e)}")
            print(f"\nError during comparison: {str(e)}")
            raise

    def _generate_comparison_report(
        self,
        source_files: Dict[str, Dict],
        source_folders: Dict[str, str],
        dest_files: Dict[str, Dict],
        dest_folders: Dict[str, str],
        detail_level: str
    ) -> Dict[str, Any]:
        source_total_size = sum(f['size'] for f in source_files.values())
        dest_total_size = sum(f['size'] for f in dest_files.values())

        missing_files = []
        size_mismatches = []
        checksum_mismatches = []
        file_types = {}

        for path, source_file in source_files.items():
            file_ext = path.split('.')[-1].lower() if '.' in path else 'no_extension'
            file_types.setdefault(file_ext, {'count': 0, 'total_size': 0})
            file_types[file_ext]['count'] += 1
            file_types[file_ext]['total_size'] += source_file['size']

            if path not in dest_files:
                missing_files.append({'path': path, 'size': source_file['size']})
            else:
                dest_file = dest_files[path]
                if dest_file['size'] != source_file['size']:
                    size_mismatches.append({
                        'path': path,
                        'source_size': source_file['size'],
                        'dest_size': dest_file['size']
                    })
                elif (source_file.get('checksum') and dest_file.get('checksum') 
                      and source_file['checksum'] != dest_file['checksum']):
                    checksum_mismatches.append(path)

        depth_stats = self._calculate_depth_stats(source_folders)

        comparison = {
            'source_stats': {
                'total_files': len(source_files),
                'total_folders': len(source_folders),
                'total_size': source_total_size,
                'file_types': file_types,
                'depth_stats': depth_stats
            },
            'dest_stats': {
                'total_files': len(dest_files),
                'total_folders': len(dest_folders),
                'total_size': dest_total_size
            },
            'discrepancies': {
                'missing_files': missing_files,
                'size_mismatches': size_mismatches,
                'checksum_mismatches': checksum_mismatches,
                'missing_folders': list(set(source_folders.keys()) - set(dest_folders.keys())),
                'extra_folders': list(set(dest_folders.keys()) - set(source_folders.keys()))
            },
            'completion_percentage': (
                (len(dest_files) / len(source_files) * 100) if source_files else 100
            )
        }

        if detail_level == 'detailed':
            comparison.update({
                'file_details': self._generate_file_details(source_files, dest_files),
                'folder_details': self._generate_folder_details(source_folders, dest_folders)
            })
        return comparison

    def _calculate_depth_stats(self, folders: Dict[str, str]) -> Dict[str, Any]:
        depths = [path.count('/') for path in folders.keys()]
        return {
            'max_depth': max(depths) if depths else 0,
            'average_depth': sum(depths)/len(depths) if depths else 0,
            'depth_distribution': {d: depths.count(d) for d in set(depths)}
        }

    def _generate_file_details(self, source_files: Dict[str, Dict], dest_files: Dict[str, Dict]) -> Dict[str, List]:
        return {
            'matching_files': [
                path for path in source_files
                if path in dest_files and source_files[path]['size'] == dest_files[path]['size']
            ],
            'different_files': [
                {
                    'path': path,
                    'source_size': source_files[path]['size'],
                    'dest_size': dest_files[path]['size']
                }
                for path in source_files
                if path in dest_files and source_files[path]['size'] != dest_files[path]['size']
            ],
            'missing_files': [
                path for path in source_files if path not in dest_files
            ]
        }

    def _generate_folder_details(self, source_folders: Dict[str, str], dest_folders: Dict[str, str]) -> Dict[str, List[str]]:
        return {
            'matching_folders': list(set(source_folders.keys()) & set(dest_folders.keys())),
            'missing_folders': list(set(source_folders.keys()) - set(dest_folders.keys())),
            'extra_folders': list(set(dest_folders.keys()) - set(source_folders.keys()))
        }

    def print_comparison_report(self, comparison: Dict[str, Any]) -> None:
        print("\nFolder Comparison Report")
        print("=======================\n")

        src_stats = comparison['source_stats']
        dst_stats = comparison['dest_stats']

        print("Overall Statistics:")
        print(f"Source: {src_stats['total_files']} files, "
              f"{src_stats['total_folders']} folders, "
              f"{src_stats['total_size'] / (1024*1024*1024):.2f} GB")
        print(f"Destination: {dst_stats['total_files']} files, "
              f"{dst_stats['total_folders']} folders, "
              f"{dst_stats['total_size'] / (1024*1024*1024):.2f} GB")

        if 'performance' in comparison:
            perf = comparison['performance']
            print(f"\nPerformance Metrics:")
            print(f"Elapsed Time: {perf['elapsed_time']:.2f} seconds")
            print(f"Processing Speed: {perf['files_per_second']:.2f} files/second")

        print(f"\nCompletion: {comparison['completion_percentage']:.1f}%")

        depth_stats = src_stats['depth_stats']
        print(f"\nDirectory Structure:")
        print(f"Maximum Depth: {depth_stats['max_depth']} levels")
        print(f"Average Depth: {depth_stats['average_depth']:.1f} levels")

        # top 5 file types
        file_types = src_stats['file_types']
        sorted_types = sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        print("\nTop File Types:")
        for ext, stats in sorted_types:
            print(f"  .{ext}: {stats['count']} files, {stats['total_size']/(1024*1024):.2f} MB")

        discrepancies = comparison['discrepancies']
        if any(discrepancies.values()):
            print("\nDiscrepancies Found:")
            if discrepancies['missing_files']:
                mf_count = len(discrepancies['missing_files'])
                print(f"\nMissing Files ({mf_count}):")
                missing_size = sum(f['size'] for f in discrepancies['missing_files'])
                print(f"Total size of missing files: {missing_size / (1024*1024):.2f} MB")
                for file_info in discrepancies['missing_files'][:10]:
                    print(f"  {file_info['path']} ({file_info['size']/(1024*1024):.2f} MB)")
                if mf_count > 10:
                    more_files = mf_count - 10
                    remaining_size = sum(f['size'] for f in discrepancies['missing_files'][10:])
                    print(f"  ...and {more_files} more files (total remaining size: {remaining_size/(1024*1024):.2f} MB)")

            if discrepancies['size_mismatches']:
                sm_count = len(discrepancies['size_mismatches'])
                print(f"\nSize Mismatches ({sm_count}):")
                for mismatch in discrepancies['size_mismatches'][:10]:
                    print(f"  {mismatch['path']}")
                    print(f"    Source: {mismatch['source_size']/(1024*1024):.2f} MB")
                    print(f"    Destination: {mismatch['dest_size']/(1024*1024):.2f} MB")
                if sm_count > 10:
                    print(f"  ...and {sm_count - 10} more mismatches")

            if discrepancies['checksum_mismatches']:
                ch_count = len(discrepancies['checksum_mismatches'])
                print(f"\nChecksum Mismatches ({ch_count}):")
                for path in discrepancies['checksum_mismatches'][:10]:
                    print(f"  {path}")
                if ch_count > 10:
                    print(f"  ...and {ch_count - 10} more mismatches")

            if discrepancies['missing_folders']:
                mfd_count = len(discrepancies['missing_folders'])
                print(f"\nMissing Folders ({mfd_count}):")
                for folder in sorted(discrepancies['missing_folders'])[:10]:
                    print(f"  {folder}")
                if mfd_count > 10:
                    print(f"  ...and {mfd_count - 10} more folders")
        else:
            print("\nNo discrepancies found - folders are identical!")
