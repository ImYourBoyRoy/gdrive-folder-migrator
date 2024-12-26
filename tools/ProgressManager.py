# tools/ProgressManager.py

from typing import Dict, Any
from datetime import datetime, timedelta
import sys
from rich.console import Console
from rich.panel import Panel

class ProgressManager:
    """Handles progress display and statistics for migration operations, 
       with real-time percentage, ETA, and logging support."""
    
    def __init__(self):
        self.console = Console()
        self.stats = {
            'total_files': 0,
            'total_folders': 0,
            'processed_files': 0,
            'successful_copies': 0,
            'failed_copies': 0,
            'skipped_copies': 0,
            'created_folders': 0,
            'skipped_folders': 0,
            'start_time': datetime.now()
        }
        self._last_render = datetime.now()

    def increment_folder_count(self):
        self.stats['total_folders'] += 1
        self._display_progress()

    def increment_file_count(self):
        self.stats['total_files'] += 1
        self._display_progress()

    def set_total_counts(self, files: int, folders: int):
        self.stats['total_files'] = files
        self.stats['total_folders'] = folders

    def update_progress(self, operation_type: str, file_name: str = None):
        """
        Update counters, optionally log the file being processed if needed.
        operation_type can be 'successful_copies', 'failed_copies', etc.
        """
        if operation_type in self.stats:
            self.stats[operation_type] += 1
        
        # Only increment processed_files for actual file operations
        if operation_type in ['successful_copies', 'failed_copies', 'skipped_copies']:
            self.stats['processed_files'] += 1
        
        self._display_progress()

    def _calculate_progress(self) -> float:
        """Calculate overall progress as a percentage of files processed against total files."""
        if self.stats['total_files'] == 0:
            return 0.0
            
        # Count all processed files (copied, failed, or skipped)
        processed = (
            self.stats['successful_copies']
            + self.stats['failed_copies']
            + self.stats['skipped_copies']
        )
        
        # For folder progress, we compare created + skipped against total
        folder_progress = 0.0
        if self.stats['total_folders'] > 0:
            folder_progress = (
                (self.stats['created_folders'] + self.stats['skipped_folders'])
                / self.stats['total_folders']
                * 100
            )
            
        # Weight file progress more heavily (80%) than folder progress (20%)
        file_progress = (processed / self.stats['total_files']) * 100
        return (file_progress * 0.8) + (folder_progress * 0.2)

    def _format_duration(self, total_seconds: int) -> str:
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        parts.append(f"{hours:02d}h")
        parts.append(f"{minutes:02d}m")
        parts.append(f"{seconds:02d}s")
        return " ".join(parts)

    def _display_progress(self):
        now = datetime.now()
        # Throttle frequent updates so as not to overload the console
        if (now - self._last_render).total_seconds() < 0.5:
            return
        self._last_render = now

        elapsed = now - self.stats['start_time']
        progress_pct = self._calculate_progress()

        processed = (
            self.stats['successful_copies']
            + self.stats['failed_copies']
            + self.stats['skipped_copies']
        )
        total_files = self.stats['total_files']

        eta_str = "N/A"
        finish_str = "N/A"
        if processed > 0 and total_files > 0:
            elapsed_seconds = elapsed.total_seconds()
            speed = processed / elapsed_seconds if elapsed_seconds > 0 else 0
            if speed > 0:
                remaining = total_files - processed
                etc_seconds = int(remaining / speed)
                eta_str = self._format_duration(etc_seconds)
                finish_time = now + timedelta(seconds=etc_seconds)
                finish_str = finish_time.strftime("%Y-%m-%d %H:%M:%S")

        panel_content = [
            "[bold blue]Migration Progress[/bold blue]",
            "",
            f"📊 Overall Progress: [cyan]{progress_pct:6.1f}%[/cyan]",
            f"⏱️ Elapsed Time: [cyan]{self._format_duration(int(elapsed.total_seconds()))}[/cyan]",
            f"🕒 ETA (Remaining): [cyan]{eta_str}[/cyan]",
            f"⌛ Finish Time: [cyan]{finish_str}[/cyan]",
            "",
            f"📁 Total Folders: [cyan]{self.stats['total_folders']:4d}[/cyan]",
            f"📄 Total Files:   [cyan]{self.stats['total_files']:4d}[/cyan]",
            "",
            f"✅ Successful Copies: [green]{self.stats['successful_copies']:4d}[/green]",
            f"❌ Failed Copies:     [red]{self.stats['failed_copies']:4d}[/red]",
            f"⏭️ Skipped Copies:    [yellow]{self.stats['skipped_copies']:4d}[/yellow]",
            f"📂 Created Folders:   [blue]{self.stats['created_folders']:4d}[/blue]",
            f"⏩ Skipped Folders:   [yellow]{self.stats['skipped_folders']:4d}[/yellow]"
        ]
        
        self.console.clear()
        self.console.print(Panel('\n'.join(panel_content), width=60, padding=(0, 2)))

    def print_final_results(self):
        """Print one last time at the end, without clearing again."""
        self._display_progress()
        self.console.print("[bold green]\nMigration process completed (or ended)![/bold green]")
