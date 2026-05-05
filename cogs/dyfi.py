import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timezone, timedelta

class DyfiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 讀取 API Key
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.api_key = config['CWA_API_KEY']

    @app_commands.command(name="dyfi", description="查詢最新一筆地震並取得體感回報連結")
    async def dyfi(self, interaction: discord.Interaction):
        # 避免 API 回應過慢導致超時報錯 (因為所有人都能用，我們不加 ephemeral=True，讓大家都能看到回覆)
        await interaction.response.defer()
        
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={self.api_key}&format=JSON"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                        return

                    data = await response.json()
                    earthquakes = data.get('records', {}).get('Earthquake', [])
                    
                    if not earthquakes:
                        await interaction.followup.send("⚠️ 目前找不到任何地震資料。")
                        return

                    # 取最新的一筆資料
                    latest_earthquake = earthquakes[0]
                    current_no = latest_earthquake.get('EarthquakeNo')
                    
                    if current_no is None:
                        await interaction.followup.send("⚠️ 找不到最新的地震編號資料。")
                        return

                    # 解析進階資訊
                    eq_info = latest_earthquake.get('EarthquakeInfo', {})
                    origin_time_str = eq_info.get('OriginTime', '')
                    magnitude = eq_info.get('EarthquakeMagnitude', {}).get('MagnitudeValue', '未知')
                    focal_depth = eq_info.get('FocalDepth', '未知')
                    
                    # 轉換時間戳記
                    try:
                        tw_tz = timezone(timedelta(hours=8))
                        dt = datetime.strptime(origin_time_str, "%Y-%m-%d %H:%M:%S")
                        dt = dt.replace(tzinfo=tw_tz)
                        discord_time = f"<t:{int(dt.timestamp())}:F>"
                    except ValueError:
                        discord_time = origin_time_str

                    # 準備排版內容 (和 /push 的格式相同)
                    report_url = f"https://www.twerg.org/dyfi?eq={current_no}"
                    message_content = f"# 體感回報填寫（{current_no}）"
                    
                    embed = discord.Embed(title="顯著有感地震報告", color=0xff3846)
                    embed.add_field(name="編號", value=str(current_no), inline=True)
                    embed.add_field(name="規模", value=f"芮氏 {magnitude}", inline=True)
                    embed.add_field(name="深度", value=f"{focal_depth} 公里", inline=True)
                    embed.add_field(name="發生時間", value=discord_time, inline=False)
                    
                    view = discord.ui.View()
                    button = discord.ui.Button(label="體感回報網頁", url=report_url, style=discord.ButtonStyle.link)
                    view.add_item(button)
                    
                    # 將排版好的訊息回覆給觸發指令的用戶
                    await interaction.followup.send(content=message_content, embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：{e}")
            print(f"❌ /dyfi 發生未預期的錯誤：{e}")

# 註冊 Cog
async def setup(bot):
    await bot.add_cog(DyfiCog(bot))