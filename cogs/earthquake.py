import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from ownercheck import is_owner

class EarthquakeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_earthquake_no = None
        
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.api_key = config['CWA_API_KEY']
        
        self.check_earthquake.start()

    def cog_unload(self):
        self.check_earthquake.cancel()

    # 將 ctx 與 interaction 都作為可選參數傳入，方便回覆不同來源的觸發
    async def fetch_and_send(self, force=False, target_guild_id=None, ctx: commands.Context = None, interaction: discord.Interaction = None, push_type: str = "report"):
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
                        discord_time = f"<t:{int(dt.timestamp())}:f>"
                    except ValueError:
                        discord_time = origin_time_str

                    report_url = f"https://www.twerg.org/dyfi?eq={current_no}"
                    message_content = f"# 📃 體感回報填寫（{current_no}）"
                    
                    embed = discord.Embed(title="顯著有感地震報告", description=report_url, color=0xff3846)
                    embed.add_field(name="編號", value=str(current_no), inline=True)
                    embed.add_field(name="規模", value=f"芮氏 {magnitude}", inline=True)
                    embed.add_field(name="深度", value=f"{focal_depth} 公里", inline=True)
                    embed.add_field(name="發生時間", value=discord_time, inline=False)
                    
                    view = discord.ui.View()
                    button = discord.ui.Button(label="TWERG 體感回報網頁", url=report_url, style=discord.ButtonStyle.link)
                    view.add_item(button)
                    
                    # 讀取各伺服器的獨立設定
                    try:
                        with open('guild_settings.json', 'r', encoding='utf-8') as f:
                            guild_settings = json.load(f)
                    except Exception:
                        guild_settings = {}
                        
                    try:
                        mag_val = float(magnitude)
                    except ValueError:
                        mag_val = 0.0 # 若無法解析規模(如: 未知)，預設為0.0
                        
                    # 若為強制推送 TWERG 體感回報，先檢查是否有資料
                    if force and push_type == "dyfi":
                        dyfi_url = f"https://www.twerg.org/api/dyfi-reports?eq_no={current_no}"
                        has_data = False
                        try:
                            async with session.get(dyfi_url) as dyfi_res:
                                if dyfi_res.status == 200:
                                    dyfi_json = await dyfi_res.json()
                                    if dyfi_json.get("meta", {}).get("totalReports", 0) > 0:
                                        has_data = True
                        except Exception:
                            pass
                            
                        if not has_data:
                            await reply_message("⚠️ 未推送，沒有 TWERG 體感回報資料")
                            return

                    pushed_channels = []
                    dyfi_scheduled_channels = []
                    # 依據各伺服器設定決定是否發送與發送目標
                    for guild_id, settings in guild_settings.items():
                        # 若有指定目標伺服器，則跳過非目標的伺服器
                        if target_guild_id and str(guild_id) != str(target_guild_id):
                            continue
                            
                        # 若未開啟自動推送，則跳過
                        if not settings.get("auto_push"):
                            continue
                            
                        # 檢查規模是否達標
                        if mag_val < settings.get("min_magnitude", 4.0):
                            continue
                            
                        # 是否發送30分鐘後初步統計 (預設開啟)
                        auto_dyfi = settings.get("auto_dyfi_report", True)
                            
                        # 兼容新舊版設定，使用 target_channel_ids
                        channel_ids = settings.get("target_channel_ids", [])
                        legacy_id = settings.get("target_channel_id")
                        if legacy_id and legacy_id not in channel_ids:
                            channel_ids.append(legacy_id)
                            
                        if not channel_ids:
                            continue
                            
                        for channel_id in channel_ids:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                if push_type == "report":
                                    try:
                                        await channel.send(content=message_content, embed=embed, view=view)
                                        if channel not in pushed_channels:
                                            pushed_channels.append(channel)
                                        if auto_dyfi and channel not in dyfi_scheduled_channels:
                                            dyfi_scheduled_channels.append(channel)
                                    except discord.Forbidden:
                                        print(f"❌ 無法發送至頻道 {channel_id}：權限不足。")
                                elif push_type == "dyfi":
                                    if channel not in pushed_channels:
                                        pushed_channels.append(channel)
                            else:
                                print(f"⚠️ 找不到頻道 {channel_id}。")
                                
                    if pushed_channels:
                        if push_type == "report":
                            if dyfi_scheduled_channels:
                                self.bot.dispatch("earthquake_pushed", current_no, dyfi_scheduled_channels, str(magnitude), str(focal_depth), origin_time_str)
                        elif push_type == "dyfi":
                            self.bot.dispatch("force_dyfi_report", current_no, pushed_channels, str(magnitude), str(focal_depth), origin_time_str)
                            
                    # 推送成功後的回報
                    if force:
                        msg = f"✅ 已強制推送地震編號：`{current_no}`"
                        if push_type == "dyfi":
                            msg += " 的 TWERG 體感回報"
                            print(f"🚨 管理員手動推送了地震 {current_no} 的 TWERG 體感回報")
                        else:
                            print(f"🚨 管理員手動推送了地震報告：{current_no}")
                        await reply_message(msg)
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
    async def traditional_push(self, ctx, arg1: str = "report", arg2: str = "global"):
        if not is_owner(ctx.author.id):
            return
        
        push_type = "report"
        scope = "global"
        args = [arg1.lower(), arg2.lower()]
        
        if "dyfi" in args:
            push_type = "dyfi"
        if "local" in args:
            scope = "local"
            
        target_guild_id = None
        if scope == "local":
            if not ctx.guild:
                await ctx.send("❌ 「local (此伺服器)」選項只能在伺服器當中使用。")
                return
            target_guild_id = ctx.guild.id
            
        temp_msg = await ctx.send("⏳ 正在抓取最新地震資料，請稍候...")
        await self.fetch_and_send(force=True, target_guild_id=target_guild_id, ctx=ctx, push_type=push_type)
        await temp_msg.delete()

    # ================= 斜線指令 /push =================
    @app_commands.command(name="push", description="（限擁有者）強制推送最新的一筆地震報告")
    @app_commands.describe(scope="推送範圍", push_type="推送類型")
    @app_commands.choices(
        scope=[
            app_commands.Choice(name="此伺服器", value="local"),
            app_commands.Choice(name="全域", value="global")
        ],
        push_type=[
            app_commands.Choice(name="地震報告", value="report"),
            app_commands.Choice(name="體感回報", value="dyfi")
        ]
    )
    async def slash_push(self, interaction: discord.Interaction, scope: app_commands.Choice[str], push_type: app_commands.Choice[str] = None):
        # 權限檢查
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ 你沒有權限使用此指令。", ephemeral=True)
            return
        
        target_guild_id = None
        if scope.value == "local":
            if not interaction.guild_id:
                await interaction.response.send_message("❌ 「此伺服器」選項只能在伺服器當中使用。", ephemeral=True)
                return
            target_guild_id = interaction.guild_id
            
        ptype = push_type.value if push_type else "report"
            
        # 避免 API 超時，先顯示思考中 (僅限自己可見)
        await interaction.response.defer(ephemeral=True)
        await self.fetch_and_send(force=True, target_guild_id=target_guild_id, interaction=interaction, push_type=ptype)

async def setup(bot):
    await bot.add_cog(EarthquakeCog(bot))