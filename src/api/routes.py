from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..models.schema import ChatRequest, ChatResponse, StreamResponse
from ..services.llm import generate_response, generate_stream
from ..core.exceptions import LLMServiceError, InvalidRequestError
import json

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse | StreamingResponse:
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
    try:
        async for chunk in generate_stream(request.message, request.system_prompt):
            try:
                # 스트림 청크 인코딩
                encoded_text = chunk.text.encode().decode('utf-8')
                response_chunk = StreamResponse(text=encoded_text, done=chunk.done)
                yield f"data: {json.dumps(response_chunk.dict(), ensure_ascii=False)}\n\n"
            except UnicodeError:
                yield f"data: {json.dumps({'error': 'Invalid character encoding in response chunk'})}\n\n"
                return
    except LLMServiceError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Internal server error: {str(e)}'})}\n\n"

__all__ = ['router']
