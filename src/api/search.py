from fastapi import APIRouter

from src.models.knowledge import SearchRequest, SearchResponse, SuggestRequest
from src.services import search_service
from src.services.es_service import suggest

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    return await search_service.search(request)


@router.post("/search/suggest")
async def search_suggest(request: SuggestRequest) -> list[str]:
    return await suggest(request.prefix, request.limit)
