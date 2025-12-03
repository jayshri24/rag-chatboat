import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.agent.factory import AgentFactory


class TestAgentFactoryUnit:
    """Unit tests for AgentFactory class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        with patch("app.agent.factory.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = "test-key"
            self.factory = AgentFactory()

    def test_get_session_history(self) -> None:
        """Test getting session history."""
        mock_agent = MagicMock()
        mock_agent.history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        history = self.factory.get_session_history(mock_agent)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there"

    def test_get_session_history_empty(self) -> None:
        """Test getting session history when empty."""
        mock_agent = MagicMock()
        mock_agent.history = []

        history = self.factory.get_session_history(mock_agent)
        assert history == []

    def test_get_session_history_no_attribute(self) -> None:
        """Test agent without a history attribute."""
        mock_agent = MagicMock()
        del mock_agent.history

        history = self.factory.get_session_history(mock_agent)
        assert history == []

@pytest.fixture
def factory():
    with patch("app.agent.factory.get_settings") as mock_get_settings:
        mock_get_settings.return_value.openai_api_key = "test-key"
        yield AgentFactory()

def test_create_agent(factory):
    """Test that create_agent returns an Agent with correct system prompt."""
    with patch("app.agent.factory.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        agent = factory.create_agent("test-session")
    
        assert agent == mock_agent

        mock_agent_class.assert_called_once_with(
            model=factory._openai_client,
            session_id="test-session"
        )

        assert "document QA assistant" in mock_agent.system_prompt


def test_create_agent_with_status_callback(factory):
    """Test that create_agent sets _status_callback if provided."""
    callback_called = False
    def status_callback(step):
        nonlocal callback_called
        callback_called = True

    with patch("agno.agent.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        agent = factory.create_agent("test-session", status_callback)

        assert agent._status_callback == status_callback

@pytest.mark.asyncio
async def test_stream_response_yields_tokens(factory):
    """Test that stream_response yields tokens from agent.run."""
    mock_agent = MagicMock()
    mock_agent.run = MagicMock(return_value="Hello world")

    tokens = []
    async for token in factory.stream_response(mock_agent, "test message"):
        tokens.append(token)

    assert len(tokens) > 0
    assert "Hello" in tokens
    assert "world" in tokens

@pytest.mark.asyncio
async def test_stream_response_error(factory):
    """Test that stream_response yields error string if agent.run fails."""
    mock_agent = MagicMock()
    mock_agent.run = MagicMock(side_effect=Exception("Test error"))

    tokens = []
    async for token in factory.stream_response(mock_agent, "test message"):
        tokens.append(token)

    assert len(tokens) == 1
    assert "Error generating response: Test error" in tokens[0]


