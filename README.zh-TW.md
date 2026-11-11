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

### 快速安裝到專案

下載本倉庫後，在倉庫目錄執行以下指令，同時安裝給兩種工具：

```sh
python3 install.py --project "/path/to/project" --agent both --venv "/path/outside-vault/health-env"
```

專案目錄必須已存在，環境路徑必須是新的，並放在 vault 外。
指令會建立獨立環境、安裝 PyYAML，並將完整 Skill 複製到兩種工具的專案目錄。
只安裝一種工具時，改用 `--agent codex` 或 `--agent claude-code`。
若已有同名 Skill，安裝工具會停止，請先人工審閱再決定如何更新。
安裝不會啟動 AI 工具或模型；下載依賴需要網路。

若已有包含 PyYAML 的 Python 環境，可使用不下載套件的方式：

```sh
python3 install.py --project "/path/to/project" --agent both --python "/path/to/environment/python"
```

安裝工具會在安裝目錄寫入被 Git 忽略的 `runtime.json`，記錄本機 Python 位置，供 AI 工具讀取。
這個檔案含有本機路徑，請勿分享。Windows 若沒有 `python3` 指令，可改用 `python`。

### 手動安裝

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

## 範例報告

[示範 vault](examples/vault) 完全由虛構筆記組成，包含兩篇筆記與兩個刻意保留的錯誤：一個缺失筆記、一個缺失標題。

- [English report](examples/report.en.md)
- [繁體中文報告](examples/report.zh-TW.md)

```sh
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault examples/vault --markdown --language zh-TW
```

## 選用檢查與報告

```sh
# 僅對指定資料夾啟用專案索引中繼資料檢查。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --projects-dir Projects --json

# 與同一個 vault、相同檢查選項的先前私人報告比較。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --baseline "/path/to/private/before.json" --json

# 移除筆記名稱、連結目標與自由文字細節，再人工審閱是否適合分享。
.venv/bin/python skills/obsidian-vault-health/scripts/check.py --vault "/path/to/vault" --json --redact
```

使用 `--exclude Private --exclude Imports`，可在讀取前排除指定檔案或整個資料夾。
路徑相對於 vault，不支援萬用字元。明確指向排除區的連結會標示為未驗證；簡短 wikilink 仍可能無法解析。
使用基準報告時，排除設定必須一致。

使用 `--markdown --language zh-TW` 或 `--markdown --language en` 產生易讀報告與建議檢視順序。
問題代碼與技術細節仍為英文。任何輸出格式都可搭配 `--summary-only`，僅輸出統計，不含筆記名稱與連結目標。
統計模式不可作為基準報告。各種格式都保留原本的結束碼；私人報告請儲存於 vault 外。

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

## 自動檢查與驗證狀態

[GitHub Actions 設定](.github/workflows/check.yml) 會執行測試、專案安裝流程、Skill 格式驗證與常見機密格式掃描，
目標環境為 Linux、macOS、Windows，搭配 Python 3.9 與 3.13。
加入設定不代表遠端工作已通過；實際驗證狀態與兩種工具的測試步驟見[驗證說明](docs/verification.md)。
格式掃描無法保證找出所有機密，也不掃描 Git 歷史或你的 vault。

## 授權

MIT。本專案為獨立專案，與 Obsidian 無隸屬關係。
