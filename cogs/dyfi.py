import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timezone, timedelta
import asyncio
import io
import os
import logging

def draw_dyfi_map_sync(town_cdi, eq_no="未知", mag="未知", depth="未知", total_reports=0, stats_time="無資料", eq_time="未知"):
    """
    同步函數：使用 geopandas 與 matplotlib 繪製體感回報地圖。
    為確保執行緒安全，使用 Matplotlib 物件導向 API 繪製。
    需要安裝：pip install geopandas matplotlib
    """
    # 關閉 matplotlib 字型尋找過程的警告，避免跨平台時找不到特定字型而導致終端機洗版
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

    try:
        import geopandas as gpd
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        from matplotlib.lines import Line2D
    except ImportError:
        print("⚠️ [地圖產生器] 缺少 geopandas 或 matplotlib 套件，無法繪製地圖。請執行: pip install geopandas matplotlib")
        return None

    # 自動偵測可能的檔名，支援 TopoJSON 與 GeoJSON
    possible_files = ["towns.topo.json", "tw_towns.topo.json", "tw_towns.geojson"]
    map_path = next((f for f in possible_files if os.path.exists(f)), None)
    
    if not map_path:
        print("⚠️ [地圖產生器] 找不到地圖檔案！")
        print("👉 請從 https://github.com/dkaoster/taiwan-atlas 取得 towns.topo.json 放在機器人目錄。")
        return None

    try:
        # 針對 TopoJSON 明確指定 layer 避免警告，並移除 driver 參數以避免底層 pyogrio 報錯
        kwargs = {}
        if "topo" in map_path.lower():
            kwargs["layer"] = "towns"
        gdf = gpd.read_file(map_path, **kwargs)
    except Exception as e:
        print(f"⚠️ [地圖產生器] 讀取 {map_path} 失敗: {e}")
        return None

    # 震度對應顏色 (參考標準配色)
    grade_colors = {
        "0": "#464f5c", "1": "#6bba6b", "2": "#00aaff", "3": "#0041ff",
        "4": "#fae696", "5-": "#ffe600", "5弱": "#ffe600", "5+": "#ff9900",
        "5強": "#ff9900", "6-": "#ff2800", "6弱": "#ff2800", "6+": "#a50021",
        "6強": "#a50021", "7": "#b40068"
    }

    county_col = next((col for col in gdf.columns if col.upper() in ['COUNTY', 'COUNTYNAME', 'C_NAME', 'COUNTY_ID']), None)
    town_col = next((col for col in gdf.columns if col.upper() in ['TOWN', 'TOWNNAME', 'T_NAME', 'TOWN_ID']), None)

    fig = Figure(figsize=(6, 8), facecolor='#0f1113')
    canvas = FigureCanvas(fig)
    ax = fig.add_subplot(1, 1, 1, facecolor='#0f1113')
    ax.set_axis_off()

    # 1. 繪製陸地背景與鄉鎮邊界
    gdf.plot(ax=ax, color='#1a1d20', edgecolor='#22262a', linewidth=0.3)

    # 2. 融合圖層並繪製縣市邊界
    if county_col:
        counties = gdf.dissolve(by=county_col)
        counties.boundary.plot(ax=ax, edgecolor='#4a5260', linewidth=0.8)

    # 3. 繪製體感回報圓點
    if county_col and town_col:
        xs, ys, colors = [], [], []
        
        # 為了提升比對成功率，將地圖資料中的「臺」統一轉換為「台」並去除前後空白
        match_county = gdf[county_col].fillna("").astype(str).str.replace('臺', '台').str.strip()
        match_town = gdf[town_col].fillna("").astype(str).str.replace('臺', '台').str.strip()
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # 忽略地理坐標系計算中心點時的警告
            for data in town_cdi:
                c_name = data.get("countyName", "").replace("臺", "台").strip()
                t_name = data.get("townName", "").replace("臺", "台").strip()
                color = grade_colors.get(str(data.get("grade", "0")), "#F0F0F0")
                mask = (match_county == c_name) & (match_town == t_name)
                if mask.any():
                    centroid = gdf[mask].geometry.centroid.iloc[0]
                    xs.append(centroid.x)
                    ys.append(centroid.y)
                    colors.append(color)
        if xs:
            ax.scatter(xs, ys, c=colors, s=50, edgecolors='#1a1d20', linewidths=0.6, zorder=5)

    # 4. 繪製圖例 (Legend)
    legend_labels = [
        ("0", "#464f5c"), ("1", "#6bba6b"), ("2", "#00aaff"), ("3", "#0041ff"),
        ("4", "#fae696"), ("5-", "#ffe600"), ("5+", "#ff9900"),
        ("6-", "#ff2800"), ("6+", "#a50021"), ("7", "#b40068")
    ]
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=lbl, markerfacecolor=c, 
               markersize=7, markeredgecolor='#1a1d20', markeredgewidth=0.6, linestyle='None') 
        for lbl, c in legend_labels
    ]
    ax.legend(handles=legend_elements, loc='lower right', facecolor='#1a1d20', edgecolor='#22262a', labelcolor='white', framealpha=0.9, fontsize=9, ncol=1)

    # 5. 加入左上角地震資訊與免責文字標示
    info_text = f"編號 {eq_no}\n規模 芮氏 {mag}\n深度 {depth} 公里\n發生時間 {eq_time}\n回報總數 {total_reports} 筆"
    ax.text(0.04, 0.96, info_text, transform=ax.transAxes, 
            color='white', alpha=0.75, fontsize=10, 
            va='top', ha='left', 
            fontfamily=['PingFang TC', 'Heiti TC', 'Microsoft JhengHei', 'Noto Sans CJK TC', 'WenQuanYi Zen Hei', 'sans-serif']
    )
    
    # 6. 加入左下角統計資訊
    report_info_text = f"www.twerg.org\n體感回報由公眾自願提供，僅供參考\n回報統計時間 {stats_time}"
    ax.text(0.04, 0.04, report_info_text, transform=ax.transAxes, 
            color='white', alpha=0.75, fontsize=10, 
            va='bottom', ha='left', 
            fontfamily=['PingFang TC', 'Heiti TC', 'Microsoft JhengHei', 'Noto Sans CJK TC', 'WenQuanYi Zen Hei', 'sans-serif']
    )

    # 調整地理坐標系視覺比例 (修復經緯度直接繪製導致的水平扁平感)
    ax.set_aspect(1.1)

    # 鎖定台灣本島與澎湖，過濾過遠外島讓地圖主題清晰
    ax.set_xlim(119.3, 122.2)
    ax.set_ylim(21.8, 25.4)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    return buf

async def generate_dyfi_message(eq_data):
    """將指定的地震資料轉換為 Discord 訊息與 Embed 的輔助函數"""
    current_no = eq_data.get('EarthquakeNo')
    eq_info = eq_data.get('EarthquakeInfo', {})
    origin_time_str = eq_info.get('OriginTime', '')
    magnitude = eq_info.get('EarthquakeMagnitude', {}).get('MagnitudeValue', '未知')
    focal_depth = eq_info.get('FocalDepth', '未知')
    
    # 轉換時間戳記
    try:
        tw_tz = timezone(timedelta(hours=8))
        dt = datetime.strptime(origin_time_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=tw_tz)
        discord_time = f"<t:{int(dt.timestamp())}:f>"
    except ValueError:
        discord_time = origin_time_str

    # 獨立抓取體感回報資料
    dyfi_url = f"https://www.twerg.org/api/dyfi-reports?eq_no={current_no}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(dyfi_url) as dyfi_response:
                if dyfi_response.status == 200:
                    dyfi_data = await dyfi_response.json()
                else:
                    dyfi_data = {}
    except Exception:
        dyfi_data = {}

    meta = dyfi_data.get("meta", {})
    total_reports = meta.get("totalReports", 0)
    valid_reports = meta.get("validReports", 0)
    calibrated_at_str = meta.get("calibratedAt", "")
    
    if calibrated_at_str:
        try:
            # 處理 API 回傳的 ISO 8601 格式時間並轉為時間戳
            calibrated_dt = datetime.fromisoformat(calibrated_at_str.replace("Z", "+00:00"))
            calibrated_discord_time = f"<t:{int(calibrated_dt.timestamp())}:f>"
            map_stats_time = calibrated_dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            calibrated_discord_time = calibrated_at_str
            map_stats_time = calibrated_at_str
    else:
        calibrated_discord_time = "無資料"
        map_stats_time = "無資料"

    town_cdi = dyfi_data.get("townCDI", [])
    map_file = None
    if town_cdi:
        # 過濾異常警告的資料
        town_cdi = [town for town in town_cdi if str(town.get("anomalyWarning", 0)) != "1"]
        
        # 獨立在背景執行緒中產生圖片，避免阻塞 Discord 機器人
        loop = asyncio.get_running_loop()
        map_buf = await loop.run_in_executor(None, draw_dyfi_map_sync, town_cdi, current_no, magnitude, focal_depth, total_reports, map_stats_time, origin_time_str)
        
        if map_buf:
            map_file = discord.File(fp=map_buf, filename="dyfi_map.png")

        # 依據 grade 權重與精準的體感震度 cdi 值由大到小排序，並取出前 8 筆
        grade_order = {"7": 10, "6強": 9, "6+": 9, "6弱": 8, "6-": 8, "5強": 7, "5+": 7, "5弱": 6, "5-": 6, "4": 5, "3": 4, "2": 3, "1": 2, "0": 1}
        town_cdi.sort(key=lambda x: (grade_order.get(str(x.get("grade", "0")), 0), x.get("cdi", 0.0)), reverse=True)
        grade_map = {
            "0": "⚫", 
            "1": "⚪", 
            "2": "🟢", 
            "3": "🔵", 
            "4": "🟡", 
            "5-": "🟠", "5弱": "🟠", 
            "5+": "🟤", "5強": "🟤", 
            "6-": "🔴", "6弱": "🔴", 
            "6+": "🟣", "6強": "🟣", 
            "7": "🛑"
            }
        top_towns = []
        for town in town_cdi[:8]:
            grade = str(town.get("grade", "0"))
            emoji = grade_map.get(grade, "⚫")
            fw_grade = grade.translate(str.maketrans("01234567-+", "０１２３４５６７－＋"))
            grade_text = fw_grade if any(c in grade for c in ["弱", "強", "-", "+"]) else f"{fw_grade}級"
            suspect_mark = " `⚠️`" if town.get("isSuspect") else ""
            top_towns.append(f"`{emoji}` {grade_text}　{town.get('countyName', '')} {town.get('townName', '')}{suspect_mark}")
        towns_value = "\n".join(top_towns) if top_towns else "目前無符合條件的回報資料"
    else:
        towns_value = "目前無回報資料"

    # Embed 內容
    report_url = f"https://www.twerg.org/dyfi?eq={current_no}"
    message_content = f"📝 體感回報填寫（{current_no}）"
    
    embed = discord.Embed(title="顯著有感地震報告", description=report_url, color=0x3498db)
    embed.add_field(name="編號", value=str(current_no), inline=True)
    embed.add_field(name="規模", value=f"芮氏 {magnitude}", inline=True)
    embed.add_field(name="深度", value=f"{focal_depth} 公里", inline=True)
    embed.add_field(name="發生時間", value=discord_time, inline=False)
    embed.add_field(name="📊 回報數量", value=f"{total_reports} 筆", inline=True)
    embed.add_field(name="✅ 認可數量", value=f"{valid_reports} 筆", inline=True)
    embed.add_field(name="🕓 體感回報統計時間", value=calibrated_discord_time, inline=False)
    embed.add_field(name="最大回報內容", value=towns_value, inline=False)
    embed.set_footer(text=f"地震資訊請以中央氣象署發佈為準。")
    
    if map_file:
        embed.set_image(url="attachment://dyfi_map.png")
    
    return message_content, embed, map_file

class DyfiView(discord.ui.View):
    def __init__(self, earthquakes, current_index, counts):
        super().__init__(timeout=300)
        self.earthquakes = earthquakes[:8]
        self.current_index = current_index
        self.counts = counts
        self.selected_no = str(self.earthquakes[self.current_index].get('EarthquakeNo'))
        self.update_components()

    def update_components(self):
        self.clear_items()

        options = []
        for eq in self.earthquakes:
            eq_no = eq.get('EarthquakeNo')
            eq_info = eq.get('EarthquakeInfo', {})
            mag = eq_info.get('EarthquakeMagnitude', {}).get('MagnitudeValue', '未知')
            time_str = eq_info.get('OriginTime', '')
            try:
                short_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").strftime("%m-%d %H:%M")
            except ValueError:
                short_time = time_str[:16]
                
            count = self.counts.get(eq_no, 0)
            options.append(discord.SelectOption(
                label=f"編號 {eq_no}",
                description=f"規模 {mag} | {short_time} | 回報: {count}筆",
                value=str(eq_no),
                default=(str(eq_no) == self.selected_no)
            ))
            
        select = discord.ui.Select(placeholder="選擇近期其他地震報告...", min_values=1, max_values=1, options=options, row=0)
        async def select_callback(interaction: discord.Interaction):
            self.selected_no = select.values[0]
            idx = next((i for i, eq in enumerate(self.earthquakes) if str(eq.get('EarthquakeNo')) == self.selected_no), self.current_index)
            await self.change_page(interaction, idx)
        select.callback = select_callback
        self.add_item(select)
        
        display_no = str(self.earthquakes[self.current_index].get('EarthquakeNo'))
        btn_dyfi_form = discord.ui.Button(label="體感回報表單", url=f"https://www.twerg.org/dyfi?eq={display_no}", style=discord.ButtonStyle.link, row=2)
        self.add_item(btn_dyfi_form)

        btn_recent_reports = discord.ui.Button(label="最近地震報告", url="https://www.twerg.org/reports", style=discord.ButtonStyle.link, row=2)
        self.add_item(btn_recent_reports)

    async def change_page(self, interaction: discord.Interaction, new_index: int):
        await interaction.response.defer()
        if 0 <= new_index < len(self.earthquakes):
            self.current_index = new_index
            selected_eq = self.earthquakes[self.current_index]
            self.selected_no = str(selected_eq.get('EarthquakeNo'))
            
            content, embed, map_file = await generate_dyfi_message(selected_eq)
            self.update_components()
            
            kwargs = {'content': content, 'embed': embed, 'view': self}
            if map_file:
                kwargs['attachments'] = [map_file]
            else:
                kwargs['attachments'] = []
            await interaction.edit_original_response(**kwargs)

class DyfiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 讀取 API Key
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.api_key = config['CWA_API_KEY']

    @app_commands.command(name="dyfi", description="查詢近期顯著有感地震的體感回報報告")
    async def dyfi(self, interaction: discord.Interaction):
        # 避免 API 回應過慢導致超時報錯
        await interaction.response.defer()
        
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={self.api_key}&format=JSON"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send(f"⚠️ API 請求失敗，狀態碼：{response.status}")
                        return

                    data = await response.json()
                    earthquakes = data.get('records', {}).get('Earthquake', [])
                    
                    if not earthquakes:
                        await interaction.followup.send("⚠️ 目前找不到任何地震資料。")
                        return

                    # 取最新的一筆資料
                    latest_earthquake = earthquakes[0]
                    current_no = latest_earthquake.get('EarthquakeNo')
                    
                    if current_no is None:
                        await interaction.followup.send("⚠️ 找不到最新的地震編號資料。")
                        return
                        
                    # 同步獲取前 8 筆地震資料的體感回報數量
                    async def fetch_count(eq_no):
                        dyfi_url = f"https://www.twerg.org/api/dyfi-reports?eq_no={eq_no}"
                        try:
                            async with session.get(dyfi_url) as dyfi_res:
                                if dyfi_res.status == 200:
                                    dyfi_json = await dyfi_res.json()
                                    return eq_no, dyfi_json.get("meta", {}).get("totalReports", 0)
                        except Exception:
                            pass
                        return eq_no, 0
                    
                    tasks = [fetch_count(eq.get('EarthquakeNo')) for eq in earthquakes[:8]]
                    results = await asyncio.gather(*tasks)
                    counts = dict(results)

                    # 產生預設最新一筆的 Embed 畫面
                    content, embed, map_file = await generate_dyfi_message(latest_earthquake)
                    # 產生包含近期 8 筆地震選單與切換按鈕的 View 控制項
                    view = DyfiView(earthquakes, 0, counts)
                    
                    if map_file:
                        await interaction.followup.send(content=content, embed=embed, view=view, file=map_file)
                    else:
                        await interaction.followup.send(content=content, embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：{e}")
            print(f"❌ /dyfi 發生未預期的錯誤：{e}")

async def setup(bot):
    await bot.add_cog(DyfiCog(bot))