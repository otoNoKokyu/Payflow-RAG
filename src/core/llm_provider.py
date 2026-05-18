import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import aiohttp
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    prompt_tokens: int = 0

class LLMProvider(ABC):
    """Abstract base for pluggable LLM providers."""

    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        json_mode: bool = False
    ) -> LLMResponse:
        """Generate content from the LLM.
        
        Args:
            prompt: The user input or main prompt.
            system_prompt: Optional system instruction.
            json_mode: Whether to force JSON output format.
            
        Returns:
            LLMResponse containing text and token usage.
        """
        ...

class GenAIProvider(LLMProvider):
    """Google GenAI (Gemini) implementation."""

    def __init__(self, api_key: str, model: str = "gemma-4-31b-it"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        json_mode: bool = False
    ) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json" if json_mode else None,
            temperature=0.0 if json_mode else 0.7,
        )
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            
            text = response.text or ""
            tokens = (response.usage_metadata.prompt_token_count or 0) if response.usage_metadata else 0
            return LLMResponse(text=text, prompt_tokens=tokens)
        except Exception as e:
            logger.error("GenAI generation failed: %s", e)
            raise

class OllamaProvider(LLMProvider):
    """Local Ollama implementation."""

    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        json_mode: bool = False
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json" if json_mode else None,
            "options": {
                "temperature": 0.0 if json_mode else 0.7,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    text = data["message"]["content"]
                    # Ollama returns prompt token count in prompt_eval_count
                    tokens = data.get("prompt_eval_count", 0)
                    return LLMResponse(text=text, prompt_tokens=tokens)
        except Exception as e:
            logger.error("Ollama generation failed: %s", e)
            raise

def get_llm_provider() -> LLMProvider:
    """Factory to get the configured LLM provider.
    
    Reads from environment variables:
    - LLM_PROVIDER: "genai" or "ollama" (default: "ollama")
    - GENAI_MODEL: Model to use for GenAI (default: "gemma-4-31b-it")
    - OLLAMA_MODEL: Model to use for Ollama (default: "llama3.1:8b")
    - OLLAMA_BASE_URL: Base URL for Ollama API (default: "http://localhost:11434")
    """
    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    if provider_name == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info("Using Ollama provider: %s at %s", model, base_url)
        return OllamaProvider(model=model, base_url=base_url)
    
    # Provider: GenAI
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_GENAI_API_KEY not found in environment")
        
    model = os.getenv("GENAI_MODEL", "gemma-4-31b-it")
    logger.info("Using GenAI provider: %s", model)
    return GenAIProvider(api_key=api_key or "", model=model)
