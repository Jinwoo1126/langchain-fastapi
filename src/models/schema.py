from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    response: str = Field(..., description="The generated response text")

class StreamResponse(BaseModel):
    text: str
    done: bool
