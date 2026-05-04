import discord
from discord.ext import commands
import json
import sys

# ================= 讀取設定檔 =================
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    DISCORD_TOKEN = config['DISCORD_TOKEN']
except Exception as e:
    print(f"❌ 讀取 config.json 失敗：{e}")
    sys.exit()
# ============================================

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # 必須開啟這個權限，機器人才能看懂 *push 指令
        intents.message_content = True 
        
        # 將指令前綴設定為 *
        super().__init__(command_prefix='*', intents=intents)

    async def setup_hook(self):
        # 載入地震模組
        await self.load_extension('cogs.earthquake')
        print("🔄 地震模組載入完成")

    async def on_ready(self):
        print(f'✅ 機器人已成功登入為 {self.user}')

bot = MyBot()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)