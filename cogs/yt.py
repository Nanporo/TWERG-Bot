import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import re
import json
import os

class YTCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.video_url = "https://www.youtube.com/watch?v=KyT4qSK8lJo"
        self.last_viewers = None
        
        self.monitor_task.start()

    def cog_unload(self):
        self.monitor_task.cancel()

    async def get_live_viewers(self):
        """爬取 YouTube 頁面獲取直播觀看人數"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.video_url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    html = await response.text()
                    
                    # 1. 嘗試依據提供的 HTML 標籤結構尋找 (例如 <span>659</span><span> 人正在觀看</span>)
                    match = re.search(r'>([\d,]+)</span><span[^>]*>\s*人正在觀看', html)
                    if match:
                        return int(match.group(1).replace(',', ''))

                    # 2. 嘗試從 YouTube 內嵌的 JSON 資料中尋找 (aiohttp 取得的原始碼通常為 JSON 結構)
                    match = re.search(r'"text":"([\d,]+)"\}\s*,\s*\{"text":"\s*人正在觀看"', html)
                    if match:
                        return int(match.group(1).replace(',', ''))
                        
                    match = re.search(r'"viewCountText":\{"simpleText":"([\d,]+)\s*人正在觀看"', html)
                    if match:
                        return int(match.group(1).replace(',', ''))

                    # 3. 嘗試原有的 concurrentViewers 或是 viewCount 數據
                    match = re.search(r'"concurrentViewers":"(\d+)"', html)
                    if match:
                        return int(match.group(1))
                        
                    match = re.search(r'"viewCount":"(\d+)"', html)
                    if match:
                        return int(match.group(1))
                        
                    return None
        except Exception as e:
            print(f"❌ 獲取 YouTube 觀看人數失敗：{e}")
            return None

    @tasks.loop(minutes=5)
    async def monitor_task(self):
        await self.bot.wait_until_ready()
        current_viewers = await self.get_live_viewers()
        
        if current_viewers is not None and current_viewers > 1000000:
            print(f"⚠️ 觀看人數異常 ({current_viewers} 人)，超過 100 萬，略過此次監控")
            return

        if current_viewers is not None and current_viewers < 100:
            print(f"⚠️ 觀看人數過低 ({current_viewers} 人)，小於 100 人，可能為直播斷線，略過此次監控")
            return

        if current_viewers is None:
            print("⚠️ 無法獲取 YouTube 直播觀看人數")
            return

        if self.last_viewers is not None:
            diff = current_viewers - self.last_viewers
            
            # 讀取各伺服器的獨立設定
            try:
                with open('guild_settings.json', 'r', encoding='utf-8') as f:
                    guild_settings = json.load(f)
            except Exception:
                guild_settings = {}

            for guild_id, settings in guild_settings.items():
                # 確認有開啟監控，且增加的人數達到門檻
                if not settings.get("yt_monitor_enabled", False):
                    continue
                threshold = settings.get("yt_monitor_threshold", 1000)
                if diff < threshold:
                    continue
                
                # 向所有設定好的監控頻道發送推播
                channel_ids = settings.get("yt_target_channel_ids", [])
                for channel_id in channel_ids:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            embed = discord.Embed(title="⚠️ 可能有地震發生", description="台灣地震監視 YouTube 直播觀看人數增加", color=0xffffff)
                            embed.add_field(name="📈 增加人數", value=f"+{diff} 人", inline=True)
                            embed.add_field(name="👥 目前總人數", value=f"{current_viewers} 人", inline=True)
                            view = discord.ui.View()
                            view.add_item(discord.ui.Button(label="觀看 YouTube 直播", url=self.video_url, style=discord.ButtonStyle.link))
                            await channel.send(embed=embed, view=view)
                        except discord.Forbidden:
                            pass

        # 更新最後一次獲取的觀看人數
        self.last_viewers = current_viewers

    @app_commands.command(name="yt", description="查詢台灣地震監視 YouTube 直播觀看人數")
    async def yt_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        current_viewers = await self.get_live_viewers()
        
        if current_viewers is not None and current_viewers > 1000000:
            await interaction.followup.send(f"❌ 抓取到異常觀看人數 ({current_viewers} 人)，超過 100 萬，判定為無效數值。")
            return

        if current_viewers is not None and current_viewers < 100:
            await interaction.followup.send(f"❌ 抓取到異常觀看人數 ({current_viewers} 人)，小於 100 人，判定為直播暫時斷線。")
            return

        if current_viewers is None:
            await interaction.followup.send("❌ 無法獲取直播觀看人數，可能是直播已結束或 YouTube 頁面結構改變。")
            return
            
        embed = discord.Embed(title="台灣地震監視 YouTube 直播監控狀態", url=self.video_url, color=0xffffff)
        embed.add_field(name="目前觀看人數", value=f"{current_viewers} 人", inline=False)
        
        if self.last_viewers is not None:
            diff = current_viewers - self.last_viewers
            trend = "增加" if diff > 0 else "減少" if diff < 0 else "無變化"
            embed.add_field(name="上次記錄人數 (前 5 分鐘)", value=f"{self.last_viewers} 人 ({trend} {abs(diff)} 人)", inline=False)
        else:
            embed.add_field(name="上次記錄人數", value="尚未有記錄 (等待下一次更新)", inline=False)
            
        # 取得當前伺服器的設定門檻
        threshold = 1000
        if interaction.guild:
            try:
                with open('guild_settings.json', 'r', encoding='utf-8') as f:
                    guild_settings = json.load(f)
                guild_id_str = str(interaction.guild.id)
                if guild_id_str in guild_settings:
                    threshold = guild_settings[guild_id_str].get("yt_monitor_threshold", 1000)
            except Exception:
                pass
                
        embed.set_footer(text=f"每 5 分鐘自動檢查，若觀看人數增加超過 {threshold} 人將發送警報。")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(YTCog(bot))