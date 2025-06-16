import discord
from discord.ext import commands
import logging

from accounts.models import UserProfile
from discord_bot.bot import DJANGO_API_URL, get_user_by_discord_id, bot
from jobs.models import JobApplication

logger = logging.getLogger(__name__)


@bot.command(name='profile')
async def profile_command(ctx):
    """View your profile information"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            embed = discord.Embed(
                title="❌ Profile Not Found",
                description="You don't have a profile yet.",
                color=0xdc3545
            )
            embed.add_field(
                name="🚀 Get Started",
                value=f"[Create Profile]({DJANGO_API_URL}/accounts/register/)",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            await ctx.send("❌ Profile data not found. Please complete your profile on the web dashboard.")
            return

        embed = discord.Embed(
            title=f"👤 Profile: {user.get_full_name() or user.username}",
            color=0x007bff
        )

        # Profile completion
        completion = profile.profile_completion_percentage
        completion_bar = "█" * (completion // 10) + "░" * (10 - completion // 10)
        embed.add_field(
            name="📊 Profile Completion",
            value=f"{completion_bar} {completion}%",
            inline=False
        )

        # Basic info
        embed.add_field(name="📧 Email", value=user.email, inline=True)
        embed.add_field(name="📍 Location", value=profile.location or "Not set", inline=True)
        embed.add_field(name="💼 Experience", value=f"{profile.years_experience or 0} years", inline=True)

        # Current role
        if profile.current_job_title:
            current_role = f"{profile.current_job_title}"
            if profile.current_company:
                current_role += f" at {profile.current_company}"
            embed.add_field(name="🎯 Current Role", value=current_role, inline=False)

        # Skills
        if profile.key_skills:
            skills = ", ".join(profile.key_skills[:8])
            if len(profile.key_skills) > 8:
                skills += f" (+{len(profile.key_skills) - 8} more)"
            embed.add_field(name="🛠️ Key Skills", value=skills, inline=False)

        # Job preferences
        if profile.preferred_salary_min and profile.preferred_salary_max:
            salary_range = f"${profile.preferred_salary_min:,} - ${profile.preferred_salary_max:,}"
            embed.add_field(name="💰 Salary Range", value=salary_range, inline=True)

        embed.add_field(name="🏠 Work Type", value=profile.get_work_type_preference_display(), inline=True)

        # Action buttons
        embed.add_field(
            name="🌐 Actions",
            value=f"[Edit Profile]({DJANGO_API_URL}/accounts/profile/) • [Dashboard]({DJANGO_API_URL}/dashboard/)",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Profile command error: {e}")
        await ctx.send("❌ Error fetching profile.")


@bot.command(name='stats')
async def stats_command(ctx):
    """View your job search statistics"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            await ctx.send("❌ Profile not found.")
            return

        # Get statistics
        applications = JobApplication.objects.filter(user=user)
        total_apps = applications.count()

        if total_apps == 0:
            await ctx.send("📊 No statistics yet. Start by using `!search` to find jobs!")
            return

        # Calculate stats
        applied_count = applications.filter(application_status='applied').count()
        responded_count = applications.filter(application_status__in=['responded', 'interview', 'offer']).count()
        interview_count = applications.filter(application_status='interview').count()
        offer_count = applications.filter(application_status='offer').count()

        response_rate = (responded_count / applied_count * 100) if applied_count > 0 else 0

        embed = discord.Embed(
            title="📊 Your Job Search Statistics",
            color=0x17a2b8
        )

        embed.add_field(name="📋 Total Applications", value=str(total_apps), inline=True)
        embed.add_field(name="📧 Applied", value=str(applied_count), inline=True)
        embed.add_field(name="📞 Responses", value=str(responded_count), inline=True)
        embed.add_field(name="🎯 Interviews", value=str(interview_count), inline=True)
        embed.add_field(name="🎉 Offers", value=str(offer_count), inline=True)
        embed.add_field(name="📈 Response Rate", value=f"{response_rate:.1f}%", inline=True)

        # Recent activity
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_apps = applications.filter(created_at__gte=week_ago).count()

        embed.add_field(
            name="📅 This Week",
            value=f"{recent_apps} new applications",
            inline=False
        )

        embed.add_field(
            name="🌐 Detailed Analytics",
            value=f"[View Dashboard]({DJANGO_API_URL}/dashboard/analytics/)",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await ctx.send("❌ Error fetching statistics.")
