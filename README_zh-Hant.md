# Uber Eats for Home Assistant

在 Home Assistant 裡追蹤你的 Uber Eats 訂單 —— 訂單狀態、外送員位置、外送員照片、餐廳名稱,
全部變成可以拿來寫自動化的實體。

> **使用本整合的風險由你自行承擔。** 它用你的 session cookie 呼叫 Uber Eats 未公開的 API,
> 上游隨時可能改變格式而不另行通知。

[English README](README.md)

## 來源與致謝

本專案衍生自 [**tsunglung/UberEats**](https://github.com/tsunglung/UberEats),
原作者為 [@tsunglung](https://github.com/tsunglung) —— 這個整合的骨架與所有做得好的地方
都是他寫的。原專案採 MIT 授權,授權條款與著作權聲明原封不動延續,見 [LICENSE](LICENSE)。

本 repository 從上游的 `512c57f` 分歧。在那之前的每一個 commit 都是 tsunglung 的,
**原作者身分與 commit hash 都保持不變**,所以你可以自行比對驗證這份程式碼的基底確實來自上游。

它以獨立 repository 而非 GitHub fork 的形式維護,理由記錄在
[docs/adr/0001-standalone-repo-not-fork.md](docs/adr/0001-standalone-repo-not-fork.md)。

## 這個分支改了什麼

| 改動 | 為什麼重要 |
|---|---|
| **偵測靜默過期的 session,並觸發重新驗證** | `sid` cookie 過期時,Uber Eats API 回的是 `HTTP 200` 加一個空的 payload,**不是 `403`**。上游的過期判斷因此永遠不會觸發,`binary_sensor.new_order` 就一直卡在 `False`,而且完全沒有錯誤訊息。本分支改為檢查回應結構、丟出 `ConfigEntryAuthFailed`,讓 Home Assistant 跳出重新驗證的提示,直接貼上新 cookie 即可 —— 不用移除再重新加入整合。 |
| **修正新版 Home Assistant 的選項流程** | 在較新的版本按「設定」會噴 500。 |
| **閒置時不再出現 `HTTP 400`** | 外送員圖片實體原本會退回一個 Wikipedia 的預設圖網址,而該網址會拒絕 Home Assistant 的請求 —— 沒有訂單時每次輪詢都在寫錯誤日誌。 |
| **移除沒有用到的 `requests` 依賴** | 整合全程使用 `aiohttp`,`requests` 只是宣告了但從未使用。 |
| **從兩個 cookie 簡化為一個** | 第二個 cookie 的備援機制從未如預期運作,只是讓設定變得更麻煩。 |

## 系統需求

**Home Assistant 2024.12 以上。** 選項流程依賴框架提供的 `OptionsFlow.config_entry` 屬性,
該屬性在 2024.12 之前並不存在 —— 舊版可以安裝,但一按「設定」就會出現 `AttributeError`。

## 安裝

**用 HACS** —— HACS → 整合 → 右上角 ⋮ → 自訂儲存庫 →
網址填 `kalijason/UberEats`,類別選 `Integration`。安裝後重新啟動 Home Assistant。

**手動安裝** —— 把 `custom_components/uber_eats/` 複製到你設定資料夾(例如 `/config`)底下的
`custom_components/` 目錄,然後重新啟動。

## 前置作業

### 1. 取得你的 `sid` cookie

整合是用瀏覽器裡的 session cookie 驗證身分。它大約一個月後過期,到時候要重做一次這個步驟。

1. 開啟 [ubereats.com](https://www.ubereats.com/) 並登入。
2. 打開開發者工具 —— <kbd>F12</kbd>,或 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>I</kbd>
   (macOS 是 <kbd>⌘</kbd>+<kbd>⌥</kbd>+<kbd>I</kbd>)。
3. 切到 **應用程式 (Application)** 分頁 → **儲存空間 (Storage)** → **Cookies** →
   `https://www.ubereats.com`。
4. 找到名稱為 **`sid`** 的 cookie。如果有多筆,選第一筆。
5. 複製 **值 (Value)** 欄位的完整字串 —— 很長,以 `QA.` 開頭、`=` 結尾。

**請把這串字當成密碼看待**,它等同於你 Uber Eats 帳號的存取權。

### 2. 加入整合

1. **設定 → 裝置與服務 → 新增整合 → Uber Eats**。
   如果清單裡沒有,重新整理網頁;還是沒有的話,清除瀏覽器快取。
2. 輸入帳號名稱與 `sid` cookie,所有欄位都是必填。

設定完成後就可以建立自動化,例如把外送進度廣播到通訊軟體或 HomePod mini。

## Cookie 過期時

整合的卡片上會出現**重新驗證**的提示 —— 點開貼上新的 `sid` 即可。不需要移除再重新加入,
實體 ID 也不會改變。

想手動處理的話:**設定 → 裝置與服務 → Uber Eats → 設定**。

## 實體

| 實體 | 內容 |
|---|---|
| `sensor.uber_eats_<account>_orders` | 進行中的訂單數,以及所有解析出來的訂單屬性 |
| `binary_sensor.uber_eats_<account>_new_order` | 目前是否有進行中的訂單 |
| `device_tracker.uber_eats_<account>_courier` | 外送員的即時 GPS 位置 |
| `image.uber_eats_<account>_courier` | 外送員照片 |
| `button.uber_eats_<account>_order` | 強制下一次輪詢真的去打 API |

## 授權

MIT —— 見 [LICENSE](LICENSE)。Copyright © 2021 tsunglung。
