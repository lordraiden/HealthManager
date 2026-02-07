from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import openai
import requests
from config import Config


class AIProvider(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides medical information based on patient data. Remember that this is for informational purposes only and not a substitute for professional medical advice."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating response with OpenAI: {str(e)}"
    
    def get_name(self) -> str:
        return "OpenAI"


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                return f"Error generating response with Ollama: HTTP {response.status_code}"
        except Exception as e:
            return f"Error generating response with Ollama: {str(e)}"
    
    def get_name(self) -> str:
        return "Ollama"


class LMStudioProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url.rstrip('/')
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "",  # LM Studio often doesn't require a specific model name
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that provides medical information based on patient data. Remember that this is for informational purposes only and not a substitute for professional medical advice."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                choices = response.json().get("choices", [])
                if choices:
                    return choices[0]["message"]["content"].strip()
                else:
                    return "No response generated"
            else:
                return f"Error generating response with LM Studio: HTTP {response.status_code}"
        except Exception as e:
            return f"Error generating response with LM Studio: {str(e)}"
    
    def get_name(self) -> str:
        return "LM Studio"


class MockProvider(AIProvider):
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        return "This is a mock response for testing purposes. In a real implementation, this would connect to an AI service."
    
    def get_name(self) -> str:
        return "Mock"


class AIProviderFactory:
    _providers = {
        'openai': lambda: OpenAIProvider(
            api_key=Config.OPENAI_API_KEY,
            model=getattr(Config, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        ),
        'ollama': lambda: OllamaProvider(
            base_url=Config.OLLAMA_BASE_URL,
            model=Config.OLLAMA_MODEL
        ),
        'lmstudio': lambda: LMStudioProvider(base_url=Config.LMSTUDIO_BASE_URL),
        'mock': lambda: MockProvider()
    }
    
    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[AIProvider]:
        provider_creator = cls._providers.get(provider_name.lower())
        if provider_creator:
            return provider_creator()
        return None
    
    @classmethod
    def get_available_providers(cls) -> list:
        return list(cls._providers.keys())