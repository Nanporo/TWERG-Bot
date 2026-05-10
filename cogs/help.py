import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="顯示 TWERG BOT 的使用幫助與可用指令清單")
    async def help_command(self, interaction: discord.Interaction):
        
        message_content = "🛠️ TWERG BOT 使用幫助"
        
        embed = discord.Embed(title="可用指令", color=0xff3846)
        embed.add_field(name="/about", value="ℹ️ 關於 TWERG BOT 的資訊", inline=False)
        embed.add_field(name="/dyfi", value="📃 最新一筆體感回報的網址和簡易地震報告", inline=False)
        embed.add_field(name="/eewnow", value="🌐 查詢 地牛Wake Up! 的在線人數", inline=False)
        embed.add_field(name="/help", value="🛠️ 使用幫助", inline=False)
        embed.add_field(name="/invite", value="🔗 取得地牛記錄小組的 Discord 邀請網址", inline=False)
        embed.add_field(name="/kkw", value="💥 計算地震規模相等於多少顆原子彈的能量", inline=False)
        embed.add_field(name="/yt", value="🖥️ 查詢 台灣地震監視 YouTube 直播觀看人數", inline=False)
        embed.add_field(name="/add", value="`(限管理員)` 將目前頻道加入自動推送列表", inline=False)
        embed.add_field(name="/remove", value="`(限管理員)` 將目前頻道從自動推送列表移除", inline=False)
        embed.add_field(name="/settings", value="`(限管理員)` 顯示或修改機器人的設定", inline=False)


        await interaction.response.send_message(content=message_content, embed=embed)


async def setup(bot):
    bot.remove_command("help") # 移除 discord.py 預設的 help 指令
    await bot.add_cog(HelpCog(bot))