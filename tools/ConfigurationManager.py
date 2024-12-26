# tools/ConfigurationManager.py

from typing import Dict
from pathlib import Path
from datetime import datetime
import json

class ConfigurationManager:
    def __init__(self, config_path: str = './config.json'):
        self.config_path = config_path
        self.config = self._load_configuration()
        self._validate_configuration()
        self._setup_directories()

    def _load_configuration(self) -> Dict:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in configuration file")

    def _validate_configuration(self) -> None:
        required_fields = [
            'credentials.client_secrets_path',
            'credentials.token_path',
            'source.folder_id',
            'destination.folder_id'
        ]

        for field in required_fields:
            parts = field.split('.')
            current = self.config
            for part in parts:
                if part not in current:
                    raise ValueError(f"Missing required configuration field: {field}")
                current = current[part]

    def _setup_directories(self) -> None:
        log_dir = Path(self.config['logging']['log_directory'])
        log_dir.mkdir(parents=True, exist_ok=True)

    def get_credentials_path(self) -> str:
        return self.config['credentials']['client_secrets_path']

    def get_token_path(self) -> str:
        return self.config['credentials']['token_path']

    def get_log_path(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(Path(self.config['logging']['log_directory']) / f'migration_log_{timestamp}.log')
