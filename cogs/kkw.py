import discord
from discord.ext import commands
from discord import app_commands

class KKWView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=300)
        self.author_id = author_id

    @discord.ui.button(label="關閉", style=discord.ButtonStyle.secondary, emoji="❌")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author_id:
            await interaction.response.defer()
            await interaction.message.delete()
        else:
            await interaction.response.send_message("❌ 只有該訊息的使用者可以關閉此訊息。", ephemeral=True)

class KKWCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kkw", description="計算地震規模相等於多少顆原子彈的能量")
    @app_commands.describe(magnitude="輸入地震規模 (例如: 6.0)")
    async def kkw_command(self, interaction: discord.Interaction, magnitude: app_commands.Range[float, 3.5, 10.0]):

        # E = 2^((M - 6.2) / 0.2)
        e = 2 ** ((magnitude - 6.2) / 0.2)
        
        # 將結果四捨五入到小數點後 4 位，避免浮點數誤差產生過長的數字
        e_rounded = round(e, 4)
        # 如果小數點後都是 0（例如 2.0），則轉換為整數顯示以保持美觀
        e_display = int(e_rounded) if e_rounded == int(e_rounded) else e_rounded
        
        message_content = f"M `{magnitude}` = **{e_display}** 顆原子彈\n> -# 計算公式 E = 2^((M - 6.2) / 0.2)，僅供參考"
        view = KKWView(interaction.user.id)
        await interaction.response.send_message(content=message_content, view=view)

async def setup(bot):
    await bot.add_cog(KKWCog(bot))