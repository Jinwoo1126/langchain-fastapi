from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schema import ChatRequest, ChatResponse, StreamResponse
from ..services.llm import generate_response, generate_stream_async, generate_stream_sync
from ..core.exceptions import LLMServiceError, InvalidRequestError
from ..core.auth import get_current_user
import json
import asyncio

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
) -> ChatResponse | StreamingResponse:
    try:
        if not request.message.strip():
            raise InvalidRequestError("Message cannot be empty")

        # 요청 메시지 디코딩
        try:
            decoded_message = request.message.encode().decode('utf-8')
            decoded_system_prompt = request.system_prompt.encode().decode('utf-8') if request.system_prompt else None
        except UnicodeError:
            raise InvalidRequestError("Invalid character encoding in request")

        if request.stream:
            return StreamingResponse(
                stream_generator(ChatRequest(
                    message=decoded_message,
                    system_prompt=decoded_system_prompt,
                    stream=True
                )),
                media_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'  # Nginx 버퍼링 비활성화
                }
            )
        
        response = generate_response(decoded_message, decoded_system_prompt)
        
        # 응답 인코딩
        try:
            encoded_response = response.encode().decode('utf-8')
        except UnicodeError:
            raise LLMServiceError("Failed to encode response")
            
        return ChatResponse(response=encoded_response)
    except (LLMServiceError, InvalidRequestError) as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def stream_generator(request: ChatRequest):
    """비동기 스트리밍 생성기"""
    try:
        async for chunk in generate_stream_async(request.message, request.system_prompt):
            try:
                # 각 청크를 즉시 전송하고 flush
                yield f"data: {json.dumps(chunk.dict(), ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)  # 다른 코루틴에 실행 기회를 줌
            except UnicodeError:
                yield f"data: {json.dumps({'error': 'Invalid character encoding in response chunk'})}\n\n"
                await asyncio.sleep(0)
                return
    except LLMServiceError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        await asyncio.sleep(0)
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Internal server error: {str(e)}'})}\n\n"
        await asyncio.sleep(0)

def sync_stream_generator(request: ChatRequest):
    """동기 스트리밍 생성기"""
    try:
        for chunk in generate_stream_sync(request.message, request.system_prompt):
            try:
                # 각 청크를 즉시 전송
                yield f"data: {json.dumps(chunk.dict(), ensure_ascii=False)}\n\n"
            except UnicodeError:
                yield f"data: {json.dumps({'error': 'Invalid character encoding in response chunk'})}\n\n"
                return
    except LLMServiceError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Internal server error: {str(e)}'})}\n\n"

__all__ = ['router']
