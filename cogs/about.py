import discord
from discord.ext import commands
from discord import app_commands

class AboutCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about", description="顯示關於 TWERG BOT 的資訊")
    async def about_command(self, interaction: discord.Interaction):
        
        message_content = "ℹ️ 關於 TWERG BOT"

        embed = discord.Embed(
            title="這個 BOT 是做什麼用的？", 
            colour=0xff3a48
        )

        embed.add_field(
            name="",
            value="主要功能為自動推送體感回報網址，附帶一些簡潔功能。\n為了避免洗版，提示只會推播顯著有感地震的報告。\n如果您遇到任何問題，請聯絡機器人作者。",
            inline=False
        )
        embed.add_field(
            name="License",
            value="GNU Affero General Public License",
            inline=False
        )
        embed.add_field(
            name="版本",
            value="1.0.3",
            inline=False
        )
        embed.set_footer(text="作者 Kuuchi (kuuchi) • Support by TWERG", icon_url="https://avatars.githubusercontent.com/u/15816531?v=4")
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="地牛記錄小組", url="https://www.twerg.org", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="Discord 伺服器", url="https://discord.gg/7sacMKp", style=discord.ButtonStyle.link))
        
        await interaction.response.send_message(content=message_content, embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AboutCog(bot))