import discord
import requests
import logging
from django.contrib.auth.models import User
from accounts.models import UserProfile

logger = logging.getLogger(__name__)


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
    """Start job search via Django/n8n integration"""
    try:
        # Update status
        await update_search_status(message, "🔍 Searching job platforms...", 0xffc107)

        # Get or create default search config
        user = User.objects.get(id=user_id)
        from jobs.models import JobSearchConfig

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

        # Trigger job search via Django view
        search_data = {
            'user_id': user_id,
            'config_id': config.id,
            'job_categories': categories,
            'target_locations': config.target_locations,
            'salary_min': config.salary_min,
            'salary_max': config.salary_max
        }

        await update_search_status(message, "📄 Generating documents...", 0x17a2b8)

        # Simulate job search completion (in real implementation, this would trigger n8n)

        result = simulate_job_search.delay(config.id)

        # Wait for completion
        import asyncio
        await asyncio.sleep(3)

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