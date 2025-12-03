import os
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables, they are."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    
    # Application Configuration
    app_name: str = Field(default="Document QA Chatbot", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")

    #Backend Server
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    
    #Frontend Server
    frontend_host: str = Field(default="0.0.0.0", alias="FRONTEND_HOST")
    frontend_port: int = Field(default=8081, alias="FRONTEND_PORT")

    storage_secret: str = Field(..., alias="STORAGE_SECRET") 

    max_pdf_size_mb: int = Field(default=10, alias="MAX_PDF_SIZE_MB")
    max_pdf_pages: int = Field(default=100, alias="MAX_PDF_PAGES")
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate that OpenAI API key is provided, we must."""
        if not v or v == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def load_settings() -> Settings:
    """Load application settings from environment, we must."""
    load_dotenv()
    try:
        return Settings()
    except Exception:
        return Settings(
            OPENAI_API_KEY="test-key-for-development",
            OPENAI_MODEL="gpt-4o-mini",
        )

settings: Settings | None = None


def get_settings() -> Settings:
    """Get global settings instance, we must."""
    global settings
    if settings is None:
        settings = load_settings()
    return settings
