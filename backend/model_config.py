"""
Model provider abstraction for supporting multiple AI providers
"""
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage


class ModelProvider:
    """Abstract base for model providers"""
    
    def __init__(self):
        self.provider = os.getenv('MODEL_PROVIDER', 'openai').lower()
        self.model_name = os.getenv('MODEL_NAME', 'gpt-4o')
        
    def get_chat_model(self, **kwargs) -> ChatOpenAI:
        """Get chat model based on provider configuration"""
        if self.provider == 'openai':
            return self._get_openai_model(**kwargs)
        elif self.provider == 'openrouter':
            return self._get_openrouter_model(**kwargs)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Supported providers: 'openai', 'openrouter'")
    
    def _get_openai_model(self, **kwargs) -> ChatOpenAI:
        """Configure OpenAI model"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
        
        return ChatOpenAI(
            model=self.model_name,
            openai_api_key=api_key,
            max_retries=kwargs.get('max_retries', 1),
            model_kwargs=kwargs.get('model_kwargs', {})
        )
    
    def _get_openrouter_model(self, **kwargs) -> ChatOpenAI:
        """Configure OpenRouter model (OpenAI-compatible API)"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for OpenRouter provider")
        
        return ChatOpenAI(
            model=self.model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_retries=kwargs.get('max_retries', 1),
            model_kwargs=kwargs.get('model_kwargs', {})
        )
    


# Global model provider instance
model_provider = ModelProvider()


def get_chat_model(**kwargs) -> ChatOpenAI:
    """Convenience function to get configured chat model"""
    return model_provider.get_chat_model(**kwargs)