"""LLM client for news analysis using AWS Bedrock with cross-region inference support."""
import json
import os
from typing import Dict, Any, Optional, List
from aws_lambda_powertools import Logger
import boto3

logger = Logger(child=True)


class LLMClient:
    """Client for interacting with AWS Bedrock models with cross-region inference support."""

    def __init__(self):
        """Initialize Bedrock client with cross-region inference support."""
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
        self.temperature = float(os.environ.get('LLM_TEMPERATURE', '0.3'))
        self.max_tokens = int(os.environ.get('LLM_MAX_TOKENS', '1000'))

        # Detect if using inference profile (cross-region) or direct model ID
        self.is_inference_profile = self._is_inference_profile(self.model_id)
        self.use_cross_region = os.environ.get('USE_CROSS_REGION_INFERENCE', 'true').lower() == 'true'

        # Initialize Bedrock Runtime client
        # For cross-region inference, we use the standard endpoint
        self.bedrock_runtime = boto3.client('bedrock-runtime')

        inference_type = "inference profile (cross-region)" if self.is_inference_profile else "model ID (single-region)"
        logger.info(f"Initialized Bedrock client with {inference_type}: {self.model_id}")

    @staticmethod
    def _is_inference_profile(model_id: str) -> bool:
        """Check if the model ID is an inference profile for cross-region inference.

        Inference profiles start with region prefixes like 'us.', 'eu.', etc.

        Args:
            model_id: Model ID or inference profile ID

        Returns:
            bool: True if inference profile, False if direct model ID
        """
        # Inference profiles have format: {region}.{provider}.{model-name}
        # Examples: us.anthropic.claude-3-5-sonnet-20241022-v2:0
        #           eu.anthropic.claude-3-haiku-20240307-v1:0
        inference_prefixes = ['us.', 'eu.', 'ap.']
        return any(model_id.startswith(prefix) for prefix in inference_prefixes)

    def _get_base_model_provider(self) -> str:
        """Extract the base model provider from model ID or inference profile.

        Returns:
            str: Model provider (anthropic, meta, amazon, ai21, cohere)
        """
        # For inference profiles like "us.anthropic.claude-...", extract "anthropic"
        # For direct model IDs like "anthropic.claude-...", extract "anthropic"
        parts = self.model_id.split('.')

        if self.is_inference_profile:
            # Format: region.provider.model
            # Example: us.anthropic.claude-3-5-sonnet
            return parts[1] if len(parts) > 1 else parts[0]
        else:
            # Format: provider.model
            # Example: anthropic.claude-3-5-sonnet
            return parts[0]

    def analyze_news(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze news using Bedrock model with cross-region inference support.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt with news details

        Returns:
            dict: Analysis result

        Raises:
            Exception: If Bedrock call fails
        """
        try:
            # Determine model provider (works for both inference profiles and direct model IDs)
            provider = self._get_base_model_provider()

            if provider == 'anthropic':
                return self._analyze_with_claude(system_prompt, user_prompt)
            elif provider == 'meta':
                return self._analyze_with_llama(system_prompt, user_prompt)
            elif provider == 'amazon':
                return self._analyze_with_titan(system_prompt, user_prompt)
            elif provider == 'ai21':
                return self._analyze_with_ai21(system_prompt, user_prompt)
            elif provider == 'cohere':
                return self._analyze_with_cohere(system_prompt, user_prompt)
            else:
                # Default to Claude format
                logger.warning(f"Unknown provider '{provider}', defaulting to Claude format")
                return self._analyze_with_claude(system_prompt, user_prompt)

        except Exception as e:
            logger.error(f"Error in Bedrock analysis: {str(e)}")
            raise

    def extract_and_analyze(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Extract stock symbol and analyze news in a single LLM call.

        This method combines symbol extraction and news analysis into one call,
        reducing Bedrock API costs by ~50%.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt with news details

        Returns:
            dict: Combined result with stock_symbol and analysis, or None if no symbol found

        Raises:
            Exception: If Bedrock call fails
        """
        try:
            # Use the standard analyze_news method
            result = self.analyze_news(system_prompt, user_prompt)

            # Validate that we got a stock symbol
            stock_symbol = result.get('stock_symbol')
            if not stock_symbol or stock_symbol.lower() == 'null':
                logger.info("No stock symbol found in combined analysis")
                return None

            # Normalize stock symbol to uppercase
            result['stock_symbol'] = stock_symbol.upper()

            logger.info(f"Combined analysis complete: {result['stock_symbol']} - {result['direction']}")
            return result

        except Exception as e:
            logger.error(f"Error in combined extract and analyze: {str(e)}")
            raise

    def extract_stock_symbols(self, news_title: str, news_content: str) -> list[str]:
        """Extract Indian stock symbols from news text using LLM.

        Args:
            news_title: News article title
            news_content: News article content

        Returns:
            list: List of stock  found in the text
        """
        try:
            # Create a focused prompt for symbol extraction
            system_prompt = """You are a financial analyst specializing in Indian stock markets (NSE/BSE).
Your task is to extract relevant NSE/BSE stock symbols from news articles.

Rules:
- Extract only valid NSE/BSE-listed stock symbols (e.g., RELIANCE, TCS, INFY).
- Ignore common words, generic acronyms, government bodies, indices, commodities, or abbreviations that are not stock symbols.
- If a company name is mentioned, return its correct NSE/BSE stock symbol.
- If no explicit company or stock symbol is mentioned, infer the most relevant listed Indian stock(s) based on:
- The company’s Indian subsidiary or parent
- The sector or industry clearly impacted by the news
- The most directly affected major NSE/BSE-listed company
- Do not invent symbols without strong contextual relevance.
- Return ONLY the stock symbols as a JSON array.
- If no relevant NSE/BSE stock can be reasonably inferred, return an empty array []."""

            user_prompt = f"""Extract Indian stock symbols from this news:

Title: {news_title[:200]}
Content: {news_content[:500]}

Return ONLY a JSON array of stock symbols, for example:
["RELIANCE", "TCS", "INFY"]

If no symbols found, return: []"""

            # Use Claude for extraction (fast and accurate)
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,  # Small response needed
                "temperature": 0.0,  # Deterministic
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']

            # Parse JSON array from response
            import re
            # Extract JSON array from response (handle markdown code blocks)
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                symbols = json.loads(json_match.group(0))
                logger.info(f"LLM extracted symbols: {symbols}")
                return symbols if isinstance(symbols, list) else []
            else:
                logger.warning(f"No JSON array found in LLM response: {response_text}")
                return []

        except Exception as e:
            logger.error(f"Error extracting stock symbols with LLM: {str(e)}")
            # Fallback to empty list rather than failing
            return []

    def _analyze_with_claude(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze using Anthropic Claude via Bedrock.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            dict: Parsed JSON response
        """
        try:
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']

            # Parse JSON from response
            result = json.loads(response_text)
            logger.info(f"Successfully analyzed with Claude via Bedrock")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {str(e)}")
            logger.error(f"Response text: {response_text if 'response_text' in locals() else 'N/A'}")
            raise
        except Exception as e:
            logger.error(f"Bedrock Claude API error: {str(e)}")
            raise

    def _analyze_with_llama(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze using Meta Llama via Bedrock.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            dict: Parsed JSON response
        """
        try:
            # Prepare request body for Llama
            full_prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]"

            request_body = {
                "prompt": full_prompt,
                "max_gen_len": self.max_tokens,
                "temperature": self.temperature,
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['generation']

            # Parse JSON from response
            result = json.loads(response_text)
            logger.info(f"Successfully analyzed with Llama via Bedrock")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Llama JSON response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Bedrock Llama API error: {str(e)}")
            raise

    def _analyze_with_titan(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze using Amazon Titan via Bedrock.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            dict: Parsed JSON response
        """
        try:
            # Combine system and user prompts for Titan
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            request_body = {
                "inputText": full_prompt,
                "textGenerationConfig": {
                    "maxTokenCount": self.max_tokens,
                    "temperature": self.temperature,
                }
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['results'][0]['outputText']

            # Parse JSON from response
            result = json.loads(response_text)
            logger.info(f"Successfully analyzed with Titan via Bedrock")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Titan JSON response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Bedrock Titan API error: {str(e)}")
            raise

    def _analyze_with_ai21(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze using AI21 Labs via Bedrock.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            dict: Parsed JSON response
        """
        try:
            # Combine system and user prompts for AI21
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            request_body = {
                "prompt": full_prompt,
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['completions'][0]['data']['text']

            # Parse JSON from response
            result = json.loads(response_text)
            logger.info(f"Successfully analyzed with AI21 via Bedrock")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI21 JSON response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Bedrock AI21 API error: {str(e)}")
            raise

    def _analyze_with_cohere(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Analyze using Cohere via Bedrock.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            dict: Parsed JSON response
        """
        try:
            # Combine system and user prompts for Cohere
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            request_body = {
                "prompt": full_prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            response_text = response_body['generations'][0]['text']

            # Parse JSON from response
            result = json.loads(response_text)
            logger.info(f"Successfully analyzed with Cohere via Bedrock")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Cohere JSON response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Bedrock Cohere API error: {str(e)}")
            raise
