# 交付包 — Online Image Description System

資料夾：`C:\Users\qwe11\image-description-final`

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `ImageDescriptionServer_STUDENT_IDS.py` | Task 1 交付檔（五個 socket function 已完成；與 Downloads 內運行中嘅 server 檔**完全相同**） |
| `ImageDescriptionClient_STUDENT_IDS.py` | Task 2 交付檔（純 standard library） |
| `Report_STUDENT_IDS.docx` / `.pdf` | 報告草稿（組員資料、截圖位置待補） |
| `tests\check_sockets.py` | 五個 function + 命令流程自動測試 |
| `tests\client_harness.py` | client 對照測試（mock backend，逐行比對格式） |
| `tests\e2e_real_ai.py` | 真 AI 端到端測試（三張圖） |
| `screenshots\` | 報告用截圖（Figure 1–4） |
| `build_report.py` | 由截圖同文字生成 `Report_STUDENT_IDS.docx`（再用 LibreOffice 轉 PDF） |

## 已驗證結果（本機）

- `check_sockets.py`：**40/40 checks passed**，exit 0
- `client_harness.py`：**PASS**（17 步 session、下載 bytes 一致、覆蓋／缺資料夾錯誤、連線被拒 exit 2），exit 0
- `e2e_real_ai.py`：**PASS**，exit 0；真模型 caption：
  - cat.jpg → "In this image we can see a cat lying on the floor."
  - flower.png → "In this image we can see two pink roses and two buds."
  - fruit_bowl.jpg → "In this image there are apples, oranges, pears, and a white bowl."
- `--check-ai .\test_images\cat.jpg`：正常輸出 caption

## 重跑命令（喺 assignment 資料夾執行）

```powershell
cd C:\Users\qwe11\Downloads\image-description-assignment\image-description-assignment

# 1) 驗證五個 function + 命令流程
.\.venv\Scripts\python.exe "C:\Users\qwe11\image-description-final\tests\check_sockets.py" ".\ImageDescriptionServer.py"

# 2) client 對照測試（mock backend）
.\.venv\Scripts\python.exe "C:\Users\qwe11\image-description-final\tests\client_harness.py" --server ".\ImageDescriptionServer.py" --client "C:\Users\qwe11\image-description-final\ImageDescriptionClient_STUDENT_IDS.py"

# 3) 真 AI 端到端（約 1–3 分鐘）
.\.venv\Scripts\python.exe "C:\Users\qwe11\image-description-final\tests\e2e_real_ai.py" --server ".\ImageDescriptionServer.py" --client "C:\Users\qwe11\image-description-final\ImageDescriptionClient_STUDENT_IDS.py"
```

## 報告用截圖（Figure 1–4，要自己機截）

喺 assignment 資料夾開兩個 PowerShell 視窗。

**Figure 1** — environment check（`--check-ai`）：

```powershell
.\.venv\Scripts\python.exe ImageDescriptionServer.py --check-ai .\test_images\cat.jpg
```

見到 "In this image we can see a cat lying on the floor." 之後截圖（連埋上面 setup 完成嗰段更好）。

**Figure 2** — server 視窗：

```powershell
.\.venv\Scripts\python.exe ImageDescriptionServer.py
```

見到 `READY host=0.0.0.0 port=18333` 之後截圖（唔好關窗）。

**Figure 3** — 第二個視窗做一個完整 session：

```powershell
.\.venv\Scripts\python.exe "C:\Users\qwe11\image-description-final\ImageDescriptionClient_STUDENT_IDS.py" 127.0.0.1 18333
```

順次序輸入：

```
UPLOAD
test_images\fruit_bowl.jpg
LIST
DESCRIBE
0000
DOWNLOAD
0000
fruit_bowl_copy.jpg
REMOVE
0000
QUIT
```

出返 prompt 之後截晒成個視窗。

**Figure 4** — 測試結果：重跑上面「重跑命令」1 同 2，見到 `40/40 checks passed` 同 `PASS: client transcript...` 就截圖。

## 交 Canvas 前 Checklist

1. 補組員姓名 / 學號入報告（Table 1），同埋 `STUDENT_IDS` placeholder 改名：
   - `ImageDescriptionServer_<IDs>.py`
   - `ImageDescriptionClient_<IDs>.py`
   - `Report_<IDs>.pdf`
2. 將 Figure 1–4 截圖放入報告 5.4 節（交截圖俾我，我幫你嵌入再出 PDF）。
3. Canvas → People → Groups：加入 `Project Group 001`（或你哋嗰組；一個組員先入空組）。
4. 只交 3 個檔：server `.py`、client `.py`、report `.pdf`。**唔好**交 `models\`、`.venv`、`.tools`、`.runtime`、`setup.log`、任何 exe。
5. Deadline：**2026-11-11 23:59 HKT**。
