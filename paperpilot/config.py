import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_url: str = os.getenv("PAPERPILOT_API_URL", "http://127.0.0.1:8000")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    chroma_dir: str = os.getenv("CHROMA_DIR", "data/chroma")
    upload_dir: str = os.getenv("UPLOAD_DIR", "data/papers")
    top_k: int = int(os.getenv("TOP_K", "6"))
    chunk_words: int = int(os.getenv("CHUNK_WORDS", "220"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "40"))


settings = Settings()
