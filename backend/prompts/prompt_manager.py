from langfuse import Langfuse
from configs.settings import get_settings


class PromptManager:
    """
    Provides centralized access to prompts managed in Langfuse.
    This class encapsulates the Langfuse client and exposes convenience
    methods for retrieving prompts used throughout the application.
    """

    def __init__(self) -> None:
        """Initialize the PromptManager.

        Creates a Langfuse client using the configured credentials.
        """
        settings = get_settings()

        self._langfuse = Langfuse(
            secret_key=settings.langfuse.secret_key,
            public_key=settings.langfuse.public_key,
            host=settings.langfuse.host,
        )

    def get_agent_system_prompt(self, label: str = "latest"):
        """Retrieve the Retrieval Agent system prompt from Langfuse.

        Args:
            label: The prompt label to retrieve. Defaults to "latest".

        Returns:
            The Langfuse PromptClient object for the Retrieval Agent system
            prompt. Use ``prompt.prompt`` to access the prompt text, or pass
            the returned object directly to
            ``langfuse.update_current_observation()`` for prompt tracking.
        """
        return self._langfuse.get_prompt(
            name="AGENT_SYSTEM_PROMPT",
            label=label,
        )

if __name__ == "__main__":
    prompt_manager = PromptManager()
    prompt = prompt_manager.get_agent_system_prompt()
    print(prompt.prompt)
