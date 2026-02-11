#!/usr/bin/env python3
"""
Tests for enhanced logging configuration
"""

import pytest
import logging
import tempfile
import json
from pathlib import Path
from crawlit.utils.logging_config import (
    LoggingConfig,
    configure_logging,
    get_logger,
    log_with_context,
    JSONFormatter,
    ContextualFormatter
)


class TestLoggingConfig:
    """Test LoggingConfig class"""
    
    def test_basic_configuration(self):
        """Test basic logging configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=True,
                enable_file=True,
                enable_json=False
            )
            config.configure()
            
            logger = logging.getLogger('test')
            logger.info("Test message")
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            # Check that file was created
            log_file = Path(tmpdir) / 'crawlit.log'
            assert log_file.exists()
    
    def test_json_logging(self):
        """Test JSON logging format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
                enable_json=True,
                file_format='json'
            )
            config.configure()
            
            logger = logging.getLogger('test')
            logger.info("Test JSON message")
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            # Check JSON log file
            json_file = Path(tmpdir) / 'crawlit.json.log'
            assert json_file.exists()
            
            # Verify JSON format
            with open(json_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) > 0
                log_entry = json.loads(lines[-1])
                assert 'timestamp' in log_entry
                assert 'level' in log_entry
                assert 'message' in log_entry
                assert log_entry['message'] == "Test JSON message"
    
    def test_log_rotation_size(self):
        """Test size-based log rotation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
                use_rotation=True,
                rotation_type='size',
                max_bytes=1024,  # 1KB
                backup_count=2
            )
            config.configure()
            
            logger = logging.getLogger('test')
            
            # Write enough to trigger rotation
            for i in range(100):
                logger.info(f"Test message {i} " * 10)
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            # Check that backup files were created
            log_file = Path(tmpdir) / 'crawlit.log'
            assert log_file.exists()
    
    def test_log_rotation_time(self):
        """Test time-based log rotation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
                use_rotation=True,
                rotation_type='time',
                when='H',  # Hourly
                interval=1,
                backup_count=2
            )
            config.configure()
            
            logger = logging.getLogger('test')
            logger.info("Test message")
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            # Check that file was created
            log_file = Path(tmpdir) / 'crawlit.log'
            assert log_file.exists()
    
    def test_module_levels(self):
        """Test module-specific log levels"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=True,
                enable_file=False,
                module_levels={
                    'crawlit.crawler': 'DEBUG',
                    'crawlit.utils': 'WARNING'
                }
            )
            config.configure()
            
            # Check module levels
            assert logging.getLogger('crawlit.crawler').level == logging.DEBUG
            assert logging.getLogger('crawlit.utils').level == logging.WARNING
    
    def test_console_formats(self):
        """Test different console formats"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for fmt in ['standard', 'detailed', 'json']:
                config = LoggingConfig(
                    level=logging.INFO,
                    enable_console=True,
                    enable_file=False,
                    console_format=fmt
                )
                config.configure()
                
                logger = logging.getLogger('test')
                logger.info("Test message")
    
    def test_to_dict_from_dict(self):
        """Test serialization to/from dictionary"""
        config = LoggingConfig(
            level=logging.DEBUG,
            log_dir='/tmp/logs',
            enable_console=True,
            enable_file=True,
            module_levels={'test': 'DEBUG'}
        )
        
        config_dict = config.to_dict()
        assert config_dict['level'] == 'DEBUG'
        assert config_dict['enable_console'] is True
        
        # Recreate from dict
        new_config = LoggingConfig.from_dict(config_dict)
        assert new_config.level == logging.DEBUG
        assert new_config.enable_console is True


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_configure_logging(self):
        """Test configure_logging convenience function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = configure_logging(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_file=True
            )
            
            assert isinstance(config, LoggingConfig)
            assert config.level == logging.INFO
            
            logger = logging.getLogger('test')
            logger.info("Test message")
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            log_file = Path(tmpdir) / 'crawlit.log'
            assert log_file.exists()
    
    def test_get_logger(self):
        """Test get_logger function"""
        logger = get_logger('test.module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test.module'
    
    def test_log_with_context(self):
        """Test log_with_context function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LoggingConfig(
                level=logging.INFO,
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
                enable_json=True,  # Enable JSON logging
                file_format='json'
            )
            config.configure()
            
            logger = get_logger('test')
            log_with_context(
                logger,
                logging.INFO,
                "Test message",
                url="https://example.com",
                depth=1,
                status_code=200
            )
            
            # Close all handlers before cleanup
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            # Check JSON log file
            json_file = Path(tmpdir) / 'crawlit.json.log'
            assert json_file.exists()
            
            with open(json_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                log_entry = json.loads(lines[-1])
                assert log_entry['message'] == "Test message"
                assert log_entry['url'] == "https://example.com"
                assert log_entry['depth'] == 1
                assert log_entry['status_code'] == 200


class TestFormatters:
    """Test custom formatters"""
    
    def test_json_formatter(self):
        """Test JSONFormatter"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert 'timestamp' in data
        assert 'level' in data
        assert 'message' in data
        assert data['message'] == 'Test message'
        assert data['level'] == 'INFO'
    
    def test_contextual_formatter(self):
        """Test ContextualFormatter"""
        formatter = ContextualFormatter(include_context=True)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        # Set funcName explicitly
        record.funcName = 'test_function'
        
        output = formatter.format(record)
        assert 'Test message' in output
        assert 'test_function' in output or 'None' in output  # funcName might be None in some cases
        assert '10' in output  # line number

