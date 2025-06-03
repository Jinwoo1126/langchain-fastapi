from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI LangChain Project"
    CHAT_API_URL: str = "http://localhost:8000/api/v1/chat"
    
    # Security Configuration
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "gemma3"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

__all__ = ['settings']
