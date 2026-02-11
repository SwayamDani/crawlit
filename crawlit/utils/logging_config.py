#!/usr/bin/env python3
"""
logging_config.py - Enhanced logging configuration with structured output and rotation
"""

import logging
import logging.handlers
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ContextualFormatter(logging.Formatter):
    """Enhanced formatter with contextual information"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, include_context: bool = True):
        if fmt is None:
            if include_context:
                fmt = '%(asctime)s [%(levelname)-8s] [%(name)s] [%(funcName)s:%(lineno)d] %(message)s'
            else:
                fmt = '%(asctime)s [%(levelname)-8s] %(message)s'
        super().__init__(fmt, datefmt)
        self.include_context = include_context


class LoggingConfig:
    """
    Enhanced logging configuration with structured output, rotation, and multiple handlers.
    
    Features:
    - Structured JSON logging
    - Log rotation (size-based and time-based)
    - Multiple output formats (console, file, JSON file)
    - Configurable log levels per module
    - Contextual information (crawl ID, URL, depth, etc.)
    """
    
    def __init__(
        self,
        level: Union[str, int] = logging.INFO,
        log_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        json_log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_file: bool = False,
        enable_json: bool = False,
        console_format: str = 'standard',  # 'standard', 'detailed', 'json'
        file_format: str = 'detailed',  # 'standard', 'detailed', 'json'
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        when: str = 'midnight',  # For time-based rotation
        interval: int = 1,  # Days
        use_rotation: bool = True,
        rotation_type: str = 'size',  # 'size' or 'time'
        module_levels: Optional[Dict[str, Union[str, int]]] = None
    ):
        """
        Initialize logging configuration.
        
        Args:
            level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (default: current directory)
            log_file: Name of the log file (default: 'crawlit.log')
            json_log_file: Name of the JSON log file (default: 'crawlit.json.log')
            enable_console: Enable console logging
            enable_file: Enable file logging
            enable_json: Enable JSON file logging
            console_format: Console format ('standard', 'detailed', 'json')
            file_format: File format ('standard', 'detailed', 'json')
            max_bytes: Maximum size for size-based rotation
            backup_count: Number of backup files to keep
            when: When to rotate for time-based rotation ('midnight', 'H', 'D', etc.)
            interval: Interval for time-based rotation
            use_rotation: Enable log rotation
            rotation_type: Type of rotation ('size' or 'time')
            module_levels: Dictionary mapping module names to log levels
        """
        self.level = level if isinstance(level, int) else getattr(logging, level.upper())
        self.log_dir = Path(log_dir) if log_dir else Path.cwd()
        self.log_file = log_file or 'crawlit.log'
        self.json_log_file = json_log_file or 'crawlit.json.log'
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        self.console_format = console_format
        self.file_format = file_format
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.when = when
        self.interval = interval
        self.use_rotation = use_rotation
        self.rotation_type = rotation_type
        self.module_levels = module_levels or {}
        
        # Ensure log directory exists
        if self.enable_file or self.enable_json:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def configure(self) -> None:
        """Configure logging with the specified settings"""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            
            if self.console_format == 'json':
                console_handler.setFormatter(JSONFormatter())
            elif self.console_format == 'detailed':
                console_handler.setFormatter(ContextualFormatter(include_context=True))
            else:  # standard
                console_handler.setFormatter(ContextualFormatter(include_context=False))
            
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.enable_file:
            file_path = self.log_dir / self.log_file
            
            if self.use_rotation:
                if self.rotation_type == 'time':
                    file_handler = logging.handlers.TimedRotatingFileHandler(
                        str(file_path),
                        when=self.when,
                        interval=self.interval,
                        backupCount=self.backup_count,
                        encoding='utf-8'
                    )
                else:  # size
                    file_handler = logging.handlers.RotatingFileHandler(
                        str(file_path),
                        maxBytes=self.max_bytes,
                        backupCount=self.backup_count,
                        encoding='utf-8'
                    )
            else:
                file_handler = logging.FileHandler(str(file_path), encoding='utf-8')
            
            file_handler.setLevel(self.level)
            
            if self.file_format == 'json':
                file_handler.setFormatter(JSONFormatter())
            elif self.file_format == 'detailed':
                file_handler.setFormatter(ContextualFormatter(include_context=True))
            else:  # standard
                file_handler.setFormatter(ContextualFormatter(include_context=False))
            
            root_logger.addHandler(file_handler)
        
        # JSON file handler
        if self.enable_json:
            json_path = self.log_dir / self.json_log_file
            
            if self.use_rotation:
                if self.rotation_type == 'time':
                    json_handler = logging.handlers.TimedRotatingFileHandler(
                        str(json_path),
                        when=self.when,
                        interval=self.interval,
                        backupCount=self.backup_count,
                        encoding='utf-8'
                    )
                else:  # size
                    json_handler = logging.handlers.RotatingFileHandler(
                        str(json_path),
                        maxBytes=self.max_bytes,
                        backupCount=self.backup_count,
                        encoding='utf-8'
                    )
            else:
                json_handler = logging.FileHandler(str(json_path), encoding='utf-8')
            
            json_handler.setLevel(self.level)
            json_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(json_handler)
        
        # Set module-specific log levels
        for module, level in self.module_levels.items():
            module_level = level if isinstance(level, int) else getattr(logging, level.upper())
            logging.getLogger(module).setLevel(module_level)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'LoggingConfig':
        """Create LoggingConfig from a dictionary"""
        return cls(**config)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'level': logging.getLevelName(self.level),
            'log_dir': str(self.log_dir),
            'log_file': self.log_file,
            'json_log_file': self.json_log_file,
            'enable_console': self.enable_console,
            'enable_file': self.enable_file,
            'enable_json': self.enable_json,
            'console_format': self.console_format,
            'file_format': self.file_format,
            'max_bytes': self.max_bytes,
            'backup_count': self.backup_count,
            'when': self.when,
            'interval': self.interval,
            'use_rotation': self.use_rotation,
            'rotation_type': self.rotation_type,
            'module_levels': self.module_levels
        }


def configure_logging(
    level: Union[str, int] = logging.INFO,
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    json_log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = False,
    enable_json: bool = False,
    console_format: str = 'standard',
    file_format: str = 'detailed',
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    when: str = 'midnight',
    interval: int = 1,
    use_rotation: bool = True,
    rotation_type: str = 'size',
    module_levels: Optional[Dict[str, Union[str, int]]] = None
) -> LoggingConfig:
    """
    Convenience function to configure logging.
    
    Returns:
        LoggingConfig instance
    """
    config = LoggingConfig(
        level=level,
        log_dir=log_dir,
        log_file=log_file,
        json_log_file=json_log_file,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_json=enable_json,
        console_format=console_format,
        file_format=file_format,
        max_bytes=max_bytes,
        backup_count=backup_count,
        when=when,
        interval=interval,
        use_rotation=use_rotation,
        rotation_type=rotation_type,
        module_levels=module_levels
    )
    config.configure()
    return config


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context
) -> None:
    """
    Log a message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **context: Additional context fields
    """
    logger.log(level, message, extra=context)


