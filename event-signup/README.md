# 活動報名系統

Python 3.10+、Flask、SQLite、Jinja；保留 events / registrations / attendees 分工架構。

## Windows PowerShell 安裝及啟動

在解壓縮後的 event-signup 資料夾開啟 PowerShell：

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m flask --app app init-db
.\venv\Scripts\python.exe -m flask --app app run --debug
```

開啟 http://127.0.0.1:5000/，停止按 Ctrl+C。不必啟用 venv 或修改 ExecutionPolicy。
若 py 無法執行，請改用已安裝的 python 或真正 python.exe 的完整路徑執行第一行；WindowsApps 啟動別名不一定代表已安裝可執行的 Python。
macOS / Linux 用 python3 -m venv venv，之後以 venv/bin/python 執行相同命令。

## 既有專案更新：保留資料

先停止伺服器，以 git status --short 與 git diff 確認未提交修改，逐檔合併變更。
保留 event_signup.db、venv 與組員修改，不要直接覆蓋整個資料夾。
下載壓縮檔不含資料庫或虛擬環境，不會自動 commit / push。

在既有專案資料夾執行：

```powershell
if (Test-Path .\event_signup.db) {
    $backupStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Copy-Item -LiteralPath .\event_signup.db -Destination ".\event_signup-$backupStamp.db.bak"
}
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m flask --app app migrate-db
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m flask --app app run --debug
```

migrate-db 新增身分查詢索引與重複報名 INSERT / UPDATE 防護觸發器，採交易執行，可重複執行。
不刪表、不清空或改寫資料。即使舊資料已有重複報名，也保留全部舊紀錄，只阻擋新的重複寫入；人數顯示實際紀錄數。
若資料庫尚不存在，請改用 init-db，它會建立資料表並安裝相同防護，對現有標準資料表執行也不刪資料。
舊資料表須包含 schema.sql 中的欄位；若來自其他結構，請先比對。遷移失敗會回滾並提示。

## 選用範例資料

```powershell
.\venv\Scripts\python.exe -m flask --app app seed-db
```

沒有活動時寫入 3 筆活動與 3 筆報名；活動日期依當下往後推算，避免範例一開始就過期。
已有活動時略過，不覆蓋資料。資料庫位於專案根目錄 event_signup.db，不應提交 Git。

## 日期與報名規則

- 新增活動：名稱必填且最多 100 個字元；說明最多 2000 個字元；兩個時間均必填。
- 新活動必須使用 YYYY-MM-DDTHH:MM，一律解讀為台灣時間 UTC+8；不接受只有日期、錯誤日期或另帶時區的表單值。
- 活動開始時間、截止時間不能早於現在；截止時間不能晚於開始，允許相等。
- 舊資料只有 YYYY-MM-DD 時，明確視為台灣時間當日 00:00，當天已開始後不能報名。
- 舊資料附時區時換算台灣時間；空白、錯誤或前後矛盾的時間會顯示異常並暫停報名。
- 到達截止瞬間即停止報名（現在時間 >= 截止時間）；活動已開始也不接受報名。
- 前端提供 min / max、必填及格式提示；後端獨立驗證，等待資料庫鎖後再次檢查時間及關閉狀態。
- 姓名去除前後空白後必填，最多 50 個字元。電話為 09 開頭的 10 個 ASCII 數字；前後空白會去除。
- 同一活動「姓名及電話都相同」才算重複；不同姓名同電話、同姓名不同電話、不同活動相同資料均可報名。
- 交易鎖及資料庫觸發器防止重複點擊、同時送出造成重複紀錄。資料庫失敗回滾，表單提示並保留輸入。
- 活動列表與報名清單顯示實際人數；無資料為 0。報名時間固定顯示台灣時間，不依賴主機時區。
- 清單的「手動關閉報名」會隱藏入口，後端也阻擋 GET / POST；沒有重新開放功能。
- 關閉使用 POST 與 session 防偽 token。本專案維持原本無登入的課堂操作模式，能開啟清單者即可操作關閉。
- SQL 參數化、Jinja 預設跳脫；輸入 HTML 只作文字顯示。字元長度依 HTML maxlength 的 UTF-16 計數方式，讓前後端一致。
- 無效網址、方法、過大請求、資料庫例外提供提示及返回連結；資料庫失敗回應 HTTP 503。
- 手機表格可在卡片內左右滑動，避免姓名、電話及整頁溢出。

## 網址對照

| 網址 | 方法 | 功能 | 實作 |
|---|---|---|---|
| / | GET | 活動清單 | routes/events.py |
| /events/new | GET / POST | 新增活動 | routes/events.py |
| /events/<id>/close | POST | 手動關閉報名 | routes/events.py |
| /events/<id>/register | GET / POST | 活動報名 | routes/registrations.py |
| /events/<id>/attendees | GET | 報名清單 | routes/attendees.py |

SECRET_KEY 環境變數可設定 session / flash 金鑰；未設定時使用課堂開發預設值。

## 自動測試

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

測試用獨立暫存資料庫，不操作現有 event_signup.db。
涵蓋截止邊界、舊資料、重複與併發報名、關閉、回滾、保留資料遷移、人數、無效參數與 XSS / SQL 輸入。

## 人工驗收

1. 新增未來活動，截止時間在現在與開始之間；確認成功提示與列表的 0 人。
2. 輸入過去時間、空值、截止晚於開始，確認前端阻擋；停用 JavaScript / 直接 POST 也被後端拒絕。
3. 報名「小明 / 0912345678」，清單為 1 人；再送同組資料提示重複且人數不變。
4. 不同姓名同電話、同姓名不同電話應可報名；不同活動可用同組資料報名。
5. 手動關閉後入口隱藏，重訪先前網址或送出先前開著的報名表都不能新增。
6. 新增數分鐘後截止的活動，保留報名頁等到截止後送出，確認阻擋且人數不增加。
7. 測試不存在網址的 404 與返回連結；空活動清單、無報名清單正常。
8. 縮到 320 / 375 像素寬，檢查新增、報名及清單；表格內可滑動，整頁不水平溢出。
