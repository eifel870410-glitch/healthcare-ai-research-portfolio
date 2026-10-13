import re
from typing import Any, Dict, List, Tuple

import requests

try:
    from opencc import OpenCC
    cc = OpenCC("s2tw")
except Exception:
    cc = None


# =========================
# 品質優先版參數
# =========================

DEFAULT_MODEL = "llama3.2"

# 從 225 份衛教單檢索後，只餵最相關的前 3 份給 LLaMA
TOP_K_CONTEXT = 3

# 每份衛教單擷取最多 4 個相關段落
MAX_SNIPPETS_PER_DOC = 4

# 每份衛教單最多保留 1800 字
MAX_CHARS_PER_DOC = 1800

# 全部 context 最多 6000 字
MAX_TOTAL_CONTEXT_CHARS = 6000

# 一次生成完整報告，給足輸出長度
NUM_PREDICT = 1400

TIMEOUT_SECONDS = 900


# =========================
# 繁體中文與台灣用語處理
# =========================
def normalize_taiwan_traditional(text: str) -> str:
    if not text:
        return text

    if cc is not None:
        text = cc.convert(text)

    replacements = {
        "患者": "病人",
        "病患": "病人",
        "医生": "醫師",
        "醫生": "醫師",
        "药物": "藥物",
        "用药": "用藥",
        "药品": "藥品",
        "复诊": "回診",
        "復診": "回診",
        "信息": "資訊",
        "视频": "影片",
        "視頻": "影片",
        "症状": "症狀",
        "检查": "檢查",
        "治疗": "治療",
        "护理": "照護",
        "质量": "品質",
        "严重": "嚴重",
        "并发症": "併發症",
        "脑卒中": "中風",
        "腦卒中": "中風",
        "高血压": "高血壓",
        "心力衰竭": "心臟衰竭",
        "肾脏": "腎臟",
        "肾功能": "腎功能",
        "监测": "監測",
        "风险": "風險",
        "建议": "建議",
        "资料": "資料",
        "发现": "發現",
        "發現和治療": "發現與治療",
        "管理": "控制",
        "严重后果": "嚴重併發症",
        "嚴重後果": "嚴重併發症",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def remove_garbled_text(text: str) -> str:
    """
    移除常見非中文亂碼，例如泰文、緬文等模型偶發輸出。
    保留中文、英文、數字與常見標點。
    """
    if not text:
        return text

    text = re.sub(r"[\u0E00-\u0E7F]+", "", text)
    text = re.sub(r"[\u1000-\u109F]+", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    return text


# =========================
# 相容 dict / object / string
# =========================
def get_hit_value(hit: Any, key: str, default: str = "") -> str:
    if isinstance(hit, dict):
        return str(hit.get(key, default) or default)
    return str(getattr(hit, key, default) or default)


def patient_to_text(patient: Any) -> str:
    if isinstance(patient, str):
        return patient

    if isinstance(patient, dict):
        subject_id = patient.get("subject_id", "")
        gender = patient.get("gender", "")
        age = patient.get("anchor_age", "")
        icd10_codes = patient.get("icd10_codes", "")
        prescriptions = patient.get("prescriptions", "")
        diagnoses = patient.get("diagnoses", "")
        medications = patient.get("medications", "")

        return f"""
- Subject ID：{subject_id}
- 性別：{gender}
- 年齡：{age}
- ICD / 診斷碼：{icd10_codes}
- 診斷名稱：{diagnoses}
- 用藥紀錄：{prescriptions}
- 用藥名稱：{medications}
""".strip()

    return str(patient)


# =========================
# 衛教單段落擷取
# =========================
def clean_leaflet_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            lines.append("")
            continue

        if re.fullmatch(r"\d+", line):
            continue

        if line.lower().startswith("--- page"):
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def extract_keywords(patient_profile: str) -> List[str]:
    text = normalize_taiwan_traditional(patient_profile)

    medical_terms = [
        "高血壓",
        "高血糖",
        "糖尿病",
        "高血脂",
        "心臟衰竭",
        "心衰竭",
        "肺炎",
        "氣喘",
        "慢性阻塞性肺病",
        "COPD",
        "腎臟",
        "腎功能",
        "中風",
        "疼痛",
        "傷口",
        "感染",
        "發燒",
        "呼吸",
        "用藥",
        "藥物",
        "照護",
        "回診",
        "血壓",
        "血糖",
        "膽固醇",
        "利尿劑",
        "吸入劑",
        "抗生素",
        "Acetaminophen",
        "Albuterol",
        "Aspirin",
        "Dextrose",
        "Sodium Chloride",
        "Azithromycin",
        "Cefepime",
        "Diazepam",
    ]

    found = []

    for term in medical_terms:
        if term.lower() in text.lower():
            found.append(term)

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text)

    stopwords = {
        "with",
        "without",
        "unspecified",
        "elsewhere",
        "classified",
        "acute",
        "chronic",
        "adult",
        "mini",
        "plus",
    }

    for token in tokens:
        if token.lower() not in stopwords:
            found.append(token)

    unique = []

    for kw in found:
        if kw not in unique:
            unique.append(kw)

    return unique[:30]


def split_into_passages(text: str) -> List[str]:
    text = clean_leaflet_text(text)
    raw_passages = re.split(r"\n\s*\n", text)

    passages = []

    for passage in raw_passages:
        passage = passage.strip()

        if not passage:
            continue

        if len(passage) > 800:
            pieces = re.split(r"(?<=[。！？；;])", passage)
            buffer = ""

            for piece in pieces:
                piece = piece.strip()

                if not piece:
                    continue

                if len(buffer) + len(piece) <= 600:
                    buffer += piece
                else:
                    if buffer:
                        passages.append(buffer)
                    buffer = piece

            if buffer:
                passages.append(buffer)
        else:
            passages.append(passage)

    passages = [p for p in passages if len(p) >= 20]

    return passages


def score_passage(passage: str, keywords: List[str], title: str) -> int:
    passage_lower = passage.lower()
    title_lower = title.lower()

    score = 0

    for kw in keywords:
        kw_lower = kw.lower()

        if not kw_lower:
            continue

        if kw_lower in passage_lower:
            score += 3

        if kw_lower in title_lower:
            score += 2

    important_words = [
        "注意",
        "症狀",
        "回診",
        "就醫",
        "治療",
        "用藥",
        "藥物",
        "副作用",
        "照護",
        "預防",
        "危險",
        "警訊",
        "飲食",
        "運動",
        "血壓",
        "血糖",
        "呼吸",
        "感染",
        "發燒",
        "疼痛",
        "喘",
        "不適",
        "生活",
        "護理",
    ]

    for word in important_words:
        if word in passage:
            score += 1

    return score


def select_relevant_snippets(
    text: str,
    title: str,
    patient_profile: str,
    max_snippets: int = MAX_SNIPPETS_PER_DOC,
    max_chars: int = MAX_CHARS_PER_DOC,
) -> str:
    text = clean_leaflet_text(text)
    keywords = extract_keywords(patient_profile)
    passages = split_into_passages(text)

    if not passages:
        return text[:max_chars]

    scored: List[Tuple[int, int, str]] = []

    for idx, passage in enumerate(passages):
        score = score_passage(passage, keywords, title)
        scored.append((score, idx, passage))

    scored.sort(key=lambda x: (-x[0], x[1]))

    selected = []

    for score, idx, passage in scored:
        if len(selected) >= max_snippets:
            break
        selected.append((idx, passage))

    selected.sort(key=lambda x: x[0])

    final_parts = []
    total_len = 0

    for _, passage in selected:
        if total_len + len(passage) > max_chars:
            remain = max_chars - total_len

            if remain > 100:
                final_parts.append(passage[:remain] + "……")

            break

        final_parts.append(passage)
        total_len += len(passage)

    return "\n".join(final_parts).strip()


def build_context(patient: Any, hits: List[Any]) -> str:
    patient_profile = patient_to_text(patient)
    context_blocks = []
    total_chars = 0

    for i, h in enumerate(hits[:TOP_K_CONTEXT], start=1):
        title = get_hit_value(h, "title", f"衛教單 {i}")
        source = get_hit_value(h, "source", f"Source {i}")
        text = get_hit_value(h, "text", "")

        snippet = select_relevant_snippets(
            text=text,
            title=title,
            patient_profile=patient_profile,
            max_snippets=MAX_SNIPPETS_PER_DOC,
            max_chars=MAX_CHARS_PER_DOC,
        )

        block = f"""
[來源 {i}]
標題：{title}
來源代碼：{source}
相關衛教內容：
{snippet}
""".strip()

        if total_chars + len(block) > MAX_TOTAL_CONTEXT_CHARS:
            break

        context_blocks.append(block)
        total_chars += len(block)

    return "\n\n".join(context_blocks)


def build_source_list(hits: List[Any]) -> str:
    lines = []

    for i, h in enumerate(hits[:TOP_K_CONTEXT], start=1):
        title = get_hit_value(h, "title", f"衛教單 {i}")
        source = get_hit_value(h, "source", "")
        lines.append(f"- [來源 {i}] {title}，{source}")

    return "\n".join(lines)


# =========================
# Prompt
# =========================
def build_prompt(patient: Any, hits: List[Any]) -> str:
    patient_profile = patient_to_text(patient)
    context = build_context(patient, hits)
    source_list = build_source_list(hits)

    prompt = f"""
你是一位台灣醫院的衛教護理師助理。
你的任務是根據「病人資料」與「已核可衛教單內容」，產生清楚、完整、可給病人閱讀的個人化衛教報告。

請嚴格遵守以下規則：
1. 只能根據下方提供的衛教單內容回答。
2. 不可以自行編造沒有在衛教單出現的治療方式、疾病判斷或用藥建議。
3. 每一段或每個重點都要標示引用來源，例如：[來源 1]。
4. 如果資料不足，請寫「目前提供的衛教單內容不足以判斷」。
5. 全程使用台灣繁體中文。
6. 不可以使用簡體中文。
7. 不可以輸出亂碼或非中文文字。
8. 使用台灣常見醫療衛教用語，例如「病人」、「用藥」、「回診」、「症狀」、「醫師」、「照護」。
9. 不要使用中國大陸用語，例如「患者」、「复诊」、「信息」、「视频」、「脑卒中」。
10. 報告要完整，不要只寫摘要。
11. 請依照指定格式完整輸出到「六、引用來源」，不可中途停止。
12. 請使用病人可以看懂的語氣。

病人資料：
{patient_profile}

可使用的衛教單內容：
{context}

請依照以下格式完整輸出：

# 個人化病人衛教報告

## 一、病人狀況摘要
請用 3 到 4 句話說明這位病人目前最需要注意的健康議題，並連結到檢索到的衛教內容。每段都要有引用來源。

## 二、主要衛教重點
請列出 4 到 6 點。每一點都要包含：
- 病人需要知道什麼
- 為什麼重要
- 建議注意事項
每一點都要加引用來源。

## 三、用藥與日常照護提醒
請列出 3 到 5 點，包含用藥、症狀觀察、生活照護、飲食或活動注意事項。每一點都要加引用來源。

## 四、需要回診或立即尋求協助的情況
請列出 3 到 5 點警訊，例如症狀惡化、呼吸困難、發燒、疼痛加劇、藥物不適等。每一點都要加引用來源。

## 五、給病人的簡短提醒
請用溫和、鼓勵的語氣，寫 3 到 4 句給病人的結語，並加引用來源。

## 六、引用來源
請列出本次使用的來源編號、衛教單標題與來源代碼。

可用引用來源如下：
{source_list}
"""
    return prompt.strip()


# =========================
# Ollama
# =========================
def call_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = "http://localhost:11434",
) -> str:
    url = f"{base_url}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "num_predict": NUM_PREDICT,
            "temperature": 0.15,
            "top_p": 0.9,
            "num_ctx": 8192,
        },
    }

    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        data = r.json()
        answer = data.get("response", "").strip()
        answer = normalize_taiwan_traditional(answer)
        answer = remove_garbled_text(answer)
        return answer

    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            "Ollama 回應逾時。建議先暖機模型，或降低 NUM_PREDICT / MAX_TOTAL_CONTEXT_CHARS。"
        ) from e

    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "無法連線到 Ollama。請確認 Ollama 已啟動，並先執行：ollama run llama3.2"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama 呼叫失敗：{e}") from e


def ensure_complete_report(answer: str, hits: List[Any]) -> str:
    """
    避免 LLaMA 沒有完整輸出最後引用來源。
    若缺少第六節，程式自動補上。
    """
    answer = normalize_taiwan_traditional(answer)
    answer = remove_garbled_text(answer)

    source_list = build_source_list(hits)

    if "## 六、引用來源" not in answer and "六、引用來源" not in answer:
        answer = answer.rstrip() + "\n\n## 六、引用來源\n" + source_list

    return answer.strip()


# =========================
# 對外主函式
# =========================
def generate_education_report(
    patient: Any,
    hits: List[Any],
    use_ollama: bool = True,
    model: str = DEFAULT_MODEL,
    base_url: str = "http://localhost:11434",
) -> str:
    if not use_ollama:
        return fallback_generation(patient, hits)

    prompt = build_prompt(patient, hits)
    answer = call_ollama(prompt, model=model, base_url=base_url)
    answer = ensure_complete_report(answer, hits)

    return answer


# =========================
# Fallback 測試版
# =========================
def fallback_generation(patient: Any, hits: List[Any]) -> str:
    patient_profile = patient_to_text(patient)

    lines = []
    lines.append("# 個人化病人衛教報告")
    lines.append("")
    lines.append("## 一、病人狀況摘要")
    lines.append("系統根據病人資料與檢索到的衛教單內容，產生個人化衛教摘要。[來源 1]")
    lines.append("")
    lines.append("病人資料：")
    lines.append(patient_profile)
    lines.append("")
    lines.append("## 二、主要衛教重點")

    for i, h in enumerate(hits[:TOP_K_CONTEXT], start=1):
        title = get_hit_value(h, "title", f"衛教單 {i}")
        lines.append(f"- 可參考「{title}」之衛教內容。[來源 {i}]")

    lines.append("")
    lines.append("## 三、用藥與日常照護提醒")
    lines.append("請依照醫療人員指示使用藥物，若有不適或疑問，應主動詢問醫師或藥師。[來源 1]")
    lines.append("")
    lines.append("## 四、需要回診或立即尋求協助的情況")
    lines.append("若症狀惡化、出現嚴重不適或藥物副作用，請儘速回診或尋求醫療協助。[來源 1]")
    lines.append("")
    lines.append("## 五、給病人的簡短提醒")
    lines.append("請依照醫療團隊建議持續追蹤與照護，若有疑問請主動詢問醫師或護理師。[來源 1]")
    lines.append("")
    lines.append("## 六、引用來源")
    lines.append(build_source_list(hits))

    return normalize_taiwan_traditional("\n".join(lines))


# =========================
# 引用檢查
# =========================
def validate_citations(answer: str, hits: List[Any] = None) -> Dict[str, Any]:
    if not answer:
        return {
            "citation_count": 0,
            "sources_used": [],
            "section_count": 0,
            "has_uncovered_statement_warning": True,
        }

    citation_matches = re.findall(r"\[來源\s*(\d+)\]", answer)
    sources_used = sorted(set(int(x) for x in citation_matches if x.isdigit()))
    section_count = len(re.findall(r"^##\s+", answer, flags=re.MULTILINE))

    expected_sections = [
        "病人狀況摘要",
        "主要衛教重點",
        "用藥與日常照護提醒",
        "需要回診或立即尋求協助的情況",
        "給病人的簡短提醒",
        "引用來源",
    ]

    has_uncovered_statement_warning = False

    for section in expected_sections:
        if section not in answer:
            has_uncovered_statement_warning = True

    important_sections = [
        "病人狀況摘要",
        "主要衛教重點",
        "用藥與日常照護提醒",
        "需要回診或立即尋求協助的情況",
        "給病人的簡短提醒",
    ]

    for section in important_sections:
        if section in answer:
            section_start = answer.find(section)
            section_text = answer[section_start: section_start + 900]
            if "[來源" not in section_text:
                has_uncovered_statement_warning = True

    return {
        "citation_count": len(citation_matches),
        "sources_used": sources_used,
        "section_count": section_count,
        "has_uncovered_statement_warning": has_uncovered_statement_warning,
    }
