#!/usr/bin/env python3

import os
import sys
import argparse
from pathlib import Path

def check_prerequisites():
    """Initial check for prerequisites before importing other modules."""
    try:
        from tools.PrerequisitesManager import PrerequisitesManager
        manager = PrerequisitesManager()
        return manager.verify_environment()
    except ImportError as e:
        print(f"\n❌ Error importing PrerequisitesManager: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during prerequisites check: {str(e)}")
        return False

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Google Drive Folder Migration Tool (Enhanced Logging)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    Run a test migration:
    $ python migrate.py --test
    
    Run a full migration:
    $ python migrate.py
    
    Use a specific config file:
    $ python migrate.py --config /path/to/config.json
    
    Print folder structure only:
    $ python migrate.py --print-structure
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='./config.json',
        help='Path to configuration file (default: ./config.json)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode using TestPath folder'
    )
    
    parser.add_argument(
        '--print-structure',
        action='store_true',
        help='Only print folder structure without performing migration'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare source and destination folders without performing migration'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed comparison when using --compare'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Set logging level (overrides config file setting)'
    )
    
    return parser.parse_args()

def main():
    print("\nGoogle Drive Migration Tool (Enhanced)")
    print("=====================================\n")
    
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please resolve the issues before proceeding.")
        return 1
    
    print("\n✅ Prerequisites verification completed successfully.")
    
    try:
        from tools import (
            ConfigurationManager,
            LogManager,
            AuthenticationManager,
            MigrationManager,
            ComparisonManager
        )
        
        args = parse_arguments()
        
        # Load config
        config_manager = ConfigurationManager(args.config)
        
        if args.log_level:
            config_manager.config['logging']['log_level'] = args.log_level
        
        # Initialize logging
        log_manager = LogManager(
            log_path=config_manager.get_log_path(),
            log_level=config_manager.config['logging']['log_level']
        )
        logger = log_manager.get_logger()
        
        logger.info("Starting Google Drive Migration Tool with enhanced logs.")
        
        # Initialize authentication
        auth_manager = AuthenticationManager(
            credentials_path=config_manager.get_credentials_path(),
            token_path=config_manager.get_token_path(),
            logger=logger
        )
        
        success, service = auth_manager.authenticate()
        if not success or not service:
            logger.error("Authentication failed.")
            return 1
        
        # Progress manager
        from tools.ProgressManager import ProgressManager
        progress_manager = ProgressManager()
        
        # Initialize migration manager
        migration_manager = MigrationManager(
            service=service,
            config=config_manager.config,
            logger=logger,
            test_mode=args.test,
            progress_manager=progress_manager
        )
        
        # Handle --print-structure / --compare
        if args.print_structure or args.compare:
            source_folder_id = config_manager.config['source']['folder_id']
            dest_folder_id = config_manager.config['destination']['folder_id']
            
            if args.print_structure:
                print("\nSource Folder Structure:")
                print("=======================")
                migration_manager.folder_manager.print_folder_structure(source_folder_id)
                
                print("\nDestination Folder Structure:")
                print("===========================")
                migration_manager.folder_manager.print_folder_structure(dest_folder_id)
                return 0
                
            if args.compare:
                comparison_manager = ComparisonManager(service, logger)
                detail_level = 'detailed' if args.detailed else 'basic'
                
                comparison = comparison_manager.compare_folders(
                    source_folder_id, 
                    dest_folder_id,
                    detail_level
                )
                comparison_manager.print_comparison_report(comparison)
                return 0
        
        # Otherwise, do the migration
        logger.info("Beginning migration process...")
        if migration_manager.execute_sync_migration():
            print("\n✅ Migration completed successfully.")
            logger.info("Migration completed successfully.")
            return 0
        else:
            print("\n❌ Migration failed - check logs for details.")
            logger.error("Migration failed. Check logs for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if 'logger' in locals():
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
