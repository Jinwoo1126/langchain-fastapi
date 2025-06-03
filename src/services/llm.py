from typing import AsyncIterator, Iterator
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from ..core.settings import settings
from ..models.schema import StreamResponse
from ..core.exceptions import LLMServiceError

def get_llm(stream: bool = False):
    try:
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.MODEL_NAME,
            streaming=stream
        )
    except Exception as e:
        raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")

def generate_response(message: str, system_prompt: str | None = None) -> str:
    try:
        llm = get_llm()
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))
        
        response = llm.invoke(messages)
        # 응답 텍스트 인코딩 처리
        try:
            return response.content.encode().decode('utf-8')
        except UnicodeError:
            raise LLMServiceError("Failed to encode model response")
    except Exception as e:
        raise LLMServiceError(f"Failed to generate response: {str(e)}")

def generate_stream_sync(message: str, system_prompt: str | None = None) -> Iterator[StreamResponse]:
    """동기적 스트리밍 응답 생성"""
    try:
        llm = get_llm(stream=True)
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))
        
        for chunk in llm.stream(messages):
            try:
                encoded_text = chunk.content.encode().decode('utf-8')
                yield StreamResponse(text=encoded_text, done=False)
            except UnicodeError:
                raise LLMServiceError("Failed to encode streaming response")
                
        yield StreamResponse(text="", done=True)
    except Exception as e:
        raise LLMServiceError(f"Failed to generate streaming response: {str(e)}")

async def generate_stream_async(message: str, system_prompt: str | None = None) -> AsyncIterator[StreamResponse]:
    """비동기적 스트리밍 응답 생성"""
    try:
        llm = get_llm(stream=True)
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))
        
        async for chunk in llm.astream(messages):
            try:
                encoded_text = chunk.content.encode().decode('utf-8')
                yield StreamResponse(text=encoded_text, done=False)
            except UnicodeError:
                raise LLMServiceError("Failed to encode streaming response")
                
        yield StreamResponse(text="", done=True)
    except Exception as e:
        raise LLMServiceError(f"Failed to generate streaming response: {str(e)}")

# 기존 generate_stream을 generate_stream_async로 대체하기 위한 별칭
generate_stream = generate_stream_async
