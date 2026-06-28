"""HTTP layer for the chat endpoint — deliberately thin.

A route's only job is the edge work: accept the validated request, hand it to the
service, return the result. No business logic lives here. The service is pulled
from ``app.state`` (where startup wiring put it) via a FastAPI dependency, so the
route never constructs anything itself.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.models.chat import ChatRequest, ChatResponse
from app.services.text_to_sql import TextToSqlService

router = APIRouter()


def get_text_to_sql(request: Request) -> TextToSqlService:
    """Pull the singleton service built at startup off the app state."""
    return request.app.state.text_to_sql


ServiceDep = Annotated[TextToSqlService, Depends(get_text_to_sql)]


@router.post("/chat")
async def chat(payload: ChatRequest, service: ServiceDep) -> ChatResponse:
    return await service.answer_question(payload.question)
