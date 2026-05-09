import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# =============================================================================
# 這個檔案負責處理頻道設定相關的指令，例如 /add 和 /remove，讓管理員可以將頻道加入或移除自動推送的列表中。
# =============================================================================

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

class ChannelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add", description="（限管理員）將目前頻道加入自動推送的頻道列表")
    @app_commands.default_permissions(administrator=True) # 限管理員可用
    async def add_channel(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ 此指令只能在伺服器當中使用。", ephemeral=True)
            return
            
        settings = load_settings()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in settings:
            settings[guild_id] = {
                "auto_push": False,
                "target_channel_ids": [],
                "min_magnitude": 4.0
            }
            
        guild_setting = settings[guild_id]
        
        # 兼容舊版設定檔
        if "target_channel_ids" not in guild_setting:
            guild_setting["target_channel_ids"] = []
            if guild_setting.get("target_channel_id"):
                guild_setting["target_channel_ids"].append(guild_setting["target_channel_id"])
                
        channel_id = interaction.channel.id
        
        if channel_id in guild_setting["target_channel_ids"]:
            await interaction.response.send_message("⚠️ 此頻道已經在自動推送列表中了。", ephemeral=True)
            return
            
        guild_setting["target_channel_ids"].append(channel_id)
        settings[guild_id] = guild_setting
        save_settings(settings)
        
        await interaction.response.send_message(f"✅ 已將 <#{channel_id}> 加入自動推送頻道列表。", ephemeral=True)

    @app_commands.command(name="remove", description="（限管理員）將目前頻道從自動推送的頻道列表中移除")
    @app_commands.default_permissions(administrator=True) # 限管理員可用
    async def remove_channel(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ 此指令只能在伺服器當中使用。", ephemeral=True)
            return
            
        settings = load_settings()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in settings:
            await interaction.response.send_message("⚠️ 尚未設定任何推送頻道。", ephemeral=True)
            return
            
        guild_setting = settings[guild_id]
        
        # 兼容舊版設定檔
        if "target_channel_ids" not in guild_setting:
            guild_setting["target_channel_ids"] = []
            if guild_setting.get("target_channel_id"):
                guild_setting["target_channel_ids"].append(guild_setting["target_channel_id"])
                
        channel_id = interaction.channel.id
        
        if channel_id not in guild_setting["target_channel_ids"]:
            await interaction.response.send_message("⚠️ 此頻道不在自動推送列表中。", ephemeral=True)
            return
            
        guild_setting["target_channel_ids"].remove(channel_id)
        settings[guild_id] = guild_setting
        save_settings(settings)
        
        await interaction.response.send_message(f"✅ 已將 <#{channel_id}> 從自動推送頻道列表中移除。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChannelCog(bot))