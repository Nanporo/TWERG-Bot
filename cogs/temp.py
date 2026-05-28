import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime, timezone, timedelta

class TempView(discord.ui.View):
    def __init__(self, results, is_high, show_high_altitude):
        super().__init__(timeout=300)
        self.results = results
        self.is_high = is_high
        self.show_high_altitude = show_high_altitude
        self.show_details = False

    def build_embed(self):
        message_content = "🌡️ 今日最高溫測站排行" if self.is_high else "❄️ 今日最低溫測站排行"
        if not self.show_high_altitude:
            message_content += " (排除高海拔地區)"
        embed = discord.Embed(color=0xff3846 if self.is_high else 0x3498db)
        
        lines = []
        for i, r in enumerate(self.results[:10]):
            # 決定高低溫燈號
            temp_val = r['temp_sort']
            icon = "⚪️"
            if temp_val != 999.0 and temp_val != -999.0:
                if self.is_high:
                    if temp_val >= 38.0:
                        icon = "🔴"
                    elif temp_val >= 36.0:
                        icon = "🟠"
                    elif temp_val >= 32.0:
                        icon = "🟡"
                else:
                    if temp_val <= 6.0:
                        icon = "🟣"
                    elif temp_val <= 12.0:
                        icon = "🔵"
                    elif temp_val <= 16.0:
                        icon = "🟢"

            num_emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][i]
            if i < 3:
                rank_str = ['`🥇`', '`🥈`', '`🥉`'][i]
                line = f"{num_emoji} **`{icon} {r['temp_display']}`** {r['county']}{r['town']} {rank_str}"
            else:
                line = f"{num_emoji} **`{icon} {r['temp_display']}`** {r['county']}{r['town']}"

            if self.show_details:
                line += f"\n> `{r['station']}` {r['time']}"
            lines.append(line)
        
        embed.description = "\n".join(lines)
        current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
        embed.set_footer(text=f"中央氣象署 • 查詢時間 {current_time}")
        return message_content, embed

    @discord.ui.button(label="顯示詳細資訊", style=discord.ButtonStyle.primary)
    async def toggle_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.show_details = not self.show_details
        if self.show_details:
            button.label = "隱藏詳細資訊"
            button.style = discord.ButtonStyle.secondary
        else:
            button.label = "顯示詳細資訊"
            button.style = discord.ButtonStyle.primary
            
        content, embed = self.build_embed()
        await interaction.response.edit_message(content=content, embed=embed, view=self)

class TempCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.api_key = config.get('CWA_API_KEY')
        except Exception:
            self.api_key = None

    @app_commands.command(name="temp", description="查詢今日台灣各測站的最高溫或最低溫排行")
    @app_commands.describe(
        temp_type="選擇查詢最高溫或最低溫",
        高海拔="是否包含高海拔測站"
    )
    @app_commands.choices(temp_type=[
        app_commands.Choice(name="最高溫", value="high"),
        app_commands.Choice(name="最低溫", value="low")
    ], 高海拔=[
        app_commands.Choice(name="是", value="yes"),
        app_commands.Choice(name="否", value="no")
    ])
    async def temp_command(self, interaction: discord.Interaction, temp_type: app_commands.Choice[str], 高海拔: app_commands.Choice[str] = None):
        if not self.api_key:
            await interaction.response.send_message("⚠️ 未設定 API Key，無法查詢資料。", ephemeral=True)
            return

        # 避免 API 回應過慢導致超時報錯
        await interaction.response.defer()

        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization={self.api_key}&WeatherElement=DailyHigh&WeatherElement=DailyLow"

        try:
            async with self.bot.session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                    return
                
                data = await response.json()
                stations = data.get('records', {}).get('Station', [])

                # 預設包含高海拔測站
                show_high_altitude = True
                if 高海拔 and 高海拔.value == 'no':
                    show_high_altitude = False

                is_high = temp_type.value == "high"
                results = []
                for st in stations:
                    station_name = st.get('StationName', '未知')
                    geo_info = st.get('GeoInfo', {})
                    county = geo_info.get('CountyName', '')
                    town = geo_info.get('TownName', '')
                    altitude_str = geo_info.get('StationAltitude', '0')

                    try:
                        altitude = float(altitude_str)
                    except ValueError:
                        altitude = 0.0

                    # 若使用者選擇不包含，且測站高度 > 1000 公尺，則跳過此測站
                    if not show_high_altitude and altitude > 1000:
                        continue
                    
                    weather = st.get('WeatherElement', {}).get('DailyExtreme', {})
                    
                    if temp_type.value == "high":
                        temp_info = weather.get('DailyHigh', {}).get('TemperatureInfo', {})
                    else:
                        temp_info = weather.get('DailyLow', {}).get('TemperatureInfo', {})
                        
                    temp_str = temp_info.get('AirTemperature', '-99')
                    time_str = temp_info.get('Occurred_at', {}).get('DateTime', '')

                    try:
                        temp_val = float(temp_str)
                    except ValueError:
                        continue

                    # 處理氣象署資料的無效值 -99 或 -99.0
                    if temp_val <= -90.0:
                        temp_display = "無資料"
                        temp_sort = -999.0 if is_high else 999.0
                    else:
                        temp_display = f"{temp_val} °C"
                        temp_sort = temp_val
                        
                    # 處理測得溫度的時間轉換為 Discord 時間戳
                    try:
                        if temp_val <= -90.0 or not time_str or time_str == "-99":
                            time_format = "未知"
                        else:
                            dt = datetime.fromisoformat(time_str)
                            time_format = f"<t:{int(dt.timestamp())}:t>"
                    except Exception:
                        time_format = "未知"

                    results.append({
                        "station": station_name,
                        "county": county,
                        "town": town,
                        "temp_display": temp_display,
                        "temp_sort": temp_sort,
                        "time": time_format
                    })

                if not results:
                    await interaction.followup.send("⚠️ 找不到有效的溫度資料。")
                    return

                results.sort(key=lambda x: x['temp_sort'], reverse=is_high)
                
                view = TempView(results, is_high, show_high_altitude)
                content, embed = view.build_embed()

                await interaction.followup.send(content=content, embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：{e}")
            print(f"❌ /temp 發生未預期的錯誤：{e}")

async def setup(bot):
    await bot.add_cog(TempCog(bot))