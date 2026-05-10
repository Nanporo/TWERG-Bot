import discord
from discord.ext import commands
import json
import sys
from datetime import timezone, timedelta

# ================= 讀取設定檔 =================
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    DISCORD_TOKEN = config['DISCORD_TOKEN']
    # 讀取要同步斜線指令的伺服器 ID 列表，如果沒設定就給個空陣列
    GUILD_IDS = config.get('GUILD_IDS', [])
    
except FileNotFoundError:
    print("❌ 錯誤：找不到 config.json 檔案！請確保它與 bot.py 放在同一個資料夾。")
    sys.exit()
except KeyError as e:
    print(f"❌ 錯誤：config.json 缺少必要設定值 {e}！")
    sys.exit()
except Exception as e:
    print(f"❌ 讀取 config.json 發生未知錯誤：{e}")
    sys.exit()
# ============================================

class MyBot(commands.Bot):
    def __init__(self):
        # 宣告 Intents
        intents = discord.Intents.default()
        # 必須開啟這項權限，傳統指令 (如 *push) 才能運作
        intents.message_content = True 
        
        # 將傳統指令前綴設定為 *
        super().__init__(command_prefix='*', intents=intents)

    async def setup_hook(self):       
        # ================= 載入所有模組 (Cogs) =================
        try:
            # 載入地震推播與 *push /push 指令
            await self.load_extension('cogs.earthquake')
            print("🔄 [模組] cogs.earthquake 載入完成")
            
            # 載入地牛 Wake Up! 在線人數查詢 (/eewnow)
            await self.load_extension('cogs.eewnow')
            print("🔄 [模組] cogs.eewnow 載入完成")
            
            # 載入單次地震查詢 (/dyfi)
            await self.load_extension('cogs.dyfi')
            print("🔄 [模組] cogs.dyfi 載入完成")
            
            # 載入幫助選單 (/help)
            await self.load_extension('cogs.help')
            print("🔄 [模組] cogs.help 載入完成")
            
            # 載入頻道設定指令 (/add, /remove)
            await self.load_extension('cogs.channel')
            print("🔄 [模組] cogs.channel 載入完成")

            await self.load_extension('cogs.settings')
            print("🔄 [模組] cogs.settings 載入完成")
            
            # 載入擁有者專用指令 (/shutdown, /restart)
            await self.load_extension('cogs.owner')
            print("🔄 [模組] cogs.owner 載入完成")
            
            # 載入關於機器人 (/about)
            await self.load_extension('cogs.about')
            print("🔄 [模組] cogs.about 載入完成")
            
            # 載入邀請網址 (/invite)
            await self.load_extension('cogs.invite')
            print("🔄 [模組] cogs.invite 載入完成")
            
            # 載入 YouTube 直播監控 (/yt)
            await self.load_extension('cogs.yt')
            print("🔄 [模組] cogs.yt 載入完成")

            # 載入地震體感回報推播 (地震發生後 30 分鐘自動發送)
            await self.load_extension('cogs.dyfiReport')
            print("🔄 [模組] cogs.dyfiReport 載入完成")

            await self.load_extension('cogs.kkw')
            print("🔄 [模組] cogs.kkw 載入完成")
            
        except Exception as e:
            print(f"❌ 載入模組時發生錯誤: {e}")
        # ========================================================

        # ================= 同步斜線指令 =================
        # 讓斜線指令立即生效，可在 config.json 中設定 GUILD_IDS 為特定伺服器直接同步
        if GUILD_IDS:
            for guild_id in GUILD_IDS:
                try:
                    guild = discord.Object(id=guild_id)
                    # 先將全域註冊的指令複製到該特定伺服器
                    self.tree.copy_global_to(guild=guild)
                    # 執行同步
                    await self.tree.sync(guild=guild)
                    print(f"🔄 [指令] 斜線指令已瞬間同步至伺服器：{guild_id}")
                except discord.Forbidden:
                    print(f"⚠️ [警告] 無法同步至伺服器 {guild_id} (機器人可能未加入該伺服器，或缺少 application.commands 權限)")
                except discord.HTTPException as e:
                    print(f"⚠️ [警告] 同步至伺服器 {guild_id} 失敗 (Discord API 錯誤): {e}")
                except Exception as e:
                    print(f"❌ 同步至伺服器 {guild_id} 發生未預期的錯誤: {e}")
        else:
            # 如果 config.json 中沒有提供 GUILD_IDS，則執行全域同步，讓你等到下次 M8 都震完一個大序列都還沒顯示出來
            print("🔄 [指令] 尚未設定 GUILD_IDS，準備執行全域指令同步 (需要一段時間才能在 Discord 看到選項)")
            try:
                await self.tree.sync()
                print("🔄 [指令] 全域指令同步完成。")
            except Exception as e:
                 print(f"❌ 全域指令同步發生錯誤: {e}")
        # ================================================

    async def on_ready(self):
        print('====================================')
        print(f'✅ 機器人已成功登入為: {self.user.name} (ID: {self.user.id})')
        print(f'✅ 目前時間: {discord.utils.utcnow().astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")}')
        print('====================================')

# 原神，啟動！
bot = MyBot()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)