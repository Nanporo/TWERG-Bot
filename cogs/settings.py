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

class YTSettingsView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)
        self.all_settings = load_settings()
        
        if self.guild_id not in self.all_settings:
            self.all_settings[self.guild_id] = {}
            
        self.settings = self.all_settings[self.guild_id]
        
        # 若無監控設定則初始化預設值
        if "yt_monitor_enabled" not in self.settings:
            self.settings["yt_monitor_enabled"] = False
        if "yt_target_channel_ids" not in self.settings:
            self.settings["yt_target_channel_ids"] = []
        if "yt_monitor_threshold" not in self.settings:
            self.settings["yt_monitor_threshold"] = 1000

    def build_embed(self) -> discord.Embed:
        """建立 YouTube 監控設定 Embed 排版"""
        embed = discord.Embed(
            title="`🖥️` YouTube 直播監控設定",
            description="調整當前伺服器的 YouTube 觀看人數監控選項。",
            color=0xffffff
        )
        
        status = "`🟢` 已啟用" if self.settings.get("yt_monitor_enabled") else "`🔴` 已停用"
        channel_ids = self.settings.get("yt_target_channel_ids", [])
        channel_status = "\n".join([f"<#{c_id}>" for c_id in channel_ids]) if channel_ids else "⚠️ 尚未設定"
        threshold = self.settings.get("yt_monitor_threshold", 1000)
        
        embed.add_field(name="監控狀態", value=status, inline=False)
        embed.add_field(name="監控發送頻道列表", value=channel_status, inline=False)
        embed.add_field(name="監控變動人數閾值", value=f"增加 {threshold} 人以上", inline=False)
        
        return embed

    @discord.ui.button(label="切換監控狀態", style=discord.ButtonStyle.primary, row=0)
    async def toggle_yt_monitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.settings["yt_monitor_enabled"] = not self.settings.get("yt_monitor_enabled", False)
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        
    @discord.ui.button(label="體感回報設定", style=discord.ButtonStyle.secondary, row=0)
    async def go_to_eq_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsView(self.guild_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="選擇監控發送頻道 (可多選，將覆蓋原設定)", 
        min_values=0,
        max_values=25,
        row=1
    )
    async def select_yt_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.settings["yt_target_channel_ids"] = [c.id for c in select.values]
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.select(
        placeholder="選擇變動人數閾值 (預設 1000)",
        options=[
            discord.SelectOption(label="增加 500 人以上", value="500"),
            discord.SelectOption(label="增加 1000 人以上", value="1000"),
            discord.SelectOption(label="增加 2000 人以上", value="2000"),
            discord.SelectOption(label="增加 5000 人以上", value="5000"),
            discord.SelectOption(label="增加 10000 人以上", value="10000"),
            discord.SelectOption(label="增加 20000 人以上", value="20000"),
            discord.SelectOption(label="增加 50000 人以上", value="50000"),
        ],
        row=2
    )
    async def select_yt_threshold(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.settings["yt_monitor_threshold"] = int(select.values[0])
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="保存", style=discord.ButtonStyle.success, row=3)
    async def finish_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✅ **設定已儲存**", 
            embed=self.build_embed(), 
            view=None
        )
        self.stop()


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
                "min_magnitude": 4.0,
                "auto_dyfi_report": True
            }
        
        self.settings = self.all_settings[self.guild_id]
        
        # 兼容舊版設定檔
        if "target_channel_ids" not in self.settings:
            self.settings["target_channel_ids"] = []
            if self.settings.get("target_channel_id"):
                self.settings["target_channel_ids"].append(self.settings["target_channel_id"])
                
        # 兼容設定檔，確保新功能有預設值
        if "auto_dyfi_report" not in self.settings:
            self.settings["auto_dyfi_report"] = True

    def build_embed(self) -> discord.Embed:
        """根據當前設定建立 Embed 排版"""
        embed = discord.Embed(
            title="`⚙️` 伺服器地震推送設定",
            description="調整當前伺服器的地震推送選項。",
            color=0xff3846
        )
        
        # 解析狀態
        auto_push_status = "`🟢` 已啟用" if self.settings.get("auto_push") else "`🔴` 已停用"
        auto_dyfi_status = "`🟢` 已啟用" if self.settings.get("auto_dyfi_report", True) else "`🔴` 已停用"
        channel_ids = self.settings.get("target_channel_ids", [])
        channel_status = "\n".join([f"<#{c_id}>" for c_id in channel_ids]) if channel_ids else "⚠️ 尚未設定"
        min_mag = self.settings.get("min_magnitude", 4.0)
        
        embed.add_field(name="自動推送狀態", value=auto_push_status, inline=False)
        embed.add_field(name="30分鐘後初步統計", value=auto_dyfi_status, inline=False)
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
        
    @discord.ui.button(label="切換初步統計", style=discord.ButtonStyle.primary, row=0)
    async def toggle_auto_dyfi(self, interaction: discord.Interaction, button: discord.ui.Button):
        """切換是否發送30分鐘後初步統計"""
        current_status = self.settings.get("auto_dyfi_report", True)
        self.settings["auto_dyfi_report"] = not current_status
        
        # 儲存並更新介面
        self.all_settings[self.guild_id] = self.settings
        save_settings(self.all_settings)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        
    @discord.ui.button(label="監控設定", style=discord.ButtonStyle.secondary, row=0)
    async def go_to_yt_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = YTSettingsView(self.guild_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

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
        await interaction.response.edit_message(
            content="✅ **設定已儲存**", 
            embed=self.build_embed(), 
            view=None
        )
        self.stop()

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="（限管理員）調整伺服器的地震自動推送設定")
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