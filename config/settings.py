"""
Intelli-Credit Global Configuration
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_primary_model: str = "llama3.1:8b"
    ollama_financial_model: str = "mistral:7b"
    ollama_structured_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_financial: str = "financial_docs"
    qdrant_collection_research: str = "research_docs"
    qdrant_collection_legal: str = "legal_docs"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "intellicredit2026"

    # Database
    database_url: str = "postgresql://intellicredit:password@localhost:5432/intellicredit_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Keys
    serp_api_key: Optional[str] = None
    news_api_key: Optional[str] = None

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Indian URLs
    mca_base_url: str = "https://www.mca.gov.in/mcafoportal/"
    ecourts_base_url: str = "https://services.ecourts.gov.in/"
    rbi_base_url: str = "https://www.rbi.org.in/"
    sebi_base_url: str = "https://www.sebi.gov.in/"

    # Scoring Thresholds
    risk_score_high_threshold: int = 70
    risk_score_medium_threshold: int = 50
    max_loan_to_turnover_ratio: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
