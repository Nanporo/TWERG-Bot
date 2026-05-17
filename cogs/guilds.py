import discord
from discord.ext import commands
from discord import app_commands
import json
from ownercheck import is_owner

class GuildsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guilds", description="（限擁有者）顯示機器人加入的伺服器列表與狀態")
    async def guilds_command(self, interaction: discord.Interaction):
        # 權限檢查
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ 你沒有權限使用此指令。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        guilds = self.bot.guilds
        # 依照伺服器人數由大到小排序
        sorted_guilds = sorted(guilds, key=lambda g: g.member_count, reverse=True)
        total_members = sum(g.member_count for g in guilds)
        
        # 讀取設定檔統計活躍狀態
        try:
            with open('guild_settings.json', 'r', encoding='utf-8') as f:
                guild_settings = json.load(f)
        except Exception:
            guild_settings = {}
            
        active_push_count = sum(1 for g in guilds if str(g.id) in guild_settings and guild_settings[str(g.id)].get("auto_push", False))

        embed = discord.Embed(
            title="🤖 機器人伺服器狀態",
            description=f"`{len(guilds)}` 群組數\n`{total_members}` 面向使用者數\n`{active_push_count}` 個伺服器已開啟自動推送",
            color=0x2ecc71
        )

        # 避免超過 Embed 上限，僅顯示前 10 大伺服器
        display_count = 10
        for i, guild in enumerate(sorted_guilds[:display_count]):
            g_settings = guild_settings.get(str(guild.id), {})
            marks = ""
            if g_settings.get("auto_push", False):
                marks += "📨 "
            if g_settings.get("yt_monitor_enabled", False):
                marks += "🖥️"
                
            embed.add_field(
                name=f"{i+1} : {guild.name} {marks}".strip(),
                value=f"ID: `{guild.id}`\n人數: {guild.member_count} 人",
                inline=False
            )

        embed.set_footer(text=f"隱藏了其他 {max(0, len(guilds) - display_count)} 個伺服器..." if len(guilds) > display_count else "已列出所有伺服器。")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GuildsCog(bot))