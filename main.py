from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.core.settings import settings
from src.core.exceptions import LLMServiceError, InvalidRequestError
from src.api.routes import router

description = """
# FastAPI LangChain AI Chat API

This API provides integration with Ollama's Gemma model for chat completions.

## Features

* 💬 Chat completion with regular response
* 🌊 Streaming chat completion
* 🎯 Custom system prompts support
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    version="1.0.0",
    # docs와 관련된 URL은 API_V1_STR 없이 루트에 배치
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 예외 핸들러
@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(InvalidRequestError)
async def invalid_request_error_handler(request: Request, exc: InvalidRequestError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API 라우터 등록 - API 엔드포인트만 API_V1_STR 프리픽스 사용
app.include_router(
    router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
