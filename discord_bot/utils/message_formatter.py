import discord

def create_error_embed(title, description):
    """Create a standardized error embed"""
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xdc3545
    )

def create_success_embed(title, description):
    """Create a standardized success embed"""
    return discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=0x28a745
    )

def create_info_embed(title, description):
    """Create a standardized info embed"""
    return discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=0x007bff
    )

def create_warning_embed(title, description):
    """Create a standardized warning embed"""
    return discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=0xffc107
    )
