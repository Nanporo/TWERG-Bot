import discord
from discord.ext import commands
from discord import app_commands
import sys
import os
from ownercheck import is_owner

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shutdown", description="（限擁有者）關閉 BOT")
    async def shutdown(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ 你沒有權限使用此指令。", ephemeral=True)
            return
            
        await interaction.response.send_message("🛑 正在關閉機器人...", ephemeral=True)
        print("🛑 收到關閉指令，機器人正在關閉...")
        await self.bot.close()

    @app_commands.command(name="restart", description="（限擁有者）重新啟動機器人")
    async def restart(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ 你沒有權限使用此指令。", ephemeral=True)
            return

        await interaction.response.send_message("🔄 正在重新啟動機器人...", ephemeral=True)
        print("🔄 收到重啟指令，機器人正在重新啟動...")
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(OwnerCog(bot))