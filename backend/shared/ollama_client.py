import json
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from .exceptions import OllamaUnavailableError, OllamaTimeoutError, OllamaModelError, JSONExtractionError

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "gpt-oss", timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def health_check(self) -> bool:
        """Check if Ollama is reachable and the model is available"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name') == self.model for model in models)
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.1) -> str:
        """Generate text using Ollama API"""
        try:
            client = await self._get_client()
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            logger.debug(f"Sending request to Ollama: model={self.model}, prompt_length={len(prompt)}")
            
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code != 200:
                raise OllamaModelError(f"Ollama returned status {response.status_code}: {response.text}")
            
            result = response.json()
            
            if 'error' in result:
                raise OllamaModelError(f"Ollama error: {result['error']}")
            
            response_text = result.get('response', '')
            if not response_text:
                raise OllamaModelError("Empty response from Ollama")
            
            logger.debug(f"Ollama response received: length={len(response_text)}")
            return response_text.strip()
            
        except httpx.TimeoutException:
            raise OllamaTimeoutError(f"Request to Ollama timed out after {self.timeout} seconds")
        except httpx.ConnectError:
            raise OllamaUnavailableError(f"Cannot connect to Ollama at {self.base_url}")
        except Exception as e:
            if isinstance(e, (OllamaUnavailableError, OllamaTimeoutError, OllamaModelError)):
                raise
            logger.error(f"Unexpected error in Ollama generate: {e}")
            raise OllamaModelError(f"Unexpected error: {str(e)}")

    async def extract_json(self, prompt: str, system: str = "") -> Dict[str, Any]:
        """Generate response and parse as JSON, with retry logic"""
        # Enhanced system prompt for JSON extraction
        json_system = f"""{system}

IMPORTANT: You must respond with ONLY valid JSON. Do not include any explanations, 
markdown formatting, or text outside the JSON structure. Your entire response 
must be a single JSON object that can be parsed directly."""

        try:
            response = await self.generate(prompt, json_system, temperature=0.1)
            
            # Clean up the response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Parse JSON
            try:
                parsed = json.loads(response)
                logger.debug("Successfully parsed JSON from Ollama response")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Ollama response: {e}")
                logger.debug(f"Raw response: {response[:500]}...")
                
                # Retry once with a more explicit prompt
                retry_prompt = f"""{prompt}

Please provide your response as a single JSON object. Do not include any explanations 
or markdown formatting. Example format: {{"field": "value"}}"""
                
                retry_response = await self.generate(retry_prompt, json_system, temperature=0.05)
                retry_response = retry_response.strip()
                
                if retry_response.startswith('```json'):
                    retry_response = retry_response[7:]
                if retry_response.startswith('```'):
                    retry_response = retry_response[3:]
                if retry_response.endswith('```'):
                    retry_response = retry_response[:-3]
                retry_response = retry_response.strip()
                
                try:
                    parsed = json.loads(retry_response)
                    logger.info("Successfully parsed JSON on retry attempt")
                    return parsed
                except json.JSONDecodeError:
                    raise JSONExtractionError(f"Failed to extract JSON after retry. Original error: {e}. Response: {retry_response[:200]}...")
                    
        except Exception as e:
            if isinstance(e, JSONExtractionError):
                raise
            logger.error(f"Error in extract_json: {e}")
            raise JSONExtractionError(f"Failed to extract JSON: {str(e)}")

# Global instance
ollama_client = OllamaClient()
