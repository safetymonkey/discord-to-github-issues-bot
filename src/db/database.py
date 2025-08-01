import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Container-friendly database path configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data/bot_data.db')


def get_database_path():
    """
    Returns the database path, ensuring the directory exists.
    Container-optimized to handle volume mounts.
    """
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def setup_database():
    """
    Creates the SQLite database and the issue_links table if they don't exist.
    Container-optimized with proper error handling and logging.
    """
    db_path = get_database_path()
    logger.info(f"Setting up database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issue_links (
                discord_message_id INTEGER PRIMARY KEY,
                github_issue_url TEXT NOT NULL,
                github_issue_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        logger.info("Database setup completed successfully")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
        raise
    finally:
        conn.close()


def save_issue_link(discord_message_id, github_issue_url, github_issue_id):
    """
    Saves the link between a Discord message and a GitHub issue to the database.
    Enhanced with better error handling and logging for container environments.
    """
    db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO issue_links (discord_message_id, github_issue_url, github_issue_id) VALUES (?, ?, ?)",
            (discord_message_id, github_issue_url, github_issue_id)
        )
        conn.commit()
        logger.info(f"Saved issue link: Discord message {discord_message_id} -> GitHub issue #{github_issue_id}")
    except sqlite3.IntegrityError as e:
        logger.warning(f"Issue link already exists for Discord message {discord_message_id}: {e}")
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error saving issue link: {e}")
        raise
    finally:
        conn.close()


def get_issue_link(discord_message_id):
    """
    Retrieves the GitHub issue link for a given Discord message ID.
    """
    db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT github_issue_url, github_issue_id FROM issue_links WHERE discord_message_id = ?",
            (discord_message_id,)
        )
        result = cursor.fetchone()
        return result if result else None
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving issue link: {e}")
        raise
    finally:
        conn.close()


def health_check():
    """
    Performs a database health check for container monitoring.
    """
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False