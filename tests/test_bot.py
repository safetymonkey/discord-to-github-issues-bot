import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from src.db.database import setup_database, save_issue_link, get_issue_link, health_check


class TestDatabase:
    """Test cases for database functionality."""
    
    def setup_method(self):
        """Set up test database with temporary file."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Patch the database path for testing
        self.patcher = patch('src.db.database.DATABASE_PATH', self.temp_db_path)
        self.patcher.start()
    
    def teardown_method(self):
        """Clean up test database."""
        self.patcher.stop()
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
    
    def test_setup_database(self):
        """Test database setup creates tables correctly."""
        setup_database()
        
        # Verify the database file was created
        assert os.path.exists(self.temp_db_path)
    
    def test_save_and_get_issue_link(self):
        """Test saving and retrieving issue links."""
        setup_database()
        
        # Test data
        message_id = 123456789
        issue_url = "https://github.com/owner/repo/issues/1"
        issue_id = 1
        
        # Save issue link
        save_issue_link(message_id, issue_url, issue_id)
        
        # Retrieve issue link
        result = get_issue_link(message_id)
        assert result is not None
        assert result[0] == issue_url
        assert result[1] == issue_id
    
    def test_get_nonexistent_issue_link(self):
        """Test retrieving non-existent issue link returns None."""
        setup_database()
        
        result = get_issue_link(999999999)
        assert result is None
    
    def test_duplicate_issue_link_raises_error(self):
        """Test that saving duplicate issue links raises an error."""
        setup_database()
        
        message_id = 123456789
        issue_url = "https://github.com/owner/repo/issues/1"
        issue_id = 1
        
        # Save first time
        save_issue_link(message_id, issue_url, issue_id)
        
        # Try to save again with same message_id
        with pytest.raises(Exception):  # Should raise sqlite3.IntegrityError
            save_issue_link(message_id, issue_url, issue_id)
    
    def test_health_check(self):
        """Test database health check."""
        setup_database()
        
        # Health check should pass with valid database
        assert health_check() is True


import importlib


class TestBotCommands:
    """Test cases for Discord bot commands."""

    @pytest.fixture(autouse=True)
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables for bot command tests."""
        monkeypatch.setenv("DISCORD_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPO_OWNER", "test_owner")
        monkeypatch.setenv("GITHUB_REPO_NAME", "test_repo")
        monkeypatch.setattr("github.Github", Mock())
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = Mock()
        interaction.response = Mock()
        interaction.response.defer = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        interaction.user = Mock()
        interaction.user.id = 12345
        interaction.guild = Mock()
        interaction.guild.name = "Test Guild"
        interaction.channel = Mock()
        interaction.channel.name = "test-channel"
        interaction.channel.fetch_message = AsyncMock()
        return interaction
    
    @pytest.fixture
    def mock_message(self):
        """Create a mock Discord message."""
        message = Mock()
        message.id = 987654321
        message.content = "Test message content"
        message.author = Mock()
        message.author.mention = "@testuser"
        message.author.display_name = "Test User"
        message.jump_url = "https://discord.com/channels/123/456/987654321"
        message.created_at = Mock()
        message.created_at.strftime = Mock(return_value="2023-01-01 12:00:00 UTC")
        message.attachments = []
        return message
    
    @pytest.mark.asyncio
    async def test_create_issue_command_success(self, mock_interaction, mock_message):
        """Test successful issue creation."""
        with patch('src.bot.repo') as mock_repo, \
             patch('src.bot.save_issue_link') as mock_save_link:
            
            # Mock GitHub issue creation
            mock_issue = Mock()
            mock_issue.html_url = "https://github.com/owner/repo/issues/1"
            mock_issue.number = 1
            mock_repo.create_issue.return_value = mock_issue
            
            # Mock message fetching
            mock_interaction.channel.fetch_message.return_value = mock_message
            
            # Import and test the command function
            from src.bot import create_issue
            
            await create_issue.callback(
                mock_interaction,
                "987654321",
                "Test Issue",
                "bug,feature",
                "user1,user2"
            )
            
            # Verify interactions
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.channel.fetch_message.assert_called_once_with(987654321)
            mock_repo.create_issue.assert_called_once()
            mock_save_link.assert_called_once_with(987654321, mock_issue.html_url, mock_issue.number)
            mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_issue_invalid_message_id(self, mock_interaction):
        """Test issue creation with invalid message ID."""
        with patch('src.bot.repo'):
            # Mock message not found
            mock_interaction.channel.fetch_message.side_effect = ValueError("Invalid message ID")
            
            from src.bot import create_issue
            
            await create_issue.callback(
                mock_interaction,
                "invalid",
                "Test Issue"
            )
            
            # Verify error handling
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once_with(
                "Error: Invalid message ID or message not found.", 
                ephemeral=True
            )


class TestContainerFeatures:
    """Test container-specific features."""
    
    def test_database_path_configuration(self):
        """Test that database path can be configured via environment."""
        custom_path = "/custom/path/test.db"
        
        with patch.dict(os.environ, {'DATABASE_PATH': custom_path}):
            import src.db.database
            importlib.reload(src.db.database)
            from src.db.database import get_database_path
            
            # Mock the directory creation to avoid filesystem operations
            with patch('pathlib.Path.mkdir'):
                path = get_database_path()
                assert path == custom_path
    
    def test_environment_variable_validation(self):
        """Test that missing environment variables are detected."""
        # This would require importing the bot module which checks env vars
        # In a real test, you'd mock the environment and test the validation
        pass


if __name__ == "__main__":
    pytest.main([__file__])