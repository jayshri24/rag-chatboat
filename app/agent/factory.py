"""Agno agent factory for creating configured agents."""
import asyncio
import logging
from agno.agent import Agent
from app.config import get_settings
from agno.models.openai.chat import OpenAIChat
from typing import AsyncGenerator, Callable

logger = logging.getLogger(__name__)

class AgentFactory:
    """Factory for creating Agno agents with OpenAI configuration."""
    
    def __init__(self) -> None:
        """Initialize the agent factory, we must."""
        settings = get_settings()
        self._openai_client = OpenAIChat(api_key=settings.openai_api_key)
    
    def create_agent(
        self,
        session_id: str,
        status_callback: Callable[[str], None] | None = None,
    ) -> Agent:
        """
        Create a new Agno agent for a session, we must.
        
        Args:
            session_id: Unique identifier for the session
            status_callback: Optional callback for status updates
            
        Returns:
            Configured Agno agent
        """
        agent = Agent(
            model=self._openai_client,
            session_id=session_id,
        )
        
        agent.system_prompt = (
            "You are a helpful document QA assistant. "
            "You can answer questions about uploaded documents and maintain context "
            "across the conversation. Be concise and accurate in your responses."
        )
        
        if status_callback:
            agent._status_callback = status_callback
        
        logger.info(f"Created agent for session {session_id}")
        return agent
        
    async def stream_response(
        self,
        agent: Agent,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Stream agent response token by token, we must."""
        try:
            if hasattr(agent, "_status_callback") and agent._status_callback:
                for step in ["Analyzing", "Searching knowledge", "Generating response"]:
                    agent._status_callback(step)
                    await asyncio.sleep(0.05)

            response = agent.run(message)

            content = ""
            if hasattr(response, "content"):
                content = str(response.content)
            elif isinstance(response, str):
                content = response
            else:
                content = "[unserializable response]"

            # Stream the content token-by-token
            for i, token in enumerate(content.split()):
                if i > 0:
                    yield " "
                yield token
                await asyncio.sleep(0.02)

        except Exception as e:
            logger.error(f"Error in stream_response: {e}", exc_info=True)
            yield f"[Error generating response: {str(e)}]"

    def get_session_history(self, agent: Agent) -> list[dict[str, str]]:
        """
        Get the conversation history for an agent, we must.
        
        Args:
            agent: The Agno agent
            
        Returns:
            List of conversation messages
        """

        if hasattr(agent, 'history') and agent.history:
            return [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in agent.history
            ]
        return []

agent_factory = AgentFactory()
