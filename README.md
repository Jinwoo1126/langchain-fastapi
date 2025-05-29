# FastAPI LangChain AI Chat API

Ollama의 Gemma 모델을 사용하는 FastAPI 기반의 채팅 API 서버입니다. 일반 응답과 스트리밍 응답을 모두 지원합니다.

## 기능

- 💬 Chat completion with regular response
- 🌊 Streaming chat completion (SSE)
- 🎯 Custom system prompts support
- 🔄 UTF-8 인코딩 지원
- 📝 OpenAPI 문서 (Swagger UI)

## 요구사항

- Python 3.11 이상
- Ollama (gemma 모델 설치 필요)

## 설치 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd fastapi_langchain
```

2. 가상환경 생성 및 활성화
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 설정
`.env.example`을 `.env`로 복사하고 필요한 설정을 수정합니다:
```bash
cp .env.example .env
```

## 실행 방법

```bash
python main.py
```

서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

## API 엔드포인트

### 채팅 API
- URL: `/api/v1/chat`
- Method: `POST`
- Content-Type: `application/json`

#### 요청 형식
```json
{
    "message": "질문 내용",
    "system_prompt": "시스템 프롬프트 (선택사항)",
    "stream": false
}
```

#### 일반 응답 예시
```json
{
    "response": "모델의 응답 내용"
}
```

#### 스트리밍 응답 사용법

스트리밍 응답을 사용하려면 `stream: true`로 설정하고 Server-Sent Events(SSE)를 사용하여 응답을 처리합니다.

```javascript
const eventSource = new EventSource('/api/v1/chat');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.done) {
        eventSource.close();
    } else {
        console.log(data.text);
    }
};
```

## API 문서

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## 상태 확인

- 헬스체크 엔드포인트: `/health`

## 설정 옵션 (.env)

```ini
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="FastAPI LangChain Project"

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=gemma3

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## 에러 처리

API는 다음과 같은 에러 응답을 반환할 수 있습니다:

- 400: 잘못된 요청 (메시지가 비어있거나 인코딩 오류)
- 503: LLM 서비스 오류 (Ollama 연결 실패 등)
- 500: 내부 서버 오류

각 에러는 다음 형식으로 반환됩니다:
```json
{
    "error": "에러 메시지"
}
```

## 라이선스

[라이선스 정보]