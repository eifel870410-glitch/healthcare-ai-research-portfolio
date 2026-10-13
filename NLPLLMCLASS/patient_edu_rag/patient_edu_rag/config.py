from pathlib import Path
from dataclasses import dataclass


@dataclass
class Settings:
    """
    專案主要設定。
    同時保留新舊欄位名稱，避免 pipeline.py / retriever.py / data_loader.py
    使用不同設定名稱時出錯。
    """

    project_root: Path = Path(__file__).resolve().parents[1]

    # =========================
    # 資料路徑
    # =========================
    ehr_csv: Path = project_root / "data" / "ehr" / "patients_demo.csv"

    # 衛教單資料夾
    leaflet_dir: Path = project_root / "data" / "leaflets"
    leaflets_dir: Path = project_root / "data" / "leaflets"

    # ChromaDB 向量資料庫
    chroma_dir: Path = project_root / "chroma_db"
    persist_dir: Path = project_root / "chroma_db"

    # Chroma collection 名稱
    collection_name: str = "patient_education_leaflets"

    # =========================
    # 輸出路徑
    # =========================
    output_dir: Path = project_root / "outputs"
    report_dir: Path = project_root / "reports"

    # =========================
    # Ollama 設定
    # =========================
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # =========================
    # RAG 設定
    # =========================
    top_k: int = 3
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# 舊版 pipeline.py / retriever.py 會 import 小寫 settings
# 所以一定要保留
settings = Settings()
