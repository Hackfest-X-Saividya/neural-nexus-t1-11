from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CrimeSketchAI Refinement Backend"
    APP_VERSION: str = "0.1.0"
    DEFAULT_CHARACTER_NAME: str = "Human"
    
    # Path configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_PATH: Path = BASE_DIR / "refinements.db"
    CONTROLLED_TEST_LOG_PATH: Path = BASE_DIR / "controlled_test_log.json"
    
    # Refinement step settings
    DEFAULT_STEP: float = 0.05
    MIN_SLIDER_VALUE: float = -1.0
    MAX_SLIDER_VALUE: float = 1.0
    
    # Bridge connection settings
    MPFB_BRIDGE_HOST: str = "127.0.0.1"
    MPFB_BRIDGE_PORT: int = 9877
    BLENDER_TIMEOUT_SECONDS: float = 3.0
    
    # Mode
    DRY_RUN_ONLY: bool = True

    # Sketch rendering settings
    SKETCH_OUTPUT_DIR: Path = BASE_DIR / "sketches"
    MPFB_EXPORT_DIR: Path = Path(r"C:\Dept\MPFB\data\exports")
    BLENDER_EXECUTABLE: str = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    SKETCH_RENDER_TIMEOUT_SECONDS: float = 45.0

    # Ollama AI Parser Settings
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_TIMEOUT_SECONDS: float = 180.0
    PARSER_MODE: str = "rule_based"  # "rule_based" or "ai"

    # Frontend CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
