import discord
from discord.ext import commands
import requests
import logging

logger = logging.getLogger(__name__)


@bot.command(name='followup')
async def followup_command(ctx, *, company_name=None):
    """Send follow-up emails"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            await ctx.send("❌ Profile not found. Use `!search` to get started.")
            return

        if company_name:
            # Send follow-up to specific company
            await send_specific_followup(ctx, user, company_name)
        else:
            # Send bulk follow-ups
            await send_bulk_followups(ctx, user)

    except Exception as e:
        logger.error(f"Follow-up command error: {e}")
        await ctx.send("❌ Error with follow-up command.")


async def send_bulk_followups(ctx, user):
    """Send bulk follow-up emails"""
    try:
        from datetime import date
        # Get applications that need follow-up
        due_applications = JobApplication.objects.filter(
            user=user,
            next_follow_up_date__lte=date.today(),
            application_status__in=['applied', 'responded']
        )

        if not due_applications:
            embed = discord.Embed(
                title="✅ No Follow-ups Due",
                description="All your follow-ups are up to date!",
                color=0x28a745
            )
            await ctx.send(embed=embed)
            return

        # Create confirmation embed
        embed = discord.Embed(
            title="📧 Bulk Follow-up Confirmation",
            description=f"Ready to send follow-ups for {len(due_applications)} applications:",
            color=0xffc107
        )

        app_list = []
        for app in due_applications[:5]:  # Show max 5
            app_list.append(f"• **{app.job_title}** at {app.company_name}")

        if len(due_applications) > 5:
            app_list.append(f"... and {len(due_applications) - 5} more")

        embed.add_field(name="Applications", value="\n".join(app_list), inline=False)
        embed.add_field(name="React with ✅ to confirm", value="You have 30 seconds to respond", inline=False)

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user_obj):
            return user_obj == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id

        try:
            reaction, user_obj = await bot.wait_for('reaction_add', timeout=30.0, check=check)

            if str(reaction.emoji) == "✅":
                # Send follow-ups via Celery task
                from followups.tasks import send_bulk_followup_emails
                app_ids = [app.id for app in due_applications]

                # Get default template
                from followups.models import FollowUpTemplate
                template = FollowUpTemplate.objects.filter(
                    user=user, is_default=True, is_active=True
                ).first()

                if template:
                    send_bulk_followup_emails.delay(app_ids, template.id)

                    success_embed = discord.Embed(
                        title="✅ Follow-ups Sent!",
                        description=f"Bulk follow-up started for {len(app_ids)} applications.",
                        color=0x28a745
                    )
                    await message.edit(embed=success_embed)
                else:
                    await message.edit(embed=create_error_embed("No Template", "No default follow-up template found."))
            else:
                cancelled_embed = discord.Embed(
                    title="❌ Cancelled",
                    description="Bulk follow-up cancelled.",
                    color=0x6c757d
                )
                await message.edit(embed=cancelled_embed)

        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Timeout",
                description="Follow-up confirmation timed out.",
                color=0x6c757d
            )
            await message.edit(embed=timeout_embed)

    except Exception as e:
        logger.error(f"Bulk follow-up error: {e}")
        await ctx.send("❌ Error sending bulk follow-ups.")


async def send_specific_followup(ctx, user, company_name):
    """Send follow-up to specific company"""
    try:
        # Find application for company
        applications = JobApplication.objects.filter(
            user=user,
            company_name__icontains=company_name,
            application_status__in=['applied', 'responded']
        )

        if not applications:
            embed = discord.Embed(
                title="❌ Company Not Found",
                description=f"No applications found for companies matching '{company_name}'",
                color=0xdc3545
            )
            await ctx.send(embed=embed)
            return

        app = applications.first()

        # Send follow-up via Celery task
        from followups.tasks import send_followup_email
        from followups.models import FollowUpTemplate

        template = FollowUpTemplate.objects.filter(
            user=user, is_default=True, is_active=True
        ).first()

        if template:
            send_followup_email.delay(app.id, template.id)

            embed = discord.Embed(
                title="📧 Follow-up Sent!",
                description=f"Follow-up email sent for **{app.job_title}** at **{app.company_name}**",
                color=0x28a745
            )
            embed.add_field(name="Template Used", value=template.template_name, inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No default follow-up template found.")

    except Exception as e:
        logger.error(f"Specific follow-up error: {e}")
        await ctx.send("❌ Error sending follow-up.")


@bot.command(name='due')
async def due_followups_command(ctx):
    """Check follow-ups that are due"""
    try:
        user = await get_user_by_discord_id(ctx.author.id)
        if not user:
            await ctx.send("❌ Profile not found.")
            return

        from datetime import date
        due_apps = JobApplication.objects.filter(
            user=user,
            next_follow_up_date__lte=date.today(),
            application_status__in=['applied', 'responded']
        )

        if not due_apps:
            embed = discord.Embed(
                title="✅ No Follow-ups Due",
                description="All your follow-ups are up to date!",
                color=0x28a745
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="⏰ Follow-ups Due Today",
            description=f"You have {len(due_apps)} follow-ups to send",
            color=0xffc107
        )

        for app in due_apps[:5]:  # Show max 5
            days_overdue = (date.today() - app.next_follow_up_date).days
            overdue_text = f"({days_overdue} days overdue)" if days_overdue > 0 else "(due today)"

            embed.add_field(
                name=f"📧 {app.job_title}",
                value=f"**Company:** {app.company_name}\n**Due:** {overdue_text}",
                inline=True
            )

        embed.add_field(
            name="🚀 Send Follow-ups",
            value="Use `!followup` to send all due follow-ups",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        logger.error(f"Due followups error: {e}")
        await ctx.send("❌ Error checking due follow-ups.")