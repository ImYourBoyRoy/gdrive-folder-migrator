# tools/__init__.py

import os
import importlib
import inspect
import sys
from typing import Dict, List, Type

def _import_all_modules() -> List[str]:
    """Automatically import all modules and their classes in the package directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    module_files = [
        f[:-3] for f in os.listdir(current_dir)
        if f.endswith('.py') and f != '__init__.py'
    ]

    imported_names = []
    
    for module_name in module_files:
        try:
            # Import the module
            module = importlib.import_module(f'.{module_name}', package=__package__)
            
            # Find all classes defined in the module
            classes = inspect.getmembers(module, inspect.isclass)
            
            # Add classes that are defined in this module (not imported)
            for name, cls in classes:
                if cls.__module__ == f'{__package__}.{module_name}':
                    # Add the class to the global namespace
                    globals()[name] = cls
                    imported_names.append(name)
                    
        except Exception as e:
            print(f"Warning: Failed to import {module_name}: {str(e)}")

    return imported_names

# Perform the imports and populate __all__
__all__ = _import_all_modules()