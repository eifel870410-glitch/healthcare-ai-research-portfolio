# 個人化病人衛教生成系統：EHR + RAG + Local LLaMA 3.2

這是一個可在 VS Code 本機執行的期末專案原型。目標是把 EHR 中的診斷與用藥資訊，對接醫院核可衛教單，透過 RAG 讓本機 LLaMA 3.2 產生有引用來源的個人化衛教報告。

## 1. 專案功能

- 從 EHR CSV 讀取 `subject_id`、ICD-10、診斷、用藥。
- 讀取 `data/leaflets/*.txt` 衛教單並建立向量索引。
- 使用 similarity search 找出最相關的衛教單。
- 呼叫本機 Ollama `llama3.2` 產生繁體中文個人化衛教內容。
- 強制模型只能根據檢索內容生成，並在重點後加入 `[來源1]` 這類引用。
- 輸出 Markdown、Word `.docx` 報告與 trace JSON。
- 提供 retrieval Hit@K 評估腳本。

## 2. 資料夾結構

```text
patient_edu_rag/
├── app.py
├── evaluate.py
├── requirements.txt
├── data/
│   ├── ehr/patients_demo.csv
│   └── leaflets/*.txt
├── outputs/
├── reports/
└── patient_edu_rag/
    ├── config.py
    ├── data_loader.py
    ├── retriever.py
    ├── generator.py
    ├── report.py
    └── pipeline.py
```

## 3. VS Code 執行步驟

### Step 1：安裝 Python 套件

建議 Python 3.10 或 3.11。

```bash
cd patient_edu_rag
python -m venv .venv
```

Windows PowerShell：

```bash
.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
source .venv/bin/activate
```

安裝套件：

```bash
pip install -r requirements.txt
```

### Step 2：安裝 Ollama 與 LLaMA 3.2

先安裝 Ollama，然後在終端機執行：

```bash
ollama pull llama3.2
ollama serve
```

如果 Ollama 已經在背景執行，`ollama serve` 可能會提示 port 已被使用，這通常代表服務已啟動。

### Step 3：建立向量索引

```bash
python app.py index --reset
```

### Step 4：產生個人化衛教報告

```bash
python app.py generate --subject-id 10001
```

輸出會出現在：

- `outputs/patient_10001_education_report.md`
- `reports/patient_10001_education_report.docx`
- `outputs/patient_10001_trace.json`

如果你還沒裝 Ollama，但想先測流程：

```bash
python app.py generate --subject-id 10001 --no-ollama
```

### Step 5：跑 retrieval 評估

```bash
python evaluate.py
```

會輸出 `outputs/retrieval_eval.csv` 與 Hit@K 指標。

## 4. 如何換成你的正式資料

### EHR CSV 欄位

把正式資料放到 `data/ehr/patients_demo.csv`，至少需要：

```csv
subject_id,icd10_codes,diagnoses,prescriptions,age,sex
```

若你用 MIMIC-IV，通常會先從 diagnoses、prescriptions 等表格彙整成每位病人一列。

### 衛教單

把 225 份衛教單轉成 `.txt`，放到 `data/leaflets/`。建議格式：

```text
TITLE: 糖尿病與 Metformin 用藥衛教
SOURCE: Hospital Approved Leaflet DM-001
正文內容...
```

更換資料後請重建索引：

```bash
python app.py index --reset
```

## 5. 安全限制設計

`generator.py` 的 prompt 已加入以下限制：

- 只能根據核可衛教內容回答。
- 未涵蓋內容要寫「目前提供的衛教單未涵蓋」。
- 每個重要建議需標註 `[來源X]`。
- 以繁體中文、病人可理解的方式輸出。

## 6. 期末簡報可對應的技術重點

- Stage 1 Feature Extraction：`data_loader.py`
- Stage 2 Vector Retrieval：`retriever.py`
- Stage 3 Controlled Generation：`generator.py`
- Stage 4 Report Output：`report.py`
- Evaluation：`evaluate.py`

## 7. 常見問題

### 無法連到 Ollama

確認：

```bash
ollama list
ollama pull llama3.2
```

若仍失敗，可先用：

```bash
python app.py generate --subject-id 10001 --no-ollama
```

### 第一次建立索引很慢

第一次會下載 multilingual sentence-transformer embedding model，屬正常現象。下載完成後會快很多。

