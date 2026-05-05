import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="顯示 TWERG BOT 的使用幫助與可用指令清單")
    async def help_command(self, interaction: discord.Interaction):
        
        # 1. 建立一般文字內容
        message_content = "## TWERG BOT 使用幫助"
        
        # 2. 建立 Embed 面板並填入你提供的內容
        embed = discord.Embed(title="可用指令", color=0xff3846)
        embed.add_field(name="/dyfi", value="最新一筆體感回報的網址和簡易地震報告", inline=False)
        embed.add_field(name="/eewnow", value="查詢 地牛Wake Up! 的在線人數", inline=False)
        embed.add_field(name="/help", value="使用幫助（目前的指令）", inline=False)
        
        # 加入你設定的 Footer (頁尾) 資訊
        embed.set_footer(text="作者 Kuuchi (kuuchi)", icon_url="https://avatars.githubusercontent.com/u/15816531?v=4")
        
        # 3. 回覆給觸發指令的用戶
        await interaction.response.send_message(content=message_content, embed=embed)

# 註冊 Cog
async def setup(bot):
    # 因為 discord.py 預設會有一個文字版的 help 指令 (雖然我們沒有用到)
    # 為了避免與預設的 help 指令衝突，我們可以先把預設的移除
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))