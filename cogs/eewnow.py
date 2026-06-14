import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
import time
from datetime import datetime, timezone, timedelta

class EewNowCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="eewnow", description="查詢地牛Wake Up!當前在線人數")
    async def eewnow(self, interaction: discord.Interaction):
        # 避免 API 回應過慢導致超時報錯
        await interaction.response.defer()
        
        try:
            async with self.bot.session.get('https://eew.earthquake.tw/online.php') as response:
                if response.status != 200:
                    await interaction.followup.send(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                    return
                    
                text = await response.text()
                # 使用正則表達式尋找第一個出現的數字
                match = re.search(r'\d+', text)
                
                if match:
                    number = match.group(0)
                    
                    # 取得當前時間
                    current_time = time.time()
                    discord_timestamp = f"<t:{int(current_time)}:f>"
                    
                    # 為了 footer，轉換為可讀的台灣時間字串
                    tw_tz = timezone(timedelta(hours=8))
                    dt = datetime.fromtimestamp(current_time, tw_tz)
                    footer_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                    # ================== Embed ==================
                    message_content = "地牛Wake Up! 當前在線人數"
                    
                    embed = discord.Embed(color=0xffffff) 
                    
                    embed.add_field(name="👥 在線人數", value=f"{number} 人", inline=False)
                    embed.add_field(name="🕓 查詢時間", value=discord_timestamp, inline=True)
                    
                    embed.set_footer(text=f"地牛Wake Up! • 僅供參考")
                    # ============================================

                    await interaction.followup.send(content=message_content, embed=embed)
                else:
                    await interaction.followup.send("無法獲取在線人數資料。")
                        
        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：{e}")

# 註冊 Cog
async def setup(bot):
    await bot.add_cog(EewNowCog(bot))