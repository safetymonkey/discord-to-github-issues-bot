import os
import sys
import signal
import asyncio
import logging
import discord
from discord.ext import commands
from github import Github
from dotenv import load_dotenv

from .db.database import setup_database, save_issue_link, health_check

# Load environment variables (only for local development)
if os.path.exists('.env'):
    load_dotenv()

# Configure logging for container environments (structured logging to stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME')

# Validate required environment variables
required_vars = {
    'DISCORD_TOKEN': DISCORD_TOKEN,
    'GITHUB_TOKEN': GITHUB_TOKEN,
    'GITHUB_REPO_OWNER': GITHUB_REPO_OWNER,
    'GITHUB_REPO_NAME': GITHUB_REPO_NAME
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Initialize Discord bot with intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Initialize PyGithub client
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    logger.info(f"Connected to GitHub repository: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
except Exception as e:
    logger.error(f"Failed to connect to GitHub repository: {e}")
    sys.exit(1)

# Global shutdown flag for graceful shutdown
shutdown_flag = False


class GracefulShutdown:
    """Handles graceful shutdown for container environments."""
    
    def __init__(self, bot):
        self.bot = bot
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigint)
    
    def _handle_sigterm(self, signum, frame):
        logger.info("Received SIGTERM, initiating graceful shutdown...")
        asyncio.create_task(self._shutdown())
    
    def _handle_sigint(self, signum, frame):
        logger.info("Received SIGINT, initiating graceful shutdown...")
        asyncio.create_task(self._shutdown())
    
    async def _shutdown(self):
        global shutdown_flag
        shutdown_flag = True
        logger.info("Closing Discord bot connection...")
        await self.bot.close()


@bot.event
async def on_ready():
    """
    Event handler when the bot is connected and ready.
    Sets up the database and syncs slash commands.
    """
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    
    try:
        setup_database()
        logger.info("Database setup completed")
        
        await tree.sync()
        logger.info("Slash commands synced successfully")
        
        logger.info("Bot is ready and operational")
    except Exception as e:
        logger.error(f"Error during bot initialization: {e}")
        await bot.close()
        sys.exit(1)


@tree.command(name="create-issue", description="Create a GitHub issue from a Discord message.")
@discord.app_commands.describe(
    message_id="The ID of the Discord message to use for the issue body.",
    title="The title of the GitHub issue.",
    labels="A comma-separated list of labels to apply (e.g., 'bug,feature').",
    assignees="A comma-separated list of GitHub usernames to assign (e.g., 'user1,user2')."
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_issue(interaction: discord.Interaction, message_id: str, title: str, labels: str = None, assignees: str = None):
    """
    Slash command to create a GitHub issue from a Discord message.
    Enhanced with better error handling and logging for container environments.
    """
    await interaction.response.defer(ephemeral=True)
    
    try:
        logger.info(f"Creating issue request from user {interaction.user.id} for message {message_id}")
        
        # Fetch the Discord message
        try:
            channel = interaction.channel
            message = await channel.fetch_message(int(message_id))
        except (ValueError, discord.NotFound) as e:
            error_msg = "Error: Invalid message ID or message not found."
            logger.warning(f"Message fetch failed: {e}")
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        # Prepare labels and assignees
        issue_labels = ["user-reported"]
        if labels:
            issue_labels.extend([label.strip() for label in labels.split(',') if label.strip()])
        
        issue_assignees = []
        if assignees:
            issue_assignees = [assignee.strip() for assignee in assignees.split(',') if assignee.strip()]
        
        # Create issue body with Discord context
        issue_body = (
            f"**Reported by:** {message.author.mention} ({message.author.display_name})\n"
            f"**Discord Server:** {interaction.guild.name if interaction.guild else 'DM'}\n"
            f"**Channel:** {channel.name if hasattr(channel, 'name') else 'DM'}\n"
            f"**Link to Discord message:** {message.jump_url}\n"
            f"**Message created:** {message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"**Original message content:**\n{message.content if message.content else '*No text content*'}"
        )
        
        # Add attachments info if present
        if message.attachments:
            issue_body += f"\n\n**Attachments ({len(message.attachments)}):**\n"
            for attachment in message.attachments:
                issue_body += f"- [{attachment.filename}]({attachment.url})\n"
        
        # Create the GitHub issue
        try:
            new_issue = repo.create_issue(
                title=title,
                body=issue_body,
                labels=issue_labels,
                assignees=issue_assignees
            )
            
            # Save the link to the database
            save_issue_link(message.id, new_issue.html_url, new_issue.number)
            
            success_msg = f"✅ Successfully created GitHub issue: {new_issue.html_url}"
            logger.info(f"Issue created successfully: #{new_issue.number} for message {message_id}")
            await interaction.followup.send(success_msg, ephemeral=False)
            
        except Exception as github_error:
            error_msg = f"Failed to create GitHub issue: {str(github_error)}"
            logger.error(f"GitHub API error: {github_error}")
            await interaction.followup.send(error_msg, ephemeral=True)
            
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(f"Unexpected error in create_issue command: {e}")
        await interaction.followup.send(error_msg, ephemeral=True)


@create_issue.error
async def on_create_issue_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """
    Error handler for the /create-issue command.
    """
    if isinstance(error, discord.app_commands.MissingPermissions):
        error_msg = "❌ You do not have administrator permissions to use this command."
        logger.warning(f"Permission denied for user {interaction.user.id}")
    else:
        error_msg = f"❌ Command error: {str(error)}"
        logger.error(f"Command error: {error}")
    
    # Handle both deferred and non-deferred interactions
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


@tree.command(name="health", description="Check bot health status (Admin only)")
@discord.app_commands.checks.has_permissions(administrator=True)
async def health_command(interaction: discord.Interaction):
    """
    Health check command for container monitoring.
    """
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Check database health
        db_healthy = health_check()
        
        # Check GitHub API connection
        try:
            repo.get_contents("README.md")  # Simple API test
            github_healthy = True
        except Exception:
            github_healthy = False
        
        status = "🟢 Healthy" if db_healthy and github_healthy else "🔴 Unhealthy"
        details = (
            f"**Bot Health Status:** {status}\n"
            f"**Database:** {'✅ Connected' if db_healthy else '❌ Error'}\n"
            f"**GitHub API:** {'✅ Connected' if github_healthy else '❌ Error'}\n"
            f"**Bot User:** {bot.user.name}#{bot.user.discriminator}\n"
            f"**Repository:** {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
        )
        
        await interaction.followup.send(details, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        await interaction.followup.send(f"❌ Health check failed: {str(e)}", ephemeral=True)


async def main():
    """
    Main function to run the bot with graceful shutdown handling.
    """
    # Set up graceful shutdown
    shutdown_handler = GracefulShutdown(bot)
    
    try:
        logger.info("Starting Discord bot...")
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
        sys.exit(1)
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)