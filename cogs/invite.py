import discord
from discord.ext import commands
from discord import app_commands

class InviteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="取得地牛記錄小組的 Discord 邀請網址")
    async def invite_command(self, interaction: discord.Interaction):
        message_content = "Discord 邀請網址"

        embed = discord.Embed(colour=0xff3a48)

        embed.add_field(
            name="地牛記錄小組 Discord 伺服器",
            value="https://discord.gg/7sacMKp",
            inline=False
        )
        embed.add_field(
            name="地牛記錄小組 官方網站",
            value="https://www.twerg.org",
            inline=False
        )

        await interaction.response.send_message(content=message_content, embed=embed)

async def setup(bot):
    await bot.add_cog(InviteCog(bot))