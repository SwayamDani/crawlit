#!/usr/bin/env python3
"""
env_loader.py - Environment variable and configuration loader

Provides utilities for loading configuration from:
- Environment variables
- .env files
- Configuration files (JSON, YAML)
- Default values
"""

import os
import logging
import json
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvLoader:
    """
    Loads and manages environment variables and configuration.
    
    Features:
    - Load from .env files
    - Load from environment variables
    - Type conversion (str, int, float, bool, list)
    - Default values
    - Prefix filtering
    - Required variable validation
    """
    
    def __init__(self, env_file: Optional[str] = '.env', auto_load: bool = True,
                 prefix: Optional[str] = None):
        """
        Initialize EnvLoader.
        
        Args:
            env_file: Path to .env file (default: '.env')
            auto_load: Automatically load .env file if it exists
            prefix: Optional prefix to filter environment variables (e.g., 'CRAWLIT_')
        """
        self.env_file = env_file
        self.prefix = prefix
        self.loaded_vars: Dict[str, str] = {}
        
        if auto_load and env_file and os.path.exists(env_file):
            self.load_env_file(env_file)
    
    def load_env_file(self, filepath: str) -> int:
        """
        Load environment variables from a .env file.
        
        Format:
            KEY=value
            # Comments start with #
            EMPTY_VALUE=
            QUOTED="value with spaces"
        
        Args:
            filepath: Path to .env file
            
        Returns:
            Number of variables loaded
        """
        if not os.path.exists(filepath):
            logger.warning(f".env file not found: {filepath}")
            return 0
        
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' not in line:
                        logger.warning(f"Invalid line {line_num} in {filepath}: {line}")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Store in loaded_vars
                    self.loaded_vars[key] = value
                    
                    # Set as environment variable
                    os.environ[key] = value
                    count += 1
            
            logger.info(f"Loaded {count} variables from {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to load .env file {filepath}: {e}")
            raise
        
        return count
    
    def get(self, key: str, default: Any = None, required: bool = False,
            cast: Optional[type] = None) -> Any:
        """
        Get environment variable value.
        
        Args:
            key: Variable name
            default: Default value if not found
            required: Raise error if not found and no default
            cast: Type to cast value to (str, int, float, bool)
            
        Returns:
            Variable value (cast to specified type if provided)
            
        Raises:
            ValueError: If required=True and variable not found
        """
        # Try loaded vars first, then environment
        value = self.loaded_vars.get(key, os.environ.get(key, default))
        
        if value is None and required:
            raise ValueError(f"Required environment variable not found: {key}")
        
        # Cast to specified type
        if value is not None and cast is not None:
            try:
                if cast == bool:
                    # Handle boolean conversion
                    value = self._str_to_bool(value)
                elif cast == list:
                    # Handle list conversion (comma-separated)
                    value = self._str_to_list(value)
                else:
                    value = cast(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to cast {key} to {cast.__name__}: {e}")
                if required:
                    raise
                return default
        
        return value
    
    def get_int(self, key: str, default: int = 0, required: bool = False) -> int:
        """Get integer environment variable"""
        return self.get(key, default, required, cast=int)
    
    def get_float(self, key: str, default: float = 0.0, required: bool = False) -> float:
        """Get float environment variable"""
        return self.get(key, default, required, cast=float)
    
    def get_bool(self, key: str, default: bool = False, required: bool = False) -> bool:
        """Get boolean environment variable"""
        return self.get(key, default, required, cast=bool)
    
    def get_list(self, key: str, default: Optional[List[str]] = None, 
                 required: bool = False) -> List[str]:
        """Get list environment variable (comma-separated)"""
        return self.get(key, default or [], required, cast=list)
    
    def get_all(self, prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Get all environment variables, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter by
            
        Returns:
            Dictionary of environment variables
        """
        prefix = prefix or self.prefix
        
        if prefix:
            return {
                k: v for k, v in os.environ.items()
                if k.startswith(prefix)
            }
        else:
            return dict(os.environ)
    
    def set(self, key: str, value: Any):
        """
        Set environment variable.
        
        Args:
            key: Variable name
            value: Variable value (will be converted to string)
        """
        str_value = str(value)
        os.environ[key] = str_value
        self.loaded_vars[key] = str_value
        logger.debug(f"Set environment variable: {key}")
    
    def unset(self, key: str):
        """
        Unset environment variable.
        
        Args:
            key: Variable name
        """
        if key in os.environ:
            del os.environ[key]
        if key in self.loaded_vars:
            del self.loaded_vars[key]
        logger.debug(f"Unset environment variable: {key}")
    
    def clear(self):
        """Clear all loaded variables"""
        for key in list(self.loaded_vars.keys()):
            if key in os.environ:
                del os.environ[key]
        self.loaded_vars.clear()
        logger.debug("Cleared all loaded environment variables")
    
    @staticmethod
    def _str_to_bool(value: Union[str, bool]) -> bool:
        """
        Convert string to boolean.
        
        True: 'true', 'yes', '1', 'on', 'enabled'
        False: 'false', 'no', '0', 'off', 'disabled'
        """
        if isinstance(value, bool):
            return value
        
        value_lower = str(value).lower().strip()
        
        if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
            return True
        elif value_lower in ('false', 'no', '0', 'off', 'disabled', ''):
            return False
        else:
            raise ValueError(f"Cannot convert '{value}' to boolean")
    
    @staticmethod
    def _str_to_list(value: Union[str, list]) -> List[str]:
        """
        Convert comma-separated string to list.
        
        Args:
            value: Comma-separated string or list
            
        Returns:
            List of strings
        """
        if isinstance(value, list):
            return value
        
        if not value:
            return []
        
        # Split by comma and strip whitespace
        return [item.strip() for item in str(value).split(',') if item.strip()]


class ConfigLoader(EnvLoader):
    """
    Extended configuration loader with JSON/YAML support.
    
    Loads configuration from multiple sources in order of priority:
    1. Environment variables
    2. .env file
    3. Configuration file (JSON/YAML)
    4. Default values
    """
    
    def __init__(self, env_file: Optional[str] = '.env',
                 config_file: Optional[str] = None,
                 auto_load: bool = True):
        """
        Initialize ConfigLoader.
        
        Args:
            env_file: Path to .env file
            config_file: Path to configuration file (JSON)
            auto_load: Automatically load files if they exist
        """
        super().__init__(env_file, auto_load=False)
        
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        
        # Load files in order
        if auto_load:
            if config_file and os.path.exists(config_file):
                self.load_config_file(config_file)
            
            if env_file and os.path.exists(env_file):
                self.load_env_file(env_file)
    
    def load_config_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if not os.path.exists(filepath):
            logger.warning(f"Config file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.endswith('.json'):
                    self.config_data = json.load(f)
                else:
                    # Try JSON by default
                    self.config_data = json.load(f)
            
            logger.info(f"Loaded configuration from {filepath}")
            return self.config_data
        
        except Exception as e:
            logger.error(f"Failed to load config file {filepath}: {e}")
            raise
    
    def get(self, key: str, default: Any = None, required: bool = False,
            cast: Optional[type] = None) -> Any:
        """
        Get configuration value with fallback order:
        1. Environment variable
        2. .env file
        3. Config file
        4. Default value
        
        Args:
            key: Configuration key
            default: Default value
            required: Raise error if not found
            cast: Type to cast to
            
        Returns:
            Configuration value
        """
        # Try environment/loaded vars first
        value = super().get(key, default=None, required=False, cast=None)
        
        # Try config file
        if value is None and key in self.config_data:
            value = self.config_data[key]
        
        # Use default if still None
        if value is None:
            value = default
        
        # Check required
        if value is None and required:
            raise ValueError(f"Required configuration not found: {key}")
        
        # Cast type
        if value is not None and cast is not None:
            try:
                if cast == bool:
                    value = self._str_to_bool(value)
                elif cast == list:
                    if not isinstance(value, list):
                        value = self._str_to_list(value)
                else:
                    value = cast(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to cast {key} to {cast.__name__}: {e}")
                if required:
                    raise
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get configuration section (nested dictionary).
        
        Args:
            section: Section name
            
        Returns:
            Section dictionary
        """
        return self.config_data.get(section, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        # Merge config file, loaded vars, and environment
        result = self.config_data.copy()
        result.update(self.loaded_vars)
        return result


# Global instance for convenience
_default_loader: Optional[EnvLoader] = None


def get_default_loader() -> EnvLoader:
    """Get or create the default EnvLoader instance"""
    global _default_loader
    if _default_loader is None:
        _default_loader = EnvLoader()
    return _default_loader


def load_env(filepath: str = '.env') -> int:
    """
    Convenience function to load .env file.
    
    Args:
        filepath: Path to .env file
        
    Returns:
        Number of variables loaded
    """
    loader = get_default_loader()
    return loader.load_env_file(filepath)


def getenv(key: str, default: Any = None, cast: Optional[type] = None) -> Any:
    """
    Convenience function to get environment variable.
    
    Args:
        key: Variable name
        default: Default value
        cast: Type to cast to
        
    Returns:
        Variable value
    """
    loader = get_default_loader()
    return loader.get(key, default, cast=cast)




