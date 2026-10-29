"""
Ollama HTTP Client for CrimeSketchAI.

Communicates with the local Ollama instance (default: http://127.0.0.1:11434).
Configurable via backend environment variables (OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS).
Includes bounded timeouts and explicit connection error diagnostics.
"""

import json
from typing import Optional, List, Dict, Any, Callable
import urllib.request
import urllib.error
import socket

from backend.config import settings

class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass

class OllamaConnectionError(OllamaError):
    """Raised when Ollama server is unreachable or connection is refused."""
    pass

class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama HTTP request times out."""
    pass

class OllamaModelNotFoundError(OllamaError):
    """Raised when the specified model does not exist in Ollama."""
    pass

class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an error status or malformed response."""
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        http_sender: Optional[Callable[[str, str, Optional[Dict[str, Any]]], Dict[str, Any]]] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = float(timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS)
        self._http_sender = http_sender

    def chat(
        self,
        messages: List[Dict[str, str]],
        format: str = "json",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends a chat request to Ollama's /api/chat endpoint.
        Uses stream=False and format=json for structured outputs.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": format,
            "options": options or {"temperature": 0.0}
        }

        # If a custom mock sender is provided (e.g. for unit testing)
        if self._http_sender is not None:
            return self._http_sender("POST", f"{self.base_url}/api/chat", payload)

        url = f"{self.base_url}/api/chat"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.getcode()
                raw_body = resp.read().decode("utf-8")
                if status_code != 200:
                    raise OllamaResponseError(f"Ollama returned HTTP status {status_code}: {raw_body}")
                return json.loads(raw_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            if e.code == 404:
                raise OllamaModelNotFoundError(
                    f"Ollama model '{self.model}' not found at {self.base_url}. "
                    f"Ensure the model is downloaded ('ollama pull {self.model}')."
                )
            raise OllamaResponseError(f"Ollama HTTP {e.code} error: {err_body}")
        except (TimeoutError, socket.timeout) as e:
            raise OllamaTimeoutError(
                f"Ollama request to {self.base_url} timed out after {self.timeout}s during model inference. "
                f"The model '{self.model}' may need more time to complete reasoning. "
                "Consider increasing OLLAMA_TIMEOUT_SECONDS in your environment."
            )
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", None)
            if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason).lower() or "timed out" in str(e).lower():
                raise OllamaTimeoutError(
                    f"Ollama request to {self.base_url} timed out after {self.timeout}s during model inference. "
                    f"The model '{self.model}' may need more time to complete reasoning. "
                    "Consider increasing OLLAMA_TIMEOUT_SECONDS in your environment."
                )
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {e.reason or e}. "
                "Ensure the Ollama service is running on your machine ('ollama serve')."
            )
        except ConnectionRefusedError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: Connection refused. "
                "Ensure the Ollama service is running on your machine ('ollama serve')."
            )
        except OSError as e:
            if isinstance(e, (TimeoutError, socket.timeout)) or "timed out" in str(e).lower():
                raise OllamaTimeoutError(
                    f"Ollama request to {self.base_url} timed out after {self.timeout}s during model inference. "
                    f"The model '{self.model}' may need more time to complete reasoning. "
                    "Consider increasing OLLAMA_TIMEOUT_SECONDS in your environment."
                )
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {str(e)}. "
                "Ensure the Ollama service is running on your machine ('ollama serve')."
            )
        except json.JSONDecodeError as e:
            raise OllamaResponseError(f"Failed to decode Ollama JSON response: {str(e)}")

    def check_health(self) -> bool:
        """Checks if the local Ollama instance is accessible."""
        if self._http_sender is not None:
            try:
                res = self._http_sender("GET", f"{self.base_url}/api/tags", None)
                return bool(res and "models" in res)
            except Exception:
                return False

        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.getcode() == 200
        except Exception:
            return False

