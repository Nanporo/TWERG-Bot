import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timezone, timedelta

class EarthquakeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_earthquake_no = None
        self.owner_id = 69370157784371200 # 你的專屬 ID
        
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.api_key = config['CWA_API_KEY']
        self.target_channels = config.get('TARGET_CHANNEL_IDS', [])
        
        self.check_earthquake.start()

    def cog_unload(self):
        self.check_earthquake.cancel()

    # 將 ctx 與 interaction 都作為可選參數傳入，方便回覆不同來源的觸發
    async def fetch_and_send(self, force=False, ctx: commands.Context = None, interaction: discord.Interaction = None):
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={self.api_key}&format=JSON"
        
        # 定義一個輔助函數，用來處理回覆訊息，相容傳統與斜線指令
        async def reply_message(content):
            if ctx:
                await ctx.send(content)
            elif interaction:
                await interaction.followup.send(content, ephemeral=True) # 斜線指令回覆設為僅自己可見

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await reply_message(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                        return

                    data = await response.json()
                    earthquakes = data.get('records', {}).get('Earthquake', [])
                    
                    if not earthquakes:
                        await reply_message("⚠️ 目前找不到任何地震資料。")
                        return

                    latest_earthquake = earthquakes[0]
                    current_no = latest_earthquake.get('EarthquakeNo')
                    
                    if current_no is None:
                        return

                    if not force:
                        if self.last_earthquake_no is None:
                            self.last_earthquake_no = current_no
                            print(f"🔄 初始載入完成，目前最新的地震編號為：{self.last_earthquake_no}")
                            return
                        if current_no == self.last_earthquake_no:
                            return
                    
                    self.last_earthquake_no = current_no
                    
                    eq_info = latest_earthquake.get('EarthquakeInfo', {})
                    origin_time_str = eq_info.get('OriginTime', '')
                    magnitude = eq_info.get('EarthquakeMagnitude', {}).get('MagnitudeValue', '未知')
                    focal_depth = eq_info.get('FocalDepth', '未知')
                    
                    try:
                        tw_tz = timezone(timedelta(hours=8))
                        dt = datetime.strptime(origin_time_str, "%Y-%m-%d %H:%M:%S")
                        dt = dt.replace(tzinfo=tw_tz)
                        discord_time = f"<t:{int(dt.timestamp())}:F>"
                    except ValueError:
                        discord_time = origin_time_str

                    report_url = f"https://www.twerg.org/dyfi?eq={current_no}"
                    message_content = f"# 📃 體感回報填寫（{current_no}）"
                    
                    embed = discord.Embed(title="顯著有感地震報告", color=0xff3846)
                    embed.add_field(name="編號", value=str(current_no), inline=True)
                    embed.add_field(name="規模", value=f"芮氏 {magnitude}", inline=True)
                    embed.add_field(name="深度", value=f"{focal_depth} 公里", inline=True)
                    embed.add_field(name="發生時間", value=discord_time, inline=False)
                    
                    view = discord.ui.View()
                    button = discord.ui.Button(label="體感回報網頁", url=report_url, style=discord.ButtonStyle.link)
                    view.add_item(button)
                    
                    # 發送至頻道
                    for channel_id in self.target_channels:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            try:
                                await channel.send(content=message_content, embed=embed, view=view)
                            except discord.Forbidden:
                                print(f"❌ 無法發送至頻道 {channel_id}：權限不足。")
                        else:
                            print(f"⚠️ 找不到頻道 {channel_id}。")
                            
                    # 推送成功後的回報
                    if force:
                        await reply_message(f"✅ 已強制推送地震編號：`{current_no}`")
                        print(f"🚨 管理員手動推送了地震報告：{current_no}")
                    else:
                        print(f"🚨 自動發現並發送新地震報告：{current_no}")

        except Exception as e:
            await reply_message(f"❌ 發生錯誤：{e}")
            print(f"❌ 發生未預期的錯誤：{e}")

    @tasks.loop(seconds=30)
    async def check_earthquake(self):
        await self.fetch_and_send(force=False)

    @check_earthquake.before_loop
    async def before_check_earthquake(self):
        await self.bot.wait_until_ready()

    # ================= 傳統文字指令 *push =================
    @commands.command(name="push")
    async def traditional_push(self, ctx):
        if ctx.author.id != self.owner_id:
            return
        
        temp_msg = await ctx.send("⏳ 正在抓取最新地震資料，請稍候...")
        await self.fetch_and_send(force=True, ctx=ctx)
        await temp_msg.delete()

    # ================= 斜線指令 /push =================
    @app_commands.command(name="push", description="強制推送最新的一筆地震報告")
    async def slash_push(self, interaction: discord.Interaction):
        # 權限檢查
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ 你沒有權限使用此指令。", ephemeral=True)
            return
        
        # 避免 API 超時，先顯示思考中 (僅限自己可見)
        await interaction.response.defer(ephemeral=True)
        await self.fetch_and_send(force=True, interaction=interaction)

async def setup(bot):
    await bot.add_cog(EarthquakeCog(bot))