import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from patient_edu_rag.config import Settings
from patient_edu_rag.pipeline import run_patient


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_NAME = "llama3.2"


# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="個人化病人衛教報告生成系統",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================
# CSS 美化
# =========================
st.markdown(
    """
    <style>
    .main {
        background-color: #ffffff;
    }

    .block-container {
        max-width: 1050px;
        padding-top: 4rem;
        padding-bottom: 4rem;
    }

    .hero-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #1f2937;
    }

    .hero-subtitle {
        text-align: center;
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }

    .welcome-box {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        color: #374151;
        line-height: 1.8;
    }

    .status-pill {
        display: inline-block;
        background-color: #ecfdf5;
        color: #047857;
        border: 1px solid #a7f3d0;
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.9rem;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .warning-pill {
        display: inline-block;
        background-color: #fffbeb;
        color: #92400e;
        border: 1px solid #fde68a;
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.9rem;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .result-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1.5rem;
        margin-top: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }

    div[data-testid="stTextInput"] input {
        font-size: 1.1rem;
        padding: 0.75rem;
    }

    div.stButton > button:first-child {
        height: 3rem;
        border-radius: 12px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 工具函式
# =========================
def warmup_ollama(model=MODEL_NAME, base_url="http://localhost:11434"):
    """
    預先呼叫 Ollama，讓模型載入記憶體。
    """
    url = f"{base_url}/api/generate"

    payload = {
        "model": model,
        "prompt": "請用一句話說明高血壓。",
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "num_predict": 30,
            "temperature": 0.1,
        },
    }

    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    return r.json().get("response", "")


@st.cache_data
def load_patient_list(ehr_csv):
    df = pd.read_csv(ehr_csv)
    df["subject_id"] = df["subject_id"].astype(str)
    return df


def get_latest_docx(subject_id):
    reports_dir = PROJECT_ROOT / "reports"
    if not reports_dir.exists():
        return None

    docx_files = sorted(
        reports_dir.glob(f"patient_{subject_id}_education_report*.docx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return docx_files[0] if docx_files else None


def get_latest_markdown(subject_id):
    outputs_dir = PROJECT_ROOT / "outputs"
    if not outputs_dir.exists():
        return None

    md_files = sorted(
        outputs_dir.glob(f"patient_{subject_id}_education_report*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return md_files[0] if md_files else None


def show_patient_summary(patient):
    st.markdown("### 病人資料摘要")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Subject ID", patient.get("subject_id", ""))

    with c2:
        st.metric("性別", patient.get("gender", ""))

    with c3:
        st.metric("年齡", patient.get("anchor_age", ""))

    with st.expander("查看診斷與用藥資料"):
        st.markdown("**ICD / 診斷碼：**")
        st.write(patient.get("icd10_codes", ""))

        st.markdown("**診斷名稱：**")
        st.write(patient.get("diagnoses", ""))

        st.markdown("**用藥紀錄：**")
        st.write(patient.get("prescriptions", ""))


# =========================
# Session State
# =========================
if "warmup_done" not in st.session_state:
    st.session_state.warmup_done = False

if "warmup_error" not in st.session_state:
    st.session_state.warmup_error = None

if "last_subject_id" not in st.session_state:
    st.session_state.last_subject_id = ""

if "last_elapsed" not in st.session_state:
    st.session_state.last_elapsed = None

if "last_docx_path" not in st.session_state:
    st.session_state.last_docx_path = None

if "last_md_path" not in st.session_state:
    st.session_state.last_md_path = None

if "generation_done" not in st.session_state:
    st.session_state.generation_done = False


# =========================
# 載入設定與病人資料
# =========================
settings = Settings()

try:
    patients_df = load_patient_list(settings.ehr_csv)
    available_ids = patients_df["subject_id"].tolist()
except Exception as e:
    patients_df = pd.DataFrame()
    available_ids = []
    st.error(f"無法讀取病人資料：{e}")


# =========================
# 側邊欄
# =========================
with st.sidebar:
    st.header("系統狀態")
    st.write(f"模型：`{MODEL_NAME}`")
    st.write("執行方式：本機 Ollama")
    st.write("知識庫：225 份醫院核可衛教單")
    st.write("輸出格式：Word 報告 `.docx`")

    st.divider()

    if st.session_state.warmup_done:
        st.success("LLaMA 已暖機")
    elif st.session_state.warmup_error:
        st.error("LLaMA 暖機失敗")
        st.caption(st.session_state.warmup_error)
    else:
        st.info("LLaMA 準備中")

    if st.button("重新暖機 LLaMA"):
        st.session_state.warmup_done = False
        st.session_state.warmup_error = None
        with st.spinner("正在重新暖機 LLaMA..."):
            try:
                warmup_ollama()
                st.session_state.warmup_done = True
                st.success("模型暖機完成")
            except Exception as e:
                st.session_state.warmup_error = str(e)
                st.error(f"暖機失敗：{e}")


# =========================
# 首次開啟自動暖機
# =========================
warmup_placeholder = st.empty()

if not st.session_state.warmup_done and st.session_state.warmup_error is None:
    with warmup_placeholder.container():
        st.info("系統啟動中：正在自動暖機本機 LLaMA 模型，您可以先輸入已授權的 demo Subject ID。")

    try:
        warmup_ollama()
        st.session_state.warmup_done = True
        warmup_placeholder.success("LLaMA 模型已準備完成。")
        time.sleep(0.8)
        warmup_placeholder.empty()
    except Exception as e:
        st.session_state.warmup_error = str(e)
        warmup_placeholder.warning(
            "LLaMA 暖機尚未完成。仍可使用系統，但產生報告前請確認 Ollama 已啟動。"
        )


# =========================
# 主畫面：歡迎區
# =========================
st.markdown(
    """
    <div class="hero-title">🏥 個人化病人衛教報告生成系統</div>
    <div class="hero-subtitle">
        MIMIC-IV Demo × 225 份醫院核可衛教單 × RAG × 本機 LLaMA 3.2
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="welcome-box">
        歡迎使用個人化病人衛教報告生成系統。<br>
        請輸入已授權的 demo Subject ID，系統會自動檢索醫院核可衛教單，
        並透過本機 LLaMA 產生具引用來源的個人化衛教報告。
    </div>
    """,
    unsafe_allow_html=True,
)

status_html = f"""
<span class="status-pill">本機執行</span>
<span class="status-pill">RAG 檢索</span>
<span class="status-pill">Word 報告輸出</span>
<span class="warning-pill">Demo 模型：{MODEL_NAME}</span>
"""
st.markdown(status_html, unsafe_allow_html=True)

st.write("")
st.write("")


# =========================
# 輸入區
# =========================
st.markdown("### 請輸入已授權的 demo Subject ID")

input_col, button_col = st.columns([4, 1])

with input_col:
    subject_id = st.text_input(
        "Subject ID",
        value="",
        placeholder="請輸入已授權的 demo Subject ID",
        label_visibility="collapsed",
    )

with button_col:
    generate_clicked = st.button("產生報告", type="primary", use_container_width=True)

with st.expander("不知道可以輸入哪個 Subject ID？"):
    if available_ids:
        st.write("可測試範例：")
        st.code(", ".join(available_ids[:10]))
    else:
        st.write("目前沒有可用的病人資料。")


# =========================
# 產生報告流程
# =========================
if generate_clicked:
    if not subject_id.strip():
        st.error("請先輸入 Subject ID。")
        st.stop()

    if patients_df.empty:
        st.error("找不到病人資料檔案，無法產生報告。")
        st.stop()

    subject_id = subject_id.strip()
    selected = patients_df[patients_df["subject_id"] == subject_id]

    if selected.empty:
        st.error("找不到這個 demo Subject ID，請確認輸入是否正確。")
        st.stop()

    patient = selected.iloc[0]

    st.divider()
    show_patient_summary(patient)

    st.divider()

    welcome_box = st.empty()
    progress_box = st.empty()

    welcome_box.info("歡迎使用個人化衛教報告生成系統，正在準備本機 LLaMA 模型...")

    try:
        start_time = time.time()

        if not st.session_state.warmup_done:
            with st.spinner("模型暖機中..."):
                warmup_ollama()
                st.session_state.warmup_done = True

        progress_box.info("模型已準備完成，正在檢索 225 份衛教單並產生報告...")

        with st.spinner("RAG 檢索與 LLaMA 生成中，請稍候..."):
            run_patient(subject_id, use_ollama=True)

        elapsed = time.time() - start_time

        latest_docx = get_latest_docx(subject_id)
        latest_md = get_latest_markdown(subject_id)

        st.session_state.last_subject_id = subject_id
        st.session_state.last_elapsed = elapsed
        st.session_state.last_docx_path = latest_docx
        st.session_state.last_md_path = latest_md
        st.session_state.generation_done = True

        welcome_box.empty()
        progress_box.empty()

        st.success(f"報告產生完成，總執行時間：{elapsed:.2f} 秒")

    except Exception as e:
        st.error(f"產生報告失敗：{e}")
        st.info("請確認 Ollama 已啟動，且 reports 資料夾中的 Word 檔案沒有被其他程式鎖住。")


# =========================
# 結果區：報告預覽與下載
# =========================
if st.session_state.generation_done:
    st.divider()

    st.markdown("## 報告預覽與下載")

    if st.session_state.last_elapsed is not None:
        st.caption(f"最近一次產生時間：{st.session_state.last_elapsed:.2f} 秒")

    latest_docx = st.session_state.last_docx_path
    latest_md = st.session_state.last_md_path

    if latest_md and Path(latest_md).exists():
        md_text = Path(latest_md).read_text(encoding="utf-8")

        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(md_text)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("找不到 Markdown 預覽檔。")

    if latest_docx and Path(latest_docx).exists():
        with open(latest_docx, "rb") as f:
            st.download_button(
                label="下載 Word 衛教報告",
                data=f,
                file_name=Path(latest_docx).name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        st.caption(f"Word 檔案位置：{latest_docx}")
    else:
        st.warning("找不到 Word 報告檔。")

