import discord
from discord.ext import commands
import requests
import json
import os
import asyncio
import sys
from pathlib import Path
import logging

# Add the Django project to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
import django

django.setup()

# Import Django models after setup
from django.contrib.auth.models import User
from jobs.models import JobApplication, JobSearchConfig
from accounts.models import UserProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DJANGO_API_URL = os.getenv('DJANGO_API_URL', 'http://localhost:8000')
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')

    # Update bot status
    activity = discord.Activity(type=discord.ActivityType.watching, name="for job searches | !help")
    await bot.change_presence(activity=activity)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❓ Unknown Command",
            description="Use `!help` to see available commands",
            color=0xdc3545
        )
        await ctx.send(embed=embed)
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred. Please try again.")


@bot.command(name='search')
async def job_search_command(ctx, *, query=None):
    """
    Search for jobs using Discord bot
    Usage: !search data science, machine learning, python
    """
    if not query:
        embed = discord.Embed(
            title="🔍 Job Search Help",
            description="""Use: `!search <job categories>`

**Examples:**
• `!search data science, machine learning`
• `!search python developer, django`
• `!search software engineer, backend`

**Available Categories:**
Data Science, Machine Learning, Python Developer, Django Developer, 
Software Engineer, Data Analyst, AI Engineer, Backend Developer""",
            color=0x007bff
        )
        await ctx.send(embed=embed)
        return

    # Parse job categories
    categories = [cat.strip().lower().replace(' ', '_') for cat in query.split(',')]

    # Get or create user profile
    user_id = await get_or_create_user(ctx.author)
    if not user_id:
        await ctx.send("❌ Error creating user profile. Please try again.")
        return

    # Create progress embed
    embed = discord.Embed(
        title="🤖 Starting Job Search",
        description=f"Searching for jobs in: {', '.join([cat.replace('_', ' ').title() for cat in categories])}",
        color=0x28a745
    )
    embed.add_field(name="📊 Categories", value="\n".join([f"• {cat.replace('_', ' ').title()}" for cat in categories]),
                    inline=True)
    embed.add_field(name="⏰ Status", value="🔍 Initializing search...", inline=True)
    embed.add_field(name="📍 Locations", value="Remote, Toronto, Vancouver", inline=True)
    embed.set_footer(text="This may take 2-3 minutes...")

    message = await ctx.send(embed=embed)

    # Start job search
    try:
        result = await start_job_search(user_id, categories, message, ctx)
        if result:
            await update_search_status(message, "✅ Search completed! Check your dashboard.", 0x28a745)
        else:
            await update_search_status(message, "❌ Search failed! Please try again.", 0xdc3545)
    except Exception as e:
        logger.error(f"Job search error: {e}")
        await update_search_status(message, "❌ Search error! Please try again.", 0xdc3545)


# Helper functions
async def get_user_by_discord_id(discord_id):
    """Get Django user by Discord ID"""
    try:
        profile = UserProfile.objects.filter(discord_user_id=str(discord_id)).first()
        return profile.user if profile else None
    except Exception as e:
        logger.error(f"Error getting user by Discord ID: {e}")
        return None


async def get_or_create_user(discord_user):
    """Get or create Django user from Discord user"""
    try:
        # Check if user exists
        existing_user = await get_user_by_discord_id(discord_user.id)
        if existing_user:
            return existing_user.id

        # Create new user
        username = f"discord_{discord_user.id}"
        email = f"{discord_user.name}@discord.user"

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=discord_user.display_name or discord_user.name
        )

        # Create profile
        UserProfile.objects.create(
            user=user,
            discord_user_id=str(discord_user.id)
        )

        logger.info(f"Created new user for Discord ID: {discord_user.id}")
        return user.id

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None


async def start_job_search(user_id, categories, message, ctx):
    """Start job search via Django integration"""
    try:
        # Update status
        await update_search_status(message, "🔍 Searching job platforms...", 0xffc107)

        # Get or create default search config
        user = User.objects.get(id=user_id)

        config, created = JobSearchConfig.objects.get_or_create(
            user=user,
            config_name="Discord Bot Search",
            defaults={
                'job_categories': categories,
                'target_locations': ['remote', 'toronto_on', 'vancouver_bc'],
                'remote_preference': 'remote',
                'salary_min': 60000,
                'salary_max': 150000,
                'auto_follow_up_enabled': True,
                'is_active': True
            }
        )

        # Update categories for existing config
        config.job_categories = categories
        config.save()

        await update_search_status(message, "📄 Generating sample jobs...", 0x17a2b8)

        # Create sample jobs for demo (replace with real n8n integration)
        from jobs.management.commands.create_sample_jobs import Command
        sample_command = Command()

        # Simulate delay
        await asyncio.sleep(2)

        await update_search_status(message, "✅ Search completed! Check your dashboard.", 0x28a745)

        # Add dashboard link
        embed = message.embeds[0]
        embed.add_field(
            name="🌐 View Results",
            value=f"[Dashboard]({DJANGO_API_URL}/dashboard/) • [Applications]({DJANGO_API_URL}/jobs/applications/)",
            inline=False
        )
        await message.edit(embed=embed)

        return True

    except Exception as e:
        logger.error(f"Job search error: {e}")
        return False


async def update_search_status(message, status, color):
    """Update job search status embed"""
    try:
        embed = message.embeds[0]
        embed.color = color

        # Update status field
        for i, field in enumerate(embed.fields):
            if field.name == "⏰ Status":
                embed.set_field_at(i, name="⏰ Status", value=status, inline=True)
                break

        embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=embed)
    except Exception as e:
        logger.error(f"Error updating status: {e}")


def create_error_embed(title, description):
    """Create a standardized error embed"""
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xdc3545
    )


@bot.command(name='help')
async def help_command(ctx):
    """Show comprehensive help information"""
    embed = discord.Embed(
        title="🤖 Job Automation Bot Help",
        description="I help you automate your job search process! Here are all available commands:",
        color=0x007bff
    )

    # Job Search Commands
    embed.add_field(
        name="🔍 **Job Search Commands**",
        value="""
`!search <categories>` - Search for jobs
`!configs` - View saved search configurations  
`!status` - Check your application status

**Example:** `!search data science, python, machine learning`
        """,
        inline=False
    )

    # Follow-up Commands
    embed.add_field(
        name="📧 **Follow-up Commands**",
        value="""
`!followup` - Send bulk follow-up emails
`!followup <company>` - Send follow-up to specific company
`!due` - Check follow-ups that are due today
        """,
        inline=False
    )

    # Profile Commands
    embed.add_field(
        name="👤 **Profile Commands**",
        value="""
`!profile` - View your profile information
`!stats` - View your job search statistics
        """,
        inline=False
    )

    # Quick Examples
    embed.add_field(
        name="💡 **Quick Examples**",
        value="""
• `!search python developer, django` - Find Python/Django jobs
• `!followup TechCorp` - Send follow-up to TechCorp
• `!due` - Check what follow-ups are due today
• `!stats` - See your success metrics
        """,
        inline=False
    )

    # Web Dashboard
    embed.add_field(
        name="🌐 **Web Dashboard**",
        value=f"[Visit Dashboard]({DJANGO_API_URL}/dashboard/) for full features and document downloads",
        inline=False
    )

    # Tips
    embed.add_field(
        name="🎯 **Pro Tips**",
        value="""
• Complete your profile on the web dashboard for better results
• Use specific job categories for more targeted searches
• Enable auto-follow-up to increase response rates
• Check `!due` regularly to stay on top of follow-ups
        """,
        inline=False
    )

    embed.set_footer(text="Use !help <command> for detailed help on specific commands")

    await ctx.send(embed=embed)


# Run the bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Discord bot token not found. Set DISCORD_BOT_TOKEN environment variable.")
        exit(1)

    bot.run(BOT_TOKEN)