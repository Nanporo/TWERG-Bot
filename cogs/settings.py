import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# 定義儲存各伺服器設定的檔案路徑
SETTINGS_FILE = 'guild_settings.json'

def load_settings():
    """讀取伺服器設定檔"""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    """寫入伺服器設定檔"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class SettingsView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None) # 取消 Timeout，讓設定面板持續有效
        self.guild_id = str(guild_id)
        self.all_settings = load_settings()
        
        # 若該伺服器尚未有設定，初始化預設值
        if self.guild_id not in self.all_settings:
            self.all_settings[self.guild_id] = {
                "auto_push": False,
                "target_channel_ids": [],
                "min_magnitude": 4.0
            }
        
        self.settings = self.all_settings[self.guild_id]
        
        # 兼容舊版設定檔
        if "target_channel_ids" not in self.settings:
            self.settings["target_channel_ids"] = []
            if self.settings.get("target_channel_id"):
                self.settings["target_channel_ids"].append(self.settings["target_channel_id"])

    def build_embed(self) -> discord.Embed:
        """根據當前設定建立 Embed 排版"""
        embed = discord.Embed(
            title="⚙️ 伺服器地震推送設定",
            description="調整當前伺服器的地震推送選項。",
            color=0x2b2d31
        )
        
        # 解析狀態
        auto_push_status = "🟢 已開啟" if self.settings.get("auto_push") else "🔴 已關閉"
        channel_ids = self.settings.get("target_channel_ids", [])
        channel_status = "\n".join([f"<#{c_id}>" for c_id in channel_ids]) if channel_ids else "⚠️ 尚未設定"
        min_mag = self.settings.get("min_magnitude", 4.0)
        
        embed.add_field(name="自動推送狀態", value=auto_push_status, inline=False)
        embed.add_field(name="推送目標頻道列表", value=channel_status, inline=False)
        embed.add_field(name="最低推送規模", value=f"芮氏 {min_mag}", inline=False)
        
        return embed

    @discord.ui.button(label="切換自動推送", style=discord.ButtonStyle.primary, row=0)
    async def toggle_auto_push(self, interaction: discord.Interaction, button: discord.ui.Button):
        """切換是否自動推送地震回報"""
        current_status = self.settings.get("auto_push", False)
        self.settings["auto_push"] = not current_status
        
        # 儲存並更新介面
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="選擇推送目標頻道 (可多選，將覆蓋原設定)", 
        min_values=0,
        max_values=25,
        row=1
    )
    async def select_target_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        """選擇推送頻道"""
        self.settings["target_channel_ids"] = [c.id for c in select.values]
        
        # 儲存並更新介面
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.select(
        placeholder="選擇最低推送規模",
        options=[
            discord.SelectOption(label="規模 4.0 以上", value="4.0"),
            discord.SelectOption(label="規模 4.5 以上", value="4.5"),
            discord.SelectOption(label="規模 5.0 以上", value="5.0"),
            discord.SelectOption(label="規模 5.5 以上", value="5.5"),
            discord.SelectOption(label="規模 6.0 以上", value="6.0"),
        ],
        row=2
    )
    async def select_min_magnitude(self, interaction: discord.Interaction, select: discord.ui.Select):
        """選擇觸發推送的最低規模"""
        self.settings["min_magnitude"] = float(select.values[0])
        
        # 儲存並更新介面
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="保存", style=discord.ButtonStyle.success, row=3)
    async def finish_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """其實沒有特別作用的確認按鈕"""
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(
            content="✅ **設定已儲存**", 
            embed=self.build_embed(), 
            view=self
        )
        self.stop()

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="調整伺服器的地震自動推送設定")
    @app_commands.default_permissions(administrator=True) # 限管理員可用
    async def settings_command(self, interaction: discord.Interaction):
        # 確認指令是在伺服器內使用
        if not interaction.guild:
            await interaction.response.send_message("❌ 此指令只能在伺服器當中使用。", ephemeral=True)
            return
            
        # 初始化 View 與 Embed
        view = SettingsView(interaction.guild.id)
        embed = view.build_embed()
        
        # 傳送設定面板 (設為 ephemeral=True 代表僅有呼叫的管理員能看見與操作)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingsCog(bot))