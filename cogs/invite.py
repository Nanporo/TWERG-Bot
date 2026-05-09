import discord
from discord.ext import commands
from discord import app_commands

class InviteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="取得地牛記錄小組的 Discord 邀請網址")
    async def invite_command(self, interaction: discord.Interaction):
        message_content = "https://discord.gg/7sacMKp"

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="官方網站", url="https://www.twerg.org", style=discord.ButtonStyle.link))

        await interaction.response.send_message(content=message_content, view=view)

async def setup(bot):
    await bot.add_cog(InviteCog(bot))