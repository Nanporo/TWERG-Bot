# TWERG BOT

## 關於 / About

**TWERG BOT** 是地牛記錄小組的 Discord 機器人。
主要功能為自動推送地震體感回報網址，並附帶一些實用的地震相關簡易功能。

**TWERG BOT** is a Discord bot for TWERG.
Its main purpose is to automatically push [TWERG's "Did You Feel It?"](https://www.twerg.org/reports) (體感回報) URLs for earthquakes, along with some concise and useful earthquake-related features. 

## 功能 / Features

### 自動推送地震報告 Automated Earthquake Report

- 當有顯著有感地震發生時，自動將報告及體感回報連結推送到指定的伺服器頻道。
- Automatically pushes significant earthquake reports and "Did You Feel It?" URLs to designated server channels.

### 自訂的推送設定 Customizable Push Settings

- 管理員可以自訂要自動推送的頻道以及觸發推送的最低地震規模。
- Server Administrators can easily configure the auto-push toggle, target channels, and minimum magnitude threshold via an interactive UI panel.

### 即時查詢 Real-time Query
- 手動查詢最新一筆地震資料，以及體感回報網址。
- Manually query the latest earthquake data.

### YouTube 直播監控
- 監控 YouTube 上的地震監視直播人數（預設為[台灣地震監視](https://www.youtube.com/@%E5%8F%B0%E7%81%A3%E5%9C%B0%E9%9C%87%E7%9B%A3%E8%A6%96)）
- Monitor the viewers in the earthquake live streams on YouTube.

## 自行部署 / Self-Hosting

### 環境需求 (Prerequisites)

- `python 3.12`
- `git`

### 安裝步驟 (Installation)

**複製本專案 (Clone the repository)**
```bash
git clone https://github.com/Nanporo/TWERG-Bot.git
cd TWERG-Bot
```

**安裝所需套件 (Install dependencies)**
```bash
pip install discord.py
```

### 設定檔 (Configuration)

調整 `config.json` 

```
- `DISCORD_TOKEN`: Discord 機器人 Token
- `CWA_API_KEY`: 中央氣象署開放資料平臺 申請的 API 金鑰
- `OWNER_ID`: 自己的 Discord 使用者 ID，用於執行擁有者限定指令 (如 /shutdown)
- `GUILD_IDS`: (選填) Discord 伺服器 ID 列表。用於即時同步斜線指令，若留空則會進行全域同步 (會等到天荒地老)
```

### 執行 (Run the bot)
```bash
python bot.py
```

## 指令列表 / Commands

### 一般指令 / General Commands
- `/about` - 顯示關於 TWERG BOT 的資訊 / Show information about TWERG BOT
- `/dyfi` - 查詢最新一筆顯著有感地震報告並取得體感回報連結 / Query the latest significant earthquake report and get the "Did You Feel It" link
- `/help` - 顯示使用幫助與可用指令清單 / Show help and available commands
- `/invite` - 取得地牛記錄小組的 Discord 邀請網址 / Get the Discord invite link for TWERG
- `/yt` - 查詢 YouTube 上的地震監視直播人數 / Query the number of viewers in the earthquake live streams on YouTube


### 管理員指令 / Administrator Commands (Requires Admin Permissions)
- `/add` - 將目前頻道加入自動推送列表 / Add the current channel to the auto-push list
- `/remove` - 將目前頻道從自動推送列表移除 / Remove the current channel from the auto-push list
- `/settings` - 調整機器人設定/ Modify BOT settings

### 擁有者指令 / Bot Owner Commands (Requires Bot Owner Status)
- `/push` - 強制推送最新的一筆地震報告 / Force push the latest earthquake report
- `/shutdown` - 關閉機器人 / Shutdown
- `/restart` - 重新啟動機器人 / Restart

## 免責聲明 / Disclaimer

機器人所獲取之資料僅作為參考以及學習用途，機器人作者以及地牛記錄小組不負擔任何責任。

任何地震相關資訊必須以中央氣象署公告為準。

## 其它 / Others

此專案與 地牛Wake Up!、台灣地震監視、中央氣象署並無關聯。
如果您遇到任何問題，請聯絡機器人作者。

This project is not related to OX Wake Up!, Taiwan Earthquake Monitoring Channel and CWA.
If you encounter any issues, please contact the BOT author.

## 相關連結 / Links

- 地牛記錄小組 官方網站 (Official Website): https://www.twerg.org
- 地牛記錄小組 Discord (Discord Server): https://discord.gg/7sacMKp
- Facebook: https://www.facebook.com/earthquakerecording
- Threads: https://www.threads.com/@taiwanerg

## 授權 / License

GNU Affero General Public License
