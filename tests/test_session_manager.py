"""
Tests for session management functionality
"""

import pytest
from crawlit.utils.session_manager import SessionManager


class TestSessionManager:
    """Test cases for SessionManager class"""
    
    def test_sync_session_creation(self):
        """Test synchronous session creation"""
        manager = SessionManager(user_agent="test-agent/1.0")
        session = manager.get_sync_session()
        
        assert session is not None
        assert session.headers['User-Agent'] == "test-agent/1.0"
    
    def test_session_reuse(self):
        """Test that session is reused"""
        manager = SessionManager()
        session1 = manager.get_sync_session()
        session2 = manager.get_sync_session()
        
        assert session1 is session2
    
    def test_cookie_management(self):
        """Test cookie management"""
        manager = SessionManager(cookies={'test': 'value'})
        session = manager.get_sync_session()
        
        assert 'test' in session.cookies
        assert session.cookies['test'] == 'value'
    
    def test_add_cookie(self):
        """Test adding cookies"""
        manager = SessionManager()
        manager.add_cookie('new_cookie', 'new_value')
        
        cookies = manager.get_cookies()
        assert 'new_cookie' in cookies
        assert cookies['new_cookie'] == 'new_value'
    
    def test_context_manager(self):
        """Test context manager usage"""
        with SessionManager() as manager:
            session = manager.get_sync_session()
            assert session is not None
        
        # Session should be closed after context exit
        assert manager._sync_session is None
    
    @pytest.mark.asyncio
    async def test_async_session_creation(self):
        """Test asynchronous session creation"""
        manager = SessionManager(user_agent="test-agent/1.0")
        session = await manager.get_async_session()
        
        assert session is not None
        assert not session.closed
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager usage"""
        async with SessionManager() as manager:
            session = await manager.get_async_session()
            assert session is not None
        
        # Session should be closed after context exit
        assert manager._async_session is None or manager._async_session.closed

