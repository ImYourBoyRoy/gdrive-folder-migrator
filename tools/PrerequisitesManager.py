# tools/PrerequisitesManager.py

import importlib
import subprocess
import sys
from typing import List, Dict, Tuple

class PrerequisitesManager:
    """Manages package dependencies and their installation."""

    REQUIRED_PACKAGES = {
        'google-auth-oauthlib': 'google_auth_oauthlib',
        'google-api-python-client': 'googleapiclient',
        'rich': 'rich',
        'pathlib': 'pathlib'
    }

    def __init__(self):
        self.missing_packages = []
        self.installation_required = False

    def check_prerequisites(self) -> bool:
        """Check if all required packages are installed."""
        self.missing_packages = []
        
        for package, import_name in self.REQUIRED_PACKAGES.items():
            try:
                importlib.import_module(import_name)
            except ImportError:
                self.missing_packages.append(package)
                self.installation_required = True

        return not self.installation_required

    def display_status(self):
        """Display the status of required packages."""
        if not self.missing_packages:
            print("\n✅ All required packages are installed.")
            return

        print("\n⚠️  Missing required packages:")
        for package in self.missing_packages:
            print(f"  • {package}")

    def install_missing_packages(self) -> bool:
        """Offer to install missing packages and handle the installation."""
        if not self.missing_packages:
            return True

        print("\nWould you like to install the missing packages? (y/n)")
        response = input().lower().strip()

        if response != 'y':
            print("Installation cancelled. Please install the required packages manually.")
            return False

        print("\nInstalling missing packages...")
        try:
            for package in self.missing_packages:
                print(f"\nInstalling {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ Successfully installed {package}")

            # Verify installations
            self.check_prerequisites()
            if self.missing_packages:
                print("\n❌ Some packages failed to install correctly.")
                return False

            print("\n✅ All required packages have been successfully installed.")
            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error during package installation: {str(e)}")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error during installation: {str(e)}")
            return False

    def verify_environment(self) -> bool:
        """Complete verification of the environment."""
        if self.check_prerequisites():
            self.display_status()
            return True

        self.display_status()
        return self.install_missing_packages()