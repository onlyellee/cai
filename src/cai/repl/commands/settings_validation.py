"""
API key and configuration validation for CAI settings.
Provides functions to validate API keys and check service connectivity.
"""

import os
import asyncio
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from cai.i18n import t

# Try to import httpx for async HTTP, fall back to requests
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import requests


class ValidationStatus(Enum):
    """Status of a validation check."""
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"
    NOT_SET = "not_set"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    status: ValidationStatus
    message: str
    details: Optional[Dict] = None


# =============================================================================
# API Key Validators
# =============================================================================

def validate_openai_key(api_key: Optional[str] = None) -> ValidationResult:
    """Validate OpenAI API key by making a test request.

    Args:
        api_key: The API key to validate, or None to use env var

    Returns:
        ValidationResult with status and message
    """
    key = api_key or os.getenv("OPENAI_API_KEY")

    if not key:
        return ValidationResult(
            status=ValidationStatus.NOT_SET,
            message=t('settings_val_openai_not_set')
        )

    if not key.startswith("sk-"):
        return ValidationResult(
            status=ValidationStatus.INVALID,
            message=t('settings_val_openai_invalid_format')
        )

    try:
        headers = {"Authorization": f"Bearer {key}"}
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                response = client.get("https://api.openai.com/v1/models", headers=headers)
        else:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10
            )

        if response.status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_openai_valid'),
                details={"models_available": True}
            )
        elif response.status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=t('settings_val_openai_invalid')
            )
        elif response.status_code == 429:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_openai_rate_limited'),
                details={"rate_limited": True}
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=t('settings_val_unexpected_response', status_code=response.status_code)
            )
    except Exception as e:
        return ValidationResult(
            status=ValidationStatus.ERROR,
            message=t('settings_val_connection_error', error=str(e))
        )


def validate_anthropic_key(api_key: Optional[str] = None) -> ValidationResult:
    """Validate Anthropic API key.

    Args:
        api_key: The API key to validate, or None to use env var

    Returns:
        ValidationResult with status and message
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")

    if not key:
        return ValidationResult(
            status=ValidationStatus.NOT_SET,
            message=t('settings_val_anthropic_not_set')
        )

    if not key.startswith("sk-ant-"):
        return ValidationResult(
            status=ValidationStatus.INVALID,
            message=t('settings_val_anthropic_invalid_format')
        )

    try:
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        # Use a minimal request to check the key
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}]
                    }
                )
        else:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}]
                },
                timeout=10
            )

        if response.status_code in [200, 201]:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_anthropic_valid')
            )
        elif response.status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=t('settings_val_anthropic_invalid')
            )
        elif response.status_code == 429:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_anthropic_rate_limited')
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=t('settings_val_unexpected_response', status_code=response.status_code)
            )
    except Exception as e:
        return ValidationResult(
            status=ValidationStatus.ERROR,
            message=t('settings_val_connection_error', error=str(e))
        )


def validate_openrouter_key(api_key: Optional[str] = None) -> ValidationResult:
    """Validate OpenRouter API key.

    Args:
        api_key: The API key to validate, or None to use env var

    Returns:
        ValidationResult with status and message
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY")

    if not key:
        return ValidationResult(
            status=ValidationStatus.NOT_SET,
            message=t('settings_val_openrouter_not_set')
        )

    try:
        headers = {"Authorization": f"Bearer {key}"}
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers
                )
        else:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=10
            )

        if response.status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_openrouter_valid')
            )
        elif response.status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=t('settings_val_openrouter_invalid')
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=t('settings_val_unexpected_response', status_code=response.status_code)
            )
    except Exception as e:
        return ValidationResult(
            status=ValidationStatus.ERROR,
            message=t('settings_val_connection_error', error=str(e))
        )


def validate_google_key(api_key: Optional[str] = None) -> ValidationResult:
    """Validate Google API key.

    Args:
        api_key: The API key to validate, or None to use env var

    Returns:
        ValidationResult with status and message
    """
    key = api_key or os.getenv("GOOGLE_API_KEY")

    if not key:
        return ValidationResult(
            status=ValidationStatus.NOT_SET,
            message=t('settings_val_google_not_set')
        )

    try:
        # Test with Gemini API
        url = f"https://generativelanguage.googleapis.com/v1/models?key={key}"
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
        else:
            response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                message=t('settings_val_google_valid')
            )
        elif response.status_code in [401, 403]:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=t('settings_val_google_invalid')
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=t('settings_val_unexpected_response', status_code=response.status_code)
            )
    except Exception as e:
        return ValidationResult(
            status=ValidationStatus.ERROR,
            message=t('settings_val_connection_error', error=str(e))
        )


# =============================================================================
# Ollama / Local Model Validators
# =============================================================================

def check_ollama_running(base_url: Optional[str] = None) -> ValidationResult:
    """Check if Ollama server is running and accessible.

    Args:
        base_url: Ollama API base URL, or None to auto-detect

    Returns:
        ValidationResult with status and message
    """
    # Determine the base URL to check
    url = base_url or os.getenv("OLLAMA_API_BASE") or "http://127.0.0.1:11434"

    # Remove /v1 suffix if present for the root check
    if url.endswith("/v1"):
        url = url[:-3]

    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
        else:
            response = requests.get(url, timeout=5)

        if response.status_code == 200:
            text = response.text.lower()
            if "ollama" in text:
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message=t('settings_val_ollama_running', url=url),
                    details={"url": url}
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message=t('settings_val_ollama_maybe', url=url)
                )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=t('settings_val_ollama_status_error', status_code=response.status_code)
            )
    except Exception as e:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            message=t('settings_val_ollama_connect_error', url=url, error=str(e)),
            details={
                "url": url,
                "suggestions": [
                    t('settings_val_ollama_suggestion_serve'),
                    t('settings_val_ollama_suggestion_firewall'),
                    t('settings_val_ollama_suggestion_base'),
                ]
            }
        )


def list_ollama_models(base_url: Optional[str] = None) -> Tuple[bool, list]:
    """List available models in Ollama.

    Args:
        base_url: Ollama API base URL

    Returns:
        Tuple of (success, list of model names)
    """
    url = base_url or os.getenv("OLLAMA_API_BASE") or "http://127.0.0.1:11434"

    # Remove /v1 suffix for tags endpoint
    if url.endswith("/v1"):
        url = url[:-3]

    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{url}/api/tags")
        else:
            response = requests.get(f"{url}/api/tags", timeout=10)

        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
        return False, []
    except Exception:
        return False, []


# =============================================================================
# Network Connectivity Checks
# =============================================================================

def check_network_connectivity() -> ValidationResult:
    """Check general network connectivity to LLM providers.

    Returns:
        ValidationResult with connectivity status
    """
    endpoints = [
        ("OpenAI", "https://api.openai.com"),
        ("Anthropic", "https://api.anthropic.com"),
        ("OpenRouter", "https://openrouter.ai"),
        ("Google", "https://generativelanguage.googleapis.com"),
    ]

    results = {}
    any_success = False

    for name, url in endpoints:
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=5.0) as client:
                    response = client.head(url)
            else:
                response = requests.head(url, timeout=5)
            results[name] = response.status_code < 500
            if response.status_code < 500:
                any_success = True
        except Exception:
            results[name] = False

    if any_success:
        return ValidationResult(
            status=ValidationStatus.VALID,
            message=t('settings_val_network_ok'),
            details=results
        )
    else:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            message=t('settings_val_network_fail'),
            details=results
        )


# =============================================================================
# Comprehensive Validation
# =============================================================================

def validate_all_api_keys() -> Dict[str, ValidationResult]:
    """Validate all configured API keys.

    Returns:
        Dictionary mapping key names to validation results
    """
    validators = {
        "OPENAI_API_KEY": validate_openai_key,
        "ANTHROPIC_API_KEY": validate_anthropic_key,
        "OPENROUTER_API_KEY": validate_openrouter_key,
        "GOOGLE_API_KEY": validate_google_key,
    }

    results = {}
    for key_name, validator in validators.items():
        results[key_name] = validator()

    return results


def get_configuration_status() -> Dict[str, any]:
    """Get comprehensive configuration status.

    Returns:
        Dictionary with all configuration checks
    """
    status = {
        "api_keys": validate_all_api_keys(),
        "ollama": check_ollama_running(),
        "network": check_network_connectivity(),
    }

    # Check for Ollama models if Ollama is running
    if status["ollama"].status == ValidationStatus.VALID:
        success, models = list_ollama_models()
        status["ollama_models"] = models if success else []

    return status
