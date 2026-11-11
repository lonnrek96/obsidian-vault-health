# Obsidian Vault Health

[English](README.md) | 繁體中文

唯讀的 Obsidian 健康檢查工具，可作為 Agent Skill 使用。檢查失效的內部連結、缺失的標題與區塊 ID、YAML 格式錯誤，以及有歧義的筆記引用。也能比較整理前後的檢查結果，全程不修改筆記。

不需要帳號、Obsidian 外掛、API key，也不必開啟 Obsidian。檢查程式不發送網路請求，也不改寫 vault 內的檔案。

## 在本機試用

需要 Python 3.9 以上版本。請在 vault 外建立獨立環境，並於本專案目錄執行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/obsidian-vault-health/requirements.txt
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json
```

Windows 請將 `.venv/bin/python` 換成 `.venv\Scripts\python.exe`。
安裝依賴時可能連線至套件來源；檢查程式本身在本機執行。
結束碼 `1` 代表發現錯誤，請閱讀標準輸出的報告，不代表程式崩潰。若將輸出儲存為報告，請放在 vault 外。

## 安裝為 Skill

以 **Codex 與 Claude Code** 為目標，兩者共用同一份 Skill 指令與 Python 檢查程式。將完整的 `skills/obsidian-vault-health` 資料夾複製到以下任一專案位置：

| 工具 | 安裝後的 Skill 檔案位置 | 手動呼叫方式 |
| --- | --- | --- |
| Codex | `.agents/skills/obsidian-vault-health/SKILL.md` | `$obsidian-vault-health` |
| Claude Code | `.claude/skills/obsidian-vault-health/SKILL.md` | `/obsidian-vault-health` |

請保留 `SKILL.md`、`scripts`、`references`、`agents` 與 `requirements.txt` 的完整結構，複製前先確認是否已有同名安裝。Python 依賴請依上方方式安裝於獨立環境。
選用的 `agents/openai.yaml` 提供 Codex 顯示資訊，共用檢查流程不依賴這個檔案。

Codex 使用範例：

```text
$obsidian-vault-health 檢查 "/path/to/vault" 的筆記庫，列出失效連結與缺失的標題或區塊，不要修改任何筆記。
```

Claude Code 使用範例：

```text
/obsidian-vault-health 檢查 "/path/to/vault" 的筆記庫，列出失效連結與缺失的標題或區塊，不要修改任何筆記。
```

安裝位置與呼叫方式依據 [Codex 官方文件](https://learn.chatgpt.com/docs/build-skills)及 [Claude Code 官方文件](https://code.claude.com/docs/en/skills)。
共用 Python 檢查器已通過本機合成資料測試；尚未驗證在 Codex 與 Claude Code 內實際啟用 Skill 的流程，其他工具與作業系統也尚未驗證。

## 選用檢查與報告

```sh
# 僅對指定資料夾啟用專案索引中繼資料檢查。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --projects-dir Projects --json

# 與同一個 vault、相同檢查選項的先前私人報告比較。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --baseline "/path/to/private/before.json" --json

# 移除筆記名稱、連結目標與自由文字細節，再人工審閱是否適合分享。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json --redact
```

`--inbox-dir Inbox` 啟用帶日期筆記的存放時間提醒。
`--local-root` 明確允許檢查指定目錄中、位於 vault 外的本機連結目標是否存在，預設不啟用。
工具不要求特定的 vault 資料夾結構。完整行為與限制請見 [reporting.md](skills/obsidian-vault-health/references/reporting.md)。

## 隱私

本倉庫僅應包含程式碼、使用指令與合成資料測試。請勿加入真實筆記、報告、截圖、設定、備份、帳號資料或憑證。
一般報告可能包含私人筆記名稱與外部本機路徑，請保留在本機。分享前請使用 `--redact`，再人工檢查結果；移除這些欄位不代表輸出已完全匿名。

檢查器不執行筆記內容，也不擷取網頁。隱藏項目與符號連結會略過。
它不驗證 Obsidian 實際呈現的介面、所有 Markdown 擴充語法、JavaScript、Dataview 或 Bases 查詢。

## 開發

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

測試使用暫存的合成 vault，涵蓋連結與錨點檢查、基準報告比較、唯讀操作、明確的本機存取範圍、報告去識別化與私人資料邊界。請勿以真實個人筆記取代測試資料。

## 授權

MIT。本專案為獨立專案，與 Obsidian 無隸屬關係。
