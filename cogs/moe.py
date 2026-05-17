import discord
from discord.ext import commands
from discord import app_commands

class MoeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="看板娘", description="啊咧？")
    async def moe_command(self, interaction: discord.Interaction):
        message_content = "Coming Soon..."

        await interaction.response.send_message(content=message_content, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MoeCog(bot))