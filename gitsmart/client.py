import httpx

from gitsmart.config import load_config, DEFAULT_API_URL, TIMEOUT_DEFAULT


class GitSmartAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class GitSmartClient:
    def __init__(self, api_key=None, api_url=None):
        config = load_config()
        self.api_key = api_key or config.get("api_key")
        self.api_url = (api_url or config.get("api_url") or DEFAULT_API_URL).rstrip("/")

    def _headers(self):
        return {"X-API-Key": self.api_key}

    def _handle_response(self, resp):
        if resp.status_code == 401:
            raise GitSmartAPIError("Invalid or expired API key.", status_code=401)
        if resp.status_code == 402:
            # Payment Required - insufficient credits
            try:
                error_data = resp.json()
                detail = error_data.get("detail", {})
                if isinstance(detail, dict):
                    message = detail.get("message", "Insufficient credits")
                    current_balance = detail.get("current_balance")
                    if current_balance is not None:
                        message = f"{message}\nCurrent balance: {current_balance} credits"
                else:
                    message = str(detail)
                raise GitSmartAPIError(message, status_code=402)
            except (ValueError, KeyError):
                raise GitSmartAPIError("Insufficient credits.", status_code=402)
        if resp.status_code == 429:
            raise GitSmartAPIError("Rate limit exceeded.", status_code=429)
        if resp.status_code == 422:
            # Validation error
            try:
                error_data = resp.json()
                detail = error_data.get("detail", "Validation error")
                # FastAPI validation errors are often lists
                if isinstance(detail, list):
                    errors = "\n".join([f"  • {err.get('msg', str(err))}" for err in detail])
                    message = f"Validation error:\n{errors}"
                elif isinstance(detail, dict):
                    message = f"Validation error: {detail.get('message', str(detail))}"
                else:
                    message = f"Validation error: {detail}"
                raise GitSmartAPIError(message, status_code=422)
            except (ValueError, KeyError):
                raise GitSmartAPIError("Validation error.", status_code=422)
        resp.raise_for_status()
        return resp.json()

    def _request(self, method, path, timeout=None, **kwargs):
        timeout = timeout if timeout is not None else TIMEOUT_DEFAULT
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, f"{self.api_url}{path}", headers=self._headers(), **kwargs)
                return self._handle_response(resp)
        except httpx.ConnectError:
            raise GitSmartAPIError(f"Cannot connect to {self.api_url}. Check your connection.")
        except httpx.TimeoutException:
            raise GitSmartAPIError("Request timed out.")
        except GitSmartAPIError:
            raise
        except httpx.HTTPStatusError as e:
            raise GitSmartAPIError(f"API error: {e.response.status_code}")

    def get(self, path, timeout=None):
        return self._request("GET", path, timeout=timeout)

    def post(self, path, json, timeout=None):
        return self._request("POST", path, json=json, timeout=timeout)

    def get_search_anchor(self, repository_url, timeout=None):
        """
        Get last synced commit hash for search RAG.

        Args:
            repository_url: Git repository URL
            timeout: Request timeout

        Returns:
            dict: {"hash": "abc123", "full_hash": "abc123..."} or {"hash": null, "full_hash": null}
        """
        return self.post("/v1/git/search/anchor", {"repository_url": repository_url}, timeout=timeout)

    def search_commits(self, query, repository_url, commits, language="en", filters=None, timeout=None):
        """
        Search through git history using AI.

        Args:
            query: Search query string
            repository_url: Git repository URL
            commits: List of commit dictionaries
            language: Response language (en/ru/uk)
            filters: Optional filters dict (author, email)
            timeout: Request timeout

        Returns:
            dict: {
                "answer": str,
                "relevant_commits": list,
                "total_analyzed": int,
                "credits_charged": int
            }
        """
        payload = {
            "query": query,
            "repository_url": repository_url,
            "commits": commits,
            "language": language
        }

        if filters:
            payload["filters"] = filters

        return self.post("/v1/git/search", payload, timeout=timeout)
