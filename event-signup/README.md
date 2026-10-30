# 活動報名系統（event-signup）

Python Flask + SQLite 的活動報名系統。

## 安裝

```powershell
cd event-signup
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## 初始化資料庫（第一次執行前）

```powershell
.\venv\Scripts\python.exe -m flask --app app init-db
```

會在專案目錄建立 `event_signup.db`。

## 範例資料（選用）

```powershell
.\venv\Scripts\python.exe -m flask --app app seed-db
```

寫入 3 筆範例活動和幾筆報名，讓每個人都有一樣的測試資料。
資料庫已經有活動時會自動略過，不會覆蓋或重複寫入。

> `event_signup.db` 不會進 git，每個人的資料是各自獨立的。
> 想要從頭來過：刪掉 `event_signup.db`，再執行 `seed-db`（它會順便建立資料表）。

## 啟動

```powershell
.\venv\Scripts\python.exe -m flask --app app run --debug
```

開啟瀏覽器進入 <http://127.0.0.1:5000/>。

> 也可以先啟用 venv（`.\venv\Scripts\Activate.ps1`）再直接打 `flask --app app run`。
> 若 Windows 的「應用程式控制」擋下 `flask.exe`，請改用上面的 `python -m flask` 寫法。

## 設定

| 環境變數 | 說明 | 預設值 |
|---|---|---|
| `SECRET_KEY` | Flask session / flash 使用的金鑰 | 開發用預設值，正式環境務必設定 |

## 網址對照

| 網址 | 方法 | 功能 | 檔案 |
|---|---|---|---|
| `/` | GET | 活動清單 | `routes/events.py` |
| `/events/new` | GET / POST | 新增活動 | `routes/events.py` |
| `/events/<id>/register` | GET / POST | 活動報名表 | `routes/registrations.py` |
| `/events/<id>/attendees` | GET | 報名清單 | `routes/attendees.py` |

## 測試

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## 尚未實作

- 截止報名檢查（`events.deadline`、`events.is_closed` 欄位已保留）
- 重複報名檢查
