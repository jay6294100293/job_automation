import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the Discord bot"""

    # Check for bot token
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ DISCORD_BOT_TOKEN environment variable not set")
        logger.error("Please add your Discord bot token to the .env file:")
        logger.error("DISCORD_BOT_TOKEN=your-bot-token-here")
        sys.exit(1)

    # Check if Django is available
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
        import django
        django.setup()
        logger.info("✅ Django setup completed")
    except Exception as e:
        logger.error(f"❌ Django setup failed: {e}")
        logger.error("Make sure you're running this from the project root directory")
        sys.exit(1)

    # Import and run the bot
    try:
        from discord_bot.bot import bot
        logger.info("🤖 Starting Discord bot...")
        logger.info("Bot will be available in your Discord server")
        logger.info("Use !help to see available commands")

        bot.run(bot_token)

    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()