import discord
from discord.ext import commands
from discord import app_commands

class AboutCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about", description="顯示關於 TWERG BOT 的資訊")
    async def about_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="關於 TWERG BOT",
            description="地牛記錄小組 官方網站\nhttps://www.twerg.org\n\n地牛記錄小組 Discord 伺服器\nhttps://discord.gg/7sacMKp",
            colour=0xff3a48
        )

        embed.add_field(
            name="這個 BOT 是做什麼用的？",
            value="主要功能為自動推送體感回報網址，附帶一些簡潔功能。\n如果您遇到任何問題，請聯絡機器人作者。",
            inline=False
        )
        embed.add_field(
            name="License",
            value="GNU Affero General Public License",
            inline=False
        )
        embed.add_field(
            name="版本",
            value="1.0.1",
            inline=False
        )
        embed.set_footer(text="作者 Kuuchi (kuuchi)", icon_url="https://avatars.githubusercontent.com/u/15816531?v=4")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AboutCog(bot))