# TWERG 體感震度地圖渲染器 接入說明

> 適用於 TWERG-Bot，`dyfi_map.py` 渲染器的安裝與使用教學。

---

## 一、專案資料夾結構

請確認你的 TWERG-Bot 資料夾長這樣：

```
TWERG-Bot/
├── bot.py
├── config.json
├── cogs/
│   ├── dyfi_map.py       ← 地圖渲染器（放這裡）
│   └── （其他 cog 檔案）
└── fonts/
    ├── HarmonyOS_SansTC_Regular.ttf
    ├── HarmonyOS_SansTC_Bold.ttf
    ├── HarmonyOS_SansTC_Medium.ttf
    ├── HarmonyOS_SansTC_Light.ttf
    ├── HarmonyOS_SansTC_Semibold.ttf
    ├── HarmonyOS_SansTC_Thin.ttf
    └── HarmonyOS_SansTC_Black.ttf
```

`fonts/` 資料夾和 `cogs/` 資料夾要放在**同一層**（都在 TWERG-Bot 根目錄下）。

---

## 二、安裝必要套件

在 TWERG-Bot 根目錄，打開終端機（命令提示字元）執行：

```
pip install matplotlib geopandas shapely pillow
```

### Windows 注意事項

`geopandas` 在 Windows 有時裝不起來。如果出錯，改用以下兩個方案擇一：

**方案 A — Anaconda（推薦）**
1. 下載安裝 [Anaconda](https://www.anaconda.com/download)
2. 打開 Anaconda Prompt，切換到專案目錄
3. 執行：`conda install geopandas`，再執行 `pip install discord.py`

**方案 B — 手動裝 GDAL**
1. 先去 [OSGeo4W](https://trac.osgeo.org/osgeo4w/) 下載安裝
2. 安裝完再回來執行 `pip install geopandas`

### macOS 注意事項

先安裝 Homebrew，再執行：
```
brew install gdal
pip install matplotlib geopandas shapely pillow
```

### Linux（Ubuntu / Debian）

```
pip install matplotlib geopandas shapely pillow
```

---

## 三、安裝確認

安裝完後，用 Python 執行以下確認有無錯誤：

```python
import matplotlib
import geopandas
import shapely
from PIL import Image
print("全部 OK")
```

---

## 四、在 Discord Bot 裡使用

### 基本呼叫方式

在你的檔案最上方加入：

```python
from cogs.dyfi_map import render_map
```

然後在指令裡這樣用：

```python
@app_commands.command(name='dyfi', description='顯示體感震度地圖')
async def dyfi(self, interaction: discord.Interaction, eq_no: str):
    await interaction.response.defer()

    img_path = render_map(eq_no)

    await interaction.followup.send(file=discord.File(img_path))
```

---

### 有震央資訊的呼叫方式

如果你已經從氣象署 API 取得震央座標，可以一起帶進去：

```python
img_path = render_map(
    eq_no     = '115017',
    epicenter = {'lat': 23.97, 'lon': 121.6},
    eq_type   = 'significant',   # 'significant' / 'small' / 'unknown'
)
```

`eq_type` 對應顯示文字：
- `'significant'` → 顯著有感（紅色）
- `'small'`       → 小區域有感
- `'unknown'`     → 未報告地震

---

### 指定輸出路徑（避免多人同時使用蓋掉彼此的檔案）

```python
import os, time

img_path = render_map(
    eq_no       = eq_no,
    output_path = f'temp/map_{eq_no}_{int(time.time())}.png'
)

await interaction.followup.send(file=discord.File(img_path))

os.remove(img_path)   # 傳完刪掉，不佔空間
```

記得先建立 `temp/` 資料夾，或在 bot 啟動時加上：

```python
os.makedirs('temp', exist_ok=True)
```

---

### 完整範例

```python
import os, time, discord
from discord import app_commands
from discord.ext import commands
from cogs.dyfi_map import render_map

class DYFIMap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='dyfi', description='產生體感震度地圖')
    @app_commands.describe(eq_no='地震編號，例如 115017')
    async def dyfi(self, interaction: discord.Interaction, eq_no: str):
        await interaction.response.defer()

        try:
            img_path = render_map(
                eq_no       = eq_no,
                output_path = f'temp/map_{eq_no}_{int(time.time())}.png'
            )
            await interaction.followup.send(file=discord.File(img_path))
            os.remove(img_path)

        except Exception as e:
            await interaction.followup.send(f'地圖產生失敗：{e}')

async def setup(bot):
    await bot.add_cog(DYFIMap(bot))
```

---

## 問題

**Q：地圖上沒有圓圈?**
A：表示該地震編號在 TWERG 資料庫裡還沒有回報資料，或 eq_no 格式錯誤。

**Q：中文顯示亂碼或方框?**
A：確認 `fonts/` 資料夾裡有放 `HarmonyOS_SansTC_*.ttf` 字型檔，且字型資料夾的位置在 `cogs/` 的上一層。
