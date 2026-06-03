from __future__ import annotations

from app.agent.react_agent import FoodReActAgent
from app.agent.schemas import RecommendationRequest, RecommendationResponse, ReActTraceStep
from app.mcp_clients.mcp_client_manager import MCPClientManager


class RecommendationService:
    def __init__(self, mcp_manager: MCPClientManager | None = None) -> None:
        self.mcp_manager = mcp_manager or MCPClientManager()
        self.agent = FoodReActAgent(self.mcp_manager)

    async def recommend(
        self,
        request: RecommendationRequest,
        initial_trace: list[ReActTraceStep] | None = None,
    ) -> RecommendationResponse:
        return await self.agent.run(request, initial_trace=initial_trace)
