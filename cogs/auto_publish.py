import discord
from discord.ext import commands
import json
import asyncio
import re
import logging

class AutoPublishCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_regex = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 只處理公告頻道 (News)
        if message.channel.type != discord.ChannelType.news:
            return

        if not message.guild:
            return

        # 讀取設定檔確認是否啟用
        try:
            with open('guild_settings.json', 'r', encoding='utf-8') as f:
                guild_settings = json.load(f)
            settings = guild_settings.get(str(message.guild.id), {})
            if not settings.get("auto_publish_news", False):
                return
        except Exception:
            return

        # 如果訊息包含網址，稍微等待 Discord 產生 Embed
        if self.url_regex.search(message.content):
            for _ in range(5):
                await asyncio.sleep(1)
                try:
                    msg = await message.channel.fetch_message(message.id)
                    if msg.embeds:
                        break
                except discord.NotFound:
                    return
                except Exception:
                    pass

        try:
            msg = await message.channel.fetch_message(message.id)
            # 檢查是否已經發布過了
            if not msg.flags.crossposted:
                await msg.publish()
                logging.info(f"📢 [Auto Publish] 已自動發布訊息至 {message.channel.name}")
        except discord.Forbidden:
            logging.error(f"❌ [Auto Publish] 無法發布訊息：缺少管理訊息權限 ({message.channel.name})")
        except discord.HTTPException as e:
            logging.error(f"❌ [Auto Publish] 發布訊息時發生錯誤：{e}")
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(AutoPublishCog(bot))
