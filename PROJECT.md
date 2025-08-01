Instructions for Building Discord-to-GitHub Issue BotProject Goal: Create a Python-based Discord bot that allows server administrators to generate GitHub issues from Discord messages via a slash command. The bot should use a local SQLite database to link Discord messages to GitHub issues and manage its Python environment using uv.File Structure: Create the following directory and file structure./discord-github-bot/
├── src/
│   ├── db/
│   │   └── database.py
│   └── bot.py
├── tests/
│   ├── __init__.py
│   └── test_bot.py
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
File Contents:Create each file with the following content.File: src/bot.py# src/bot.py
# This is the main file for your Discord bot. It handles the bot's events,
# slash commands, and integration with the GitHub API.

import os
import discord
from discord.ext import commands
from github import Github
from dotenv import load_dotenv

# Import database functions from the local db module
from .db.database import setup_database, save_issue_link

# Load environment variables from a .env file
load_dotenv()

# --- Configuration and Initialization ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME')

# Check if environment variables are set
if not all([DISCORD_TOKEN, GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
    print("Error: Please set all required environment variables.")
    exit()

# Initialize Discord bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Initialize PyGithub client
g = Github(GITHUB_TOKEN)
repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")

# --- Discord Bot Events and Commands ---
@bot.event
async def on_ready():
    """
    Prints a message when the bot is connected and sets up the database.
    """
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    setup_database()
    await tree.sync() # Syncs the slash commands with Discord

@tree.command(name="create-issue", description="Create a GitHub issue from a message.")
@discord.app_commands.describe(
    message_id="The ID of the Discord message to use for the issue body.",
    title="The title of the GitHub issue.",
    labels="A comma-separated list of labels to apply (e.g., 'bug,feature').",
    assignees="A comma-separated list of GitHub usernames to assign (e.g., 'user1,user2')."
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_issue(interaction: discord.Interaction, message_id: str, title: str, labels: str = None, assignees: str = None):
    """
    Slash command to create a GitHub issue.
    """
    await interaction.response.defer(ephemeral=True)

    try:
        # Fetch the message
        channel = interaction.channel
        message = await channel.fetch_message(message_id)
        
        # Prepare labels and assignees
        issue_labels = ["user-reported"]
        if labels:
            issue_labels.extend([label.strip() for label in labels.split(',')])

        issue_assignees = [assignee.strip() for assignee in assignees.split(',')] if assignees else []
        
        # Create issue body
        issue_body = (
            f"**Reported by:** {message.author.mention}\n"
            f"**Link to Discord message:** {message.jump_url}\n\n"
            f"**Original message content:**\n{message.content}"
        )

        # Create the issue on GitHub
        new_issue = repo.create_issue(
            title=title,
            body=issue_body,
            labels=issue_labels,
            assignees=issue_assignees
        )

        # Save the link to the database
        save_issue_link(message.id, new_issue.html_url, new_issue.number)

        await interaction.followup.send(
            f"Successfully created GitHub issue: {new_issue.html_url}",
            ephemeral=False
        )

    except discord.NotFound:
        await interaction.followup.send("Error: Message not found. Please provide a valid message ID.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


@create_issue.error
async def on_create_issue_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """
    Handles errors for the /create-issue command.
    """
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)


# --- Run the bot ---
bot.run(DISCORD_TOKEN)
File: src/db/database.py# src/db/database.py
# This module handles all database-related functions for the bot.

import sqlite3

DATABASE_NAME = "bot_data.db"

def setup_database():
    """
    Creates the SQLite database and the issue_links table if they don't exist.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issue_links (
            discord_message_id INTEGER PRIMARY KEY,
            github_issue_url TEXT NOT NULL,
            github_issue_id INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def save_issue_link(discord_message_id, github_issue_url, github_issue_id):
    """
    Saves the link between a Discord message and a GitHub issue to the database.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO issue_links (discord_message_id, github_issue_url, github_issue_id) VALUES (?, ?, ?)",
            (discord_message_id, github_issue_url, github_issue_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()
File: requirements.txtdiscord.py
PyGithub
python-dotenv
File: .env.exampleDISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
GITHUB_TOKEN="YOUR_GITHUB_PERSONAL_ACCESS_TOKEN_HERE"
GITHUB_REPO_OWNER="the-owner-of-the-github-repo"
GITHUB_REPO_NAME="the-name-of-the-github-repo"
File: .gitignore# Environment variables
.env

# Python artifacts
__pycache__/
*.pyc
*.pyo
*~
.pytest_cache/
.tox/
.venv/
env/
venv/
File: README.md# Discord-to-GitHub Issue Bot

This is a simple Discord bot that allows server administrators to create GitHub issues directly from Discord messages using slash commands.

## Features

- Create GitHub issues from a Discord message.
- Specify issue title, labels, and assignees via slash command options.
- Automatically applies a "user-reported" label to every issue.
- Stores a link between the Discord message and the created GitHub issue in a local SQLite database.

## Prerequisites

- Python 3.8 or higher
- `uv` for environment management
- A Discord Bot Token
- A GitHub Personal Access Token with `repo` permissions
- A GitHub repository where the issues will be created

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-url.git
    cd discord-github-bot
    ```

2.  **Create and activate a virtual environment with `uv`:**
    ```bash
    uv venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install the required dependencies with `uv`:**
    ```bash
    uv pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    - Rename `.env.example` to `.env`.
    - Fill in the values for `DISCORD_TOKEN`, `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, and `GITHUB_REPO_NAME`.

5.  **Run the bot:**
    ```bash
    python3 src/bot.py
    ```

The bot will connect to your Discord server and set up the `/create-issue` slash command. You can then use it in any channel where the bot has permission to see messages.
