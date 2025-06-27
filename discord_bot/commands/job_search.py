import discord
from discord.ext import commands
import requests
import asyncio
import logging

logger = logging.getLogger(__name__)


@bot.command(name='status')
async def status_command(ctx):
    """Check your job application status"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Profile Not Found",
                description="Please use `!search` first to create your profile, or visit the web dashboard.",
                color=0xdc3545
            )
            embed.add_field(
                name="🌐 Web Dashboard",
                value=f"[Create Profile]({DJANGO_API_URL}/accounts/register/)",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        # Get user applications
        applications = JobApplication.objects.filter(user=user).order_by('-created_at')[:15]

        if not applications:
            embed = discord.Embed(
                title="📋 Application Status",
                description="No applications found yet.",
                color=0x6c757d
            )
            embed.add_field(
                name="🔍 Start Searching",
                value="Use `!search <categories>` to find jobs!",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        # Create status embed
        embed = discord.Embed(
            title="📋 Your Recent Job Applications",
            description=f"Showing {len(applications)} most recent applications",
            color=0x007bff
        )

        # Group by status
        status_groups = {}
        for app in applications:
            status = app.application_status
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(app)

        status_emojis = {
            'found': '🔍 Found',
            'applied': '📧 Applied',
            'responded': '📞 Responded',
            'interview': '🎯 Interview',
            'offer': '🎉 Offer',
            'rejected': '❌ Rejected'
        }

        for status, apps in status_groups.items():
            emoji_status = status_emojis.get(status, f"📋 {status.title()}")
            app_list = []

            for app in apps[:3]:  # Show max 3 per status
                app_list.append(f"• **{app.job_title}** at {app.company_name}")

            if len(apps) > 3:
                app_list.append(f"... and {len(apps) - 3} more")

            embed.add_field(
                name=f"{emoji_status} ({len(apps)})",
                value="\n".join(app_list) if app_list else "None",
                inline=False
            )

        embed.add_field(
            name="🌐 Full Details",
            value=f"[View Dashboard]({DJANGO_API_URL}/jobs/applications/)",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Status command error: {e}")
        await ctx.send("❌ Error checking status. Please try again.")


@bot.command(name='configs')
async def configs_command(ctx):
    """View your saved search configurations"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            await ctx.send("❌ Profile not found. Use `!search` to get started.")
            return

        configs = JobSearchConfig.objects.filter(user=user, is_active=True)

        if not configs:
            embed = discord.Embed(
                title="⚙️ Search Configurations",
                description="No search configurations found.",
                color=0x6c757d
            )
            embed.add_field(
                name="➕ Create Configuration",
                value=f"[Web Dashboard]({DJANGO_API_URL}/jobs/search-config/)",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="⚙️ Your Search Configurations",
            description=f"You have {len(configs)} active configurations",
            color=0x007bff
        )

        for config in configs[:5]:  # Show max 5
            categories = ', '.join(config.job_categories[:3])
            if len(config.job_categories) > 3:
                categories += f" (+{len(config.job_categories) - 3} more)"

            embed.add_field(
                name=f"📋 {config.config_name}",
                value=f"**Categories:** {categories}\n**Last Search:** {config.last_search_date.strftime('%b %d') if config.last_search_date else 'Never'}",
                inline=False
            )

        embed.add_field(
            name="🔍 Use Configuration",
            value="Use `!search` with categories to start a new search",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Configs command error: {e}")
        await ctx.send("❌ Error fetching configurations.")