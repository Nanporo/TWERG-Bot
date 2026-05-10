import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime

class DyfiReportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 用來記錄已經在排程倒數中的地震編號，避免重複倒數
        self.scheduled_eqs = set()

    @commands.Cog.listener()
    async def on_earthquake_pushed(self, eq_no: str, channels: list):
        # 檢查是否已經在倒數中
        if eq_no in self.scheduled_eqs:
            print(f"⚠️ 地震 {eq_no} 的體感回報已在排程中，略過重複觸發。")
            return
            
        self.scheduled_eqs.add(eq_no)
        print(f"⏳ 已排程地震 {eq_no} 的體感回報，將在 30 分鐘後發送...")
        
        # 將等待與發送的工作建立為背景任務，不阻塞目前的事件處理
        self.bot.loop.create_task(self.send_dyfi_report(eq_no, channels, delay=1800))

    @commands.Cog.listener()
    async def on_force_dyfi_report(self, eq_no: str, channels: list):
        print(f"🚨 管理員強制推送了地震 {eq_no} 的體感回報！")
        self.bot.loop.create_task(self.send_dyfi_report(eq_no, channels, delay=0))

    async def send_dyfi_report(self, eq_no: str, channels: list, delay: int = 1800):
        if delay > 0:
            await asyncio.sleep(delay)
            self.scheduled_eqs.discard(eq_no) # 倒數結束，從清單移除
        
        url = f"https://www.twerg.org/api/dyfi-reports?eq_no={eq_no}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"⚠️ 無法取得體感回報資料，狀態碼：{response.status}")
                        return
                    
                    data = await response.json()
                    
                    meta = data.get("meta", {})
                    total_reports = meta.get("totalReports", 0)
                    valid_reports = meta.get("validReports", 0)
                    calibrated_at_str = meta.get("calibratedAt", "")
                    
                    if total_reports == 0:
                        print(f"⚠️ 地震 {eq_no} 沒有任何體感回報，取消發送。")
                        return
                        
                    if calibrated_at_str:
                        try:
                            calibrated_dt = datetime.fromisoformat(calibrated_at_str.replace("Z", "+00:00"))
                            calibrated_discord_time = f"<t:{int(calibrated_dt.timestamp())}:F>"
                        except ValueError:
                            calibrated_discord_time = calibrated_at_str
                    else:
                        calibrated_discord_time = "無資料"
                        
                    # 以下可依據後續需求隨時調整排版格式
                    message_content = f"📑 體感回報（{eq_no}）"
                    
                    embed = discord.Embed(
                        title=f"30分鐘初步統計",
                        color=0x3498db
                    )
                    
                    embed.add_field(name="📊 回報數量", value=f"{total_reports} 筆", inline=True)
                    embed.add_field(name="✅ 認可數量", value=f"{valid_reports} 筆", inline=True)
                    embed.add_field(name="🕓 體感回報統計時間", value=calibrated_discord_time, inline=False)
                    
                    town_cdi = data.get("townCDI", [])
                    if town_cdi:
                        # 過濾異常警告的資料
                        town_cdi = [town for town in town_cdi if str(town.get("anomalyWarning", 0)) != "1"]
                        
                        # 依照 grade 權重與體感震度 (cdi) 由大到小重新排序
                        grade_order = {"7": 10, "6強": 9, "6+": 9, "6弱": 8, "6-": 8, "5強": 7, "5+": 7, "5弱": 6, "5-": 6, "4": 5, "3": 4, "2": 3, "1": 2, "0": 1}
                        town_cdi.sort(key=lambda x: (grade_order.get(str(x.get("grade", "0")), 0), x.get("cdi", 0.0)), reverse=True)
                        
                        grade_map = {"0": "⚫", "1": "⚪", "2": "🟢", "3": "🔵", "4": "🟡", "5-": "🟠", "5弱": "🟠", "5+": "🟤", "5強": "🟤", "6-": "🔴", "6弱": "🔴", "6+": "🟣", "6強": "🟣", "7": "🛑"}
                        # 排序後，取出最多前 8 筆市區資料當作範例顯示
                        top_towns = []
                        for town in town_cdi[:8]:
                            county = town.get("countyName", "")
                            town_name = town.get("townName", "")
                            grade = str(town.get("grade", "0"))
                            emoji = grade_map.get(grade, "⚫")
                            fw_grade = grade.translate(str.maketrans("01234567-+", "０１２３４５６７－＋"))
                            suspect_mark = " `⚠️`" if town.get("isSuspect") else ""
                            top_towns.append(f"`{emoji}` {fw_grade}級　{county} {town_name}{suspect_mark}")
                        
                        towns_value = "\n".join(top_towns) if top_towns else "目前無符合條件的回報資料"
                    else:
                        towns_value = "目前無回報資料"
                        
                    embed.add_field(
                        name="體感回報內容 (最大8筆)",
                        value=towns_value,
                        inline=False
                    )
                    
                    embed.set_footer(text="地震資訊請以中央氣象署發佈為準 • 地牛記錄小組")
                    
                    view = discord.ui.View()
                    btn_url = discord.ui.Button(label="體感回報網頁", url=f"https://www.twerg.org/dyfi?eq={eq_no}", style=discord.ButtonStyle.link)
                    view.add_item(btn_url)
                    
                    for channel in channels:
                        try:
                            await channel.send(content=message_content, embed=embed, view=view)
                        except discord.Forbidden:
                            print(f"❌ 無法發送體感報告至頻道 {channel.id}：權限不足。")
                        except Exception as e:
                            print(f"❌ 發送體感報告至頻道 {channel.id} 時發生錯誤：{e}")
                            
        except Exception as e:
            print(f"❌ /dyfiReport 發生未預期的錯誤：{e}")

async def setup(bot):
    await bot.add_cog(DyfiReportCog(bot))