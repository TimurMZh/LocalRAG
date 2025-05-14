from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Union, Type, Tuple

import instructor
from anthropic import Anthropic
from config.settings import get_settings
from openai import OpenAI
from pydantic import BaseModel

from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import torch

"""
LLM Provider Factory Module

This module implements a factory pattern for creating and managing different LLM providers
(OpenAI, Anthropic, etc.). It provides a unified interface for LLM interactions while
supporting structured output using Pydantic models.
"""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def _initialize_client(self) -> Any:
        """Initialize the client for the LLM provider."""
        pass

    @abstractmethod
    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs) -> Any:
        """Create a completion using the LLM provider."""
        pass

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for the given text."""
        pass


class RobertaKazProvider(LLMProvider):
    """Roberta-Kaz-Large provider implementation using Hugging Face."""

    def __init__(self, settings):
        self.settings = settings
        #  self.model_path = "models/models/roberta-kaz-large"  # Local path
        self.model_path = "models/models/roberta-kaz-large"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def _initialize_client(self) -> Any:
        # No client initialization needed for local models
        return None

    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs) -> Any:
        # Extract the last user message
        user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        # Tokenize and prepare input
        inputs = self.tokenizer(user_message, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get model output
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predictions = torch.softmax(logits, dim=1)

        # Convert output to response model format
        # Note: You'll need to adapt this part based on your specific response_model structure
        result = response_model(
            content=self.tokenizer.decode(torch.argmax(predictions, dim=1)),
            # Add other fields required by your response_model
        )

        return result, outputs

    def get_embedding(self, text: str) -> List[float]:
        # Get the embeddings from the model's encoder
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.roberta(inputs['input_ids'])
            # Use the last hidden state's CLS token as embedding
            embeddings = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy().tolist()

        return embeddings


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation with batching, retries & local fallback."""

    def __init__(self, settings):
        self.settings = settings
        self.raw_client = OpenAI(api_key=self.settings.api_key)
        self.client = self._initialize_client()

        # Local HF model for fallback
        self._hf_tokenizer = AutoTokenizer.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._hf_model     = AutoModel.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    def _initialize_client(self) -> Any:
        return instructor.from_openai(self.raw_client)

    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs):
        completion_params = {
            "model": kwargs.get("model", self.settings.default_model),
            "temperature": kwargs.get("temperature", self.settings.temperature),
            "max_retries": kwargs.get("max_retries", self.settings.max_retries),
            "max_tokens": kwargs.get("max_tokens", self.settings.max_tokens),
            "response_model": response_model,
            "messages": messages,
        }
        return self.client.chat.completions.create_with_completion(**completion_params)

    def _local_embedding(self, text: Union[str, List[str]]) -> List[List[float]]:
        """Generate embeddings using a local HF model."""
        texts = [text] if isinstance(text, str) else text
        inputs = self._hf_tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True
        )
        with torch.no_grad():
            # take the [CLS] token (first token) embedding
            cls_emb = self._hf_model(**inputs).last_hidden_state[:, 0]
        return cls_emb.tolist()

    def _safe_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI embeddings API with retry/backoff."""
        backoff = 1
        while True:
            try:
                resp = self.raw_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                return [d.embedding for d in resp.data]
            except RateLimitError as e:
                logging.warning(f"OpenAI rate limit hit, retrying in {backoff}s …")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except Exception:
                logging.exception("Unexpected error fetching embeddings; falling back.")
                break

        # If we exit the loop, fallback
        return self._local_embedding(texts)

    def get_embedding(self, text: str) -> List[float]:
        """Get one embedding, batching under the hood."""
        return self.get_embeddings([text])[0]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Batch multiple texts in one API call (more efficient than one-by-one).
        """
        # TODO: insert cache-mechanism here (e.g. check Redis/disk before API)
        try:
            return self._safe_openai_embeddings(texts)
        except Exception:
            logging.warning("Falling back to local embeddings for entire batch.")
            return self._local_embedding(texts)


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""

    def __init__(self, settings):
        self.settings = settings
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        return instructor.from_anthropic(Anthropic(api_key=self.settings.api_key))

    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs) -> Any:
        system_message = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [m for m in messages if m["role"] != "system"]

        completion_params = {
            "model": kwargs.get("model", self.settings.default_model),
            "temperature": kwargs.get("temperature", self.settings.temperature),
            "max_retries": kwargs.get("max_retries", self.settings.max_retries),
            "max_tokens": kwargs.get("max_tokens", self.settings.max_tokens),
            "response_model": response_model,
            "messages": user_messages,
        }
        if system_message:
            completion_params["system"] = system_message

        return self.client.messages.create_with_completion(**completion_params)

    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("Anthropic does not currently support embeddings")


class LlamaProvider(LLMProvider):
    """Llama provider implementation."""

    def __init__(self, settings):
        self.settings = settings
        self.raw_client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        return instructor.from_openai(
            self.raw_client,
            mode=instructor.Mode.JSON,
        )

    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs) -> Any:
        completion_params = {
            "model": kwargs.get("model", self.settings.default_model),
            "temperature": kwargs.get("temperature", self.settings.temperature),
            "max_retries": kwargs.get("max_retries", self.settings.max_retries),
            "max_tokens": kwargs.get("max_tokens", self.settings.max_tokens),
            "response_model": response_model,
            "messages": messages,
        }
        return self.client.chat.completions.create_with_completion(**completion_params)

    def get_embedding(self, text: str) -> List[float]:
        response = self.raw_client.embeddings.create(model=self.settings.embedding_model, input=text)
        return response.data[0].embedding


class LLMFactory:
    """
    Factory class for creating and managing LLM provider instances.

    This class implements the Factory pattern to create appropriate LLM provider
    instances based on the specified provider type. It supports multiple providers
    and handles their initialization and configuration.

    Attributes:
        provider: The name of the LLM provider to use
        settings: Configuration settings for the LLM provider
        llm_provider: The initialized LLM provider instance
    """

    def __init__(self, provider: str):
        self.provider = provider
        settings = get_settings()
        self.settings = getattr(settings.llm, provider)
        self.llm_provider = self._create_provider()
        self.model_path = "models/models/roberta-kaz-large"
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModel.from_pretrained(self.model_path)
        self.llm_provider = self._create_provider()

    def _create_provider(self) -> LLMProvider:
        providers = {
            "openai": OpenAIProvider,
            # "anthropic": AnthropicProvider,
            # "llama": LlamaProvider,
            "roberta": RobertaKazProvider,
        }
        provider_class = providers.get(self.provider)
        if provider_class:
            return provider_class(self.settings)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def create_completion(self, response_model: Type[BaseModel], messages: List[Dict[str, str]], **kwargs) -> Tuple[BaseModel, Any]:
        """
        Create a completion using the configured LLM provider.

        Args:
            response_model: Pydantic model class defining the expected response structure
            messages: List of message dictionaries containing the conversation
            **kwargs: Additional arguments to pass to the provider

        Returns:
            Tuple containing the parsed response model and raw completion

        Raises:
            TypeError: If response_model is not a Pydantic BaseModel
            ValueError: If the provider is not supported
        """
        if not issubclass(response_model, BaseModel):
            raise TypeError("response_model must be a subclass of pydantic.BaseModel")

        return self.llm_provider.create_completion(response_model, messages, **kwargs)

    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for the given text using the configured provider.

        Args:
            text: The text to get embeddings for

        Returns:
            List of floating point numbers representing the embedding vector

        Raises:
            NotImplementedError: If the provider doesn't support embeddings
        """
        return self.llm_provider.get_embedding(text)
