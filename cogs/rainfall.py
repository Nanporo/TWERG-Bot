import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime, timezone, timedelta

class RainfallCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.api_key = config.get('CWA_API_KEY')
        except Exception:
            self.api_key = None

    @app_commands.command(name="rainfall", description="查詢今日台灣各測站的累積雨量排行")
    async def rainfall_command(self, interaction: discord.Interaction):
        if not self.api_key:
            await interaction.response.send_message("⚠️ 未設定 API Key，無法查詢資料。", ephemeral=True)
            return

        # 避免 API 回應過慢導致超時報錯
        await interaction.response.defer()

        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001?Authorization={self.api_key}&RainfallElement=Now"

        try:
            async with self.bot.session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                    return
                
                data = await response.json()
                stations = data.get('records', {}).get('Station', [])

                results = []
                for st in stations:
                    station_name = st.get('StationName', '未知')
                    geo_info = st.get('GeoInfo', {})
                    county = geo_info.get('CountyName', '')
                    town = geo_info.get('TownName', '')
                    
                    precip_info = st.get('RainfallElement', {}).get('Now', {})
                    precip_str = precip_info.get('Precipitation', '-99')

                    try:
                        precip_val = float(precip_str)
                    except ValueError:
                        continue

                    # 排除氣象署資料的無效值（例如 -99.0 或 -998.0）與無雨量的測站 (0.0)
                    if precip_val <= 0.0:
                        continue
                        
                    results.append({
                        "station": station_name,
                        "county": county,
                        "town": town,
                        "precip": precip_val
                    })

                if not results:
                    await interaction.followup.send("⚠️ 目前尚無大於 0.0 mm 的雨量資料。")
                    return

                results.sort(key=lambda x: x['precip'], reverse=True)
                
                message_content = "☔ 今日累積雨量測站排行"
                embed = discord.Embed(color=0x3498db)
                
                lines = []
                for i, r in enumerate(results[:10]):
                    # 決定降雨量特報燈號
                    precip_val = r['precip']
                    icon = "`💧`"
                    if precip_val >= 500.0:
                        icon = "`🟣`"
                    elif precip_val >= 350.0:
                        icon = "`🔴`"
                    elif precip_val >= 200.0:
                        icon = "`🟠`"
                    elif precip_val >= 80.0:
                        icon = "`🟡`"

                    if i < 3:
                        rank_str = ['`🥇`', '`🥈`', '`🥉`'][i]
                    else:
                        fw_num = str(i+1).translate(str.maketrans("0123456789", "０１２３４５６７８９"))
                        rank_str = f'`{fw_num}`'
                    lines.append(f"{icon} {rank_str} **{r['county']}{r['town']} ({r['station']})** `{r['precip']} mm`")
                
                embed.description = "\n".join(lines)
                current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
                embed.set_footer(text=f"資料來源：中央氣象署 • 查詢時間 {current_time}")

                await interaction.followup.send(content=message_content, embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：{e}")
            print(f"❌ /rainfall 發生未預期的錯誤：{e}")

async def setup(bot):
    await bot.add_cog(RainfallCog(bot))