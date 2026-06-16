import discord
from discord.ext import commands
from discord import app_commands
import math

class IntensityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def calc_cwa(self, pga, pgv):
        # 台灣 CWA 震度分級 (2020年新制)
        if pga < 0.8: return "0級 (無感)"
        elif pga < 2.5: return "1級 (微震)"
        elif pga < 8.0: return "2級 (輕震)"
        elif pga < 25.0: return "3級 (弱震)"
        elif pga < 80.0: return "4級 (中震)"
        else:
            if pgv is None:
                return "5弱或以上 (需提供 PGV 計算)"
            if pgv < 15: return "4級 (中震)"
            elif pgv < 30: return "5弱 (強震)"
            elif pgv < 50: return "5強 (強震)"
            elif pgv < 80: return "6弱 (烈震)"
            elif pgv < 140: return "6強 (烈震)"
            else: return "7級 (劇震)"

    def calc_jma(self, pga):
        # 日本 JMA 震度 (以經驗公式 I = 2.0 * log10(PGA) + 0.94 約略估算)
        if pga <= 0: return "0"
        ir = 2.0 * math.log10(pga) + 0.94
        if ir < 0.5: return "0"
        elif ir < 1.5: return "1"
        elif ir < 2.5: return "2"
        elif ir < 3.5: return "3"
        elif ir < 4.5: return "4"
        elif ir < 5.0: return "5弱"
        elif ir < 5.5: return "5強"
        elif ir < 6.0: return "6弱"
        elif ir < 6.5: return "6強"
        else: return "7"

    def calc_mmi(self, pga, pgv, sa03=None, sa10=None):
        # 美國 USGS 震度 (MMI, 使用 Worden et al. 2012 連續經驗公式)
        def _get_mmi(value, mtype):
            if value <= 0: return 1.0
            l_val = math.log10(value)
            if mtype == 'pga':
                mmi = 1.78 + 1.55 * l_val
                if mmi >= 5.0: mmi = -1.58 + 3.48 * l_val
            elif mtype == 'pgv':
                mmi = 3.78 + 1.47 * l_val
                if mmi >= 5.0: mmi = 2.89 + 3.16 * l_val
            elif mtype == 'sa03':
                mmi = 1.40 + 1.25 * l_val
                if mmi >= 5.0: mmi = -3.22 + 3.39 * l_val
            elif mtype == 'sa10':
                mmi = 3.82 + 1.20 * l_val
                if mmi >= 5.0: mmi = 1.62 + 3.34 * l_val
            return mmi

        hf_vals = []
        if pga and pga > 0: hf_vals.append(_get_mmi(pga, 'pga'))
        if sa03 and sa03 > 0: hf_vals.append(_get_mmi(sa03, 'sa03'))
        
        lf_vals = []
        if pgv and pgv > 0: lf_vals.append(_get_mmi(pgv, 'pgv'))
        if sa10 and sa10 > 0: lf_vals.append(_get_mmi(sa10, 'sa10'))

        hf_mmi = max(hf_vals) if hf_vals else 1.0
        lf_mmi = max(lf_vals) if lf_vals else 1.0

        # 依 USGS ShakeMap 邏輯，低震度由高頻 (PGA/Sa03) 主導，高震度由低頻 (PGV/Sa10) 主導
        if not lf_vals: final_mmi = hf_mmi
        elif not hf_vals: final_mmi = lf_mmi
        elif hf_mmi < 5.0 and lf_mmi < 5.0: final_mmi = hf_mmi
        elif hf_mmi >= 5.0 and lf_mmi >= 5.0: final_mmi = lf_mmi
        else: final_mmi = max(hf_mmi, lf_mmi)

        if final_mmi < 1.5: return "I (無感)"
        elif final_mmi < 3.5: return "II-III (微弱-弱)"
        elif final_mmi < 4.5: return "IV (中等)"
        elif final_mmi < 5.5: return "V (中度)"
        elif final_mmi < 6.5: return "VI (強)"
        elif final_mmi < 7.5: return "VII (非常強)"
        elif final_mmi < 8.5: return "VIII (嚴重)"
        elif final_mmi < 9.5: return "IX (猛烈)"
        else: return "X 或以上 (極猛烈)"

    def calc_peis(self, pga, pgv):
        # 菲律賓 PHIVOLCS 震度 (PEIS, 共 10 級，數值常與 MMI 相似)
        if pgv and pgv >= 3.4:
            if pgv < 8.1: return "V (強)"
            elif pgv < 16: return "VI (非常強)"
            elif pgv < 31: return "VII (破壞性)"
            elif pgv < 60: return "VIII (嚴重破壞)"
            elif pgv < 116: return "IX (毀滅性)"
            else: return "X (完全毀滅)"
        else:
            if pga < 1.66: return "I (幾乎無感)"
            elif pga < 13.72: return "II-III (微弱-弱)"
            elif pga < 38.22: return "IV (中等)"
            elif pga < 90.16: return "V (強)"
            elif pga < 176.4: return "VI (非常強)"
            elif pga < 333.2: return "VII (破壞性)"
            elif pga < 637.0: return "VIII (嚴重破壞)"
            elif pga < 1215.2: return "IX (毀滅性)"
            else: return "X (完全毀滅)"

    def calc_cenc(self, pga, pgv):
        # 中國 CENC (GB/T 17742-2020)
        if pgv and (pga >= 5 or pgv >= 0.5):
            if pgv < 1: return "IV度"
            elif pgv < 2: return "V度"
            elif pgv < 5: return "VI度"
            elif pgv < 10: return "VII度"
            elif pgv < 20: return "VIII度"
            elif pgv < 39: return "IX度"
            elif pgv < 78: return "X度"
            elif pgv < 156: return "XI度"
            else: return "XII度"
        else:
            if pga < 1: return "I度"
            elif pga < 2: return "II度"
            elif pga < 5: return "III度"
            elif pga < 11: return "IV度"
            elif pga < 22: return "V度"
            elif pga < 44: return "VI度"
            elif pga < 90: return "VII度"
            elif pga < 177: return "VIII度"
            elif pga < 353: return "IX度"
            elif pga < 707: return "X度"
            elif pga < 1414: return "XI度"
            else: return "XII度"

    def calc_ems98(self, pga):
        # 歐洲 EMSC (EMS-98, 約略 PGA 分布)
        if pga < 1: return "I"
        elif pga < 2: return "II"
        elif pga < 5: return "III"
        elif pga < 15: return "IV"
        elif pga < 30: return "V"
        elif pga < 60: return "VI"
        elif pga < 120: return "VII"
        elif pga < 250: return "VIII"
        elif pga < 500: return "IX"
        elif pga < 1000: return "X"
        elif pga < 2000: return "XI"
        else: return "XII"

    @app_commands.command(name="intensity", description="透過輸入 PGA 和 PGV 大約換算各國地震震度")
    @app_commands.describe(
        pga="最大地動加速度 PGA (gal 或 cm/s²)", 
        pgv="最大地動速度 PGV (cm/s，可選，有助於高震度準確性)",
        sa03="0.3秒頻譜加速度 Sa(0.3s) (gal，可選，輔助 MMI 準確度)",
        sa10="1.0秒頻譜加速度 Sa(1.0s) (gal，可選，輔助 MMI 準確度)"
    )
    async def intensity_command(
        self, 
        interaction: discord.Interaction, 
        pga: app_commands.Range[float, 0.0, 5000.0], 
        pgv: app_commands.Range[float, 0.0, 5000.0] = None, 
        sa03: app_commands.Range[float, 0.0, 5000.0] = None, 
        sa10: app_commands.Range[float, 0.0, 5000.0] = None
    ):

        try:
            cwa = self.calc_cwa(pga, pgv)
            jma = self.calc_jma(pga)
            mmi = self.calc_mmi(pga, pgv, sa03, sa10)
            cenc = self.calc_cenc(pga, pgv)
            ems98 = self.calc_ems98(pga)
            peis = self.calc_peis(pga, pgv)

            embed = discord.Embed(
                title="震度換算結果 (約略值)",
                color=0x3498db
            )
            
            pgv_str = f"{pgv} cm/s" if pgv is not None else "未提供"
            sa03_str = f"\n`Sa(0.3s): {sa03} gal`" if sa03 is not None else ""
            sa10_str = f"\n`Sa(1.0s): {sa10} gal`" if sa10 is not None else ""
            embed.description = f"**輸入數值**\n`PGA: {pga} gal`\n`PGV: {pgv_str}`{sa03_str}{sa10_str}"

            embed.add_field(name="🇹🇼 臺灣 CWA", value=cwa, inline=True)
            embed.add_field(name="🇯🇵 日本 JMA", value=jma, inline=True)
            embed.add_field(name="🇺🇸 美國 USGS (MMI)", value=mmi, inline=True)
            embed.add_field(name="🇨🇳 中國 CENC", value=cenc, inline=True)
            embed.add_field(name="🇪🇺 歐洲 EMSC", value=ems98, inline=True)
            embed.add_field(name="🇵🇭 菲律賓 PEIS", value=peis, inline=True)

            embed.set_footer(text="⚠️ 本換算採用各國參考經驗公式，僅供粗略換算參考。\n實際震度會受儀器頻率響應、觀測站環境等多重因素影響。")

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ 發生未預期的錯誤：{e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(IntensityCog(bot))