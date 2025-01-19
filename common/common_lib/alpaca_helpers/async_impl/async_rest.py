import asyncio
import base64
from abc import ABC
from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from itertools import chain
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    AsyncIterator,
)

import httpx
from pydantic import BaseModel

from alpaca import __version__
from alpaca.common.constants import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_WAIT_SECONDS,
    DEFAULT_RETRY_EXCEPTION_CODES,
)
from alpaca.common.exceptions import APIError, RetryException
from alpaca.common.types import RawData, HTTPResult, Credentials

from alpaca.common.constants import PageItem
from alpaca.common.enums import PaginationType, BaseURL

# --------------------------------------------------------------------------
# Helper functions to mirror the synchronous version
# --------------------------------------------------------------------------

def _get_marketdata_entries(response: HTTPResult, no_sub_key: bool) -> RawData:
    """
    Utility function to extract the data portion from the HTTP response
    for market data endpoints.
    """
    if no_sub_key:
        return response

    data_keys = {
        "bar",
        "bars",
        "corporate_actions",
        "news",
        "orderbook",
        "orderbooks",
        "quote",
        "quotes",
        "snapshot",
        "snapshots",
        "trade",
        "trades",
    }
    selected_keys = data_keys.intersection(response)
    if not selected_keys:
        raise ValueError("The data in response does not match any known marketdata keys.")
    if len(selected_keys) > 1:
        raise ValueError("The data in response matches multiple known keys.")

    selected_key = selected_keys.pop()
    if selected_key == "news":
        # If it's news, we simply return {'news': response[selected_key]}
        return {"news": response[selected_key]}
    return response[selected_key]


# --------------------------------------------------------------------------
# AsyncRestClient class
# --------------------------------------------------------------------------

class AsyncRestClient(ABC):
    """
    An asynchronous version of the RESTClient, using httpx.AsyncClient.
    """

    def __init__(
        self,
        base_url: Union[BaseURL, str],
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        use_basic_auth: bool = False,
        api_version: str = "v2",
        sandbox: bool = False,
        raw_data: bool = False,
        retry_attempts: Optional[int] = None,
        retry_wait_seconds: Optional[int] = None,
        retry_exception_codes: Optional[List[int]] = None,
    ) -> None:
        """
        Initialize the AsyncRestClient, storing credentials and configuration.
        """
        self._api_key, self._secret_key, self._oauth_token = self._validate_credentials(
            api_key=api_key,
            secret_key=secret_key,
            oauth_token=oauth_token,
        )
        self._base_url: Union[BaseURL, str] = base_url
        self._api_version: str = api_version
        self._sandbox: bool = sandbox
        self._use_raw_data: bool = raw_data
        self._use_basic_auth: bool = use_basic_auth

        # httpx.AsyncClient for async communication
        self._client: httpx.AsyncClient = httpx.AsyncClient(follow_redirects=False)

        # Set up retries
        self._retry: int = DEFAULT_RETRY_ATTEMPTS
        self._retry_wait: int = DEFAULT_RETRY_WAIT_SECONDS
        self._retry_codes: List[int] = DEFAULT_RETRY_EXCEPTION_CODES

        if retry_attempts and retry_attempts > 0:
            self._retry = retry_attempts

        if retry_wait_seconds and retry_wait_seconds > 0:
            self._retry_wait = retry_wait_seconds

        if retry_exception_codes:
            self._retry_codes = retry_exception_codes

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        base_url: Optional[Union[BaseURL, str]] = None,
        api_version: Optional[str] = None,
    ) -> HTTPResult:
        """
        Prepares and submits an HTTP request to the given API endpoint
        and returns the response, handling retries if needed.
        """
        base_url = base_url or self._base_url
        version = api_version if api_version else self._api_version
        url: str = f"{base_url}/{version}{path}"

        headers = self._get_default_headers()

        # Build request options
        opts: Dict[str, Any] = {"headers": headers}
        for k, v in list(data.items()):
            if isinstance(v, Enum):
                data[k] = v.value
            if v is None:
                del data[k]
        # Decide whether to send data as query params or JSON
        if method.upper() in ["GET", "DELETE"]:
            opts["params"] = data
        else:
            opts["json"] = data

        # Attempt the request with retries
        retry = self._retry
        while retry >= 0:
            try:
                return await self._one_request(method, url, opts, retry)
            except RetryException:
                # Wait and retry
                await asyncio.sleep(self._retry_wait)
                retry -= 1
                continue

    async def _one_request(
        self,
        method: str,
        url: str,
        opts: Dict[str, Any],
        retry: int,
    ) -> dict:
        """
        Perform one HTTP request attempt with the given method/URL/options.
        Raises `RetryException` for certain HTTP status codes (e.g., 429)
        if the retry limit is not yet reached.
        Otherwise, raises `APIError` for other HTTP errors.
        Returns the response JSON if the request is successful.
        """
        response = await self._client.request(method, url, **opts)

        # Raise for HTTP errors
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as http_error:
            status_code = response.status_code
            # If we have a retry code (e.g., 429) and still have attempts left
            if status_code in self._retry_codes and retry > 0:
                raise RetryException()

            # Otherwise, raise an APIError
            raise APIError(response.text, http_error)

        # Return JSON if available
        if response.text:
            return response.json()
        else:
            # e.g., 204 No Content
            return {}

    def _get_default_headers(self) -> Dict[str, str]:
        """
        Returns default headers for every request,
        including Auth and User-Agent.
        """
        headers = self._get_auth_headers()
        headers["User-Agent"] = f"APCA-PY-ASYNC/{__version__}"
        return headers

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Returns a dictionary of authentication headers depending
        on whether we're using OAuth, Basic Auth, or Key-based.
        """
        headers: Dict[str, str] = {}

        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"
        elif self._use_basic_auth:
            api_key_secret = f"{self._api_key}:{self._secret_key}".encode("utf-8")
            encoded_api_key_secret = base64.b64encode(api_key_secret).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded_api_key_secret}"
        else:
            headers["APCA-API-KEY-ID"] = self._api_key
            headers["APCA-API-SECRET-KEY"] = self._secret_key

        return headers

    # ----------------------------------------------------------------------
    # Public async methods for HTTP verbs
    # ----------------------------------------------------------------------

    async def get(
        self,
        path: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        **kwargs,
    ) -> HTTPResult:
        """Perform an async GET request."""
        return await self._request("GET", path, data, **kwargs)

    async def post(
        self,
        path: str,
        data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> HTTPResult:
        """Perform an async POST request."""
        return await self._request("POST", path, data)

    async def put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> HTTPResult:
        """Perform an async PUT request."""
        return await self._request("PUT", path, data)

    async def patch(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> HTTPResult:
        """Perform an async PATCH request."""
        return await self._request("PATCH", path, data)

    async def delete(
        self,
        path: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
    ) -> HTTPResult:
        """Perform an async DELETE request."""
        return await self._request("DELETE", path, data)

    # ----------------------------------------------------------------------
    # Response helper
    # ----------------------------------------------------------------------

    def response_wrapper(
        self,
        model: Type[BaseModel],
        raw_data: RawData,
        **kwargs,
    ) -> Union[BaseModel, RawData]:
        """
        Optionally wrap the raw data in a Pydantic model,
        or return the raw data directly, depending on config.
        """
        if self._use_raw_data:
            return raw_data
        return model(raw_data=raw_data, **kwargs)

    # ----------------------------------------------------------------------
    # Pagination helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _validate_pagination(
        max_items_limit: Optional[int],
        handle_pagination: Optional[PaginationType],
    ) -> PaginationType:
        if handle_pagination is None:
            handle_pagination = PaginationType.FULL

        if handle_pagination != PaginationType.FULL and max_items_limit is not None:
            raise ValueError(
                "max_items_limit can only be specified for PaginationType.FULL"
            )
        return handle_pagination

    @staticmethod
    def _return_paginated_result(
        iterator: AsyncIterator[PageItem],
        handle_pagination: PaginationType,
    ) -> Union[List[PageItem], AsyncIterator[List[PageItem]]]:
        """
        Convert an async iterator that yields pages into the
        desired pagination shape (no pagination, full list, or iterator).
        """

        # If user wants no pagination, just gather a single page
        # If user wants all pages, gather them all
        # If user wants an iterator, return the async iterator itself

        async def _single_page() -> List[PageItem]:
            return await anext(iterator, [])

        async def _full_list() -> List[PageItem]:
            # Flatten all pages
            items = []
            async for page in iterator:
                items.extend(page)
            return items

        if handle_pagination == PaginationType.NONE:
            # Return one page as a list
            return [PageItem] if False else _single_page()  # structured for clarity
        elif handle_pagination == PaginationType.FULL:
            # Return all pages combined into one list
            return [PageItem] if False else _full_list()
        elif handle_pagination == PaginationType.ITERATOR:
            return iterator
        else:
            raise ValueError(f"Invalid pagination type: {handle_pagination}.")

    # ----------------------------------------------------------------------
    # Marketdata example method
    # ----------------------------------------------------------------------

    async def _get_marketdata(
        self,
        path: str,
        params: Dict[str, Any],
        page_limit: int = 10_000,
        no_sub_key: bool = False,
    ) -> Dict[str, List[Any]]:
        """
        Example of how to replicate the synchronous marketdata
        pagination in an async style.
        """
        d = defaultdict(list)
        limit = params.get("limit")
        total_items = 0
        page_token = params.get("page_token")

        while True:
            actual_limit = None

            if limit:
                # If the user specified a limit overall, adjust
                # the per-page limit to avoid overshooting
                actual_limit = min(int(limit) - total_items, page_limit)
                if actual_limit < 1:
                    break

            params["limit"] = actual_limit
            params["page_token"] = page_token

            response = await self.get(path=path, data=params)
            chunk = _get_marketdata_entries(response, no_sub_key)

            for k, v in chunk.items():
                if isinstance(v, list):
                    d[k].extend(v)
                else:
                    d[k] = v

            # Keep track of how many items so far
            if actual_limit:
                total_items = sum([len(items) for items in d.values()])

            # Check for a next page token
            page_token = response.get("next_page_token", None)
            if not page_token:
                break

        return dict(d)

    # ----------------------------------------------------------------------
    # Credential validation (same as sync)
    # ----------------------------------------------------------------------
    @staticmethod
    def _validate_credentials(
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ) -> Credentials:
        """
        Ensures that either (api_key + secret_key) or oauth_token is provided.
        """
        if not oauth_token and not api_key:
            raise ValueError("You must supply a method of authentication")

        if oauth_token and (api_key or secret_key):
            raise ValueError(
                "Either an oauth_token or an api_key may be supplied, but not both"
            )

        if not oauth_token and not (api_key and secret_key):
            raise ValueError(
                "A corresponding secret_key must be supplied with the api_key"
            )

        return api_key, secret_key, oauth_token

    # ----------------------------------------------------------------------
    # Cleanup method
    # ----------------------------------------------------------------------

    async def aclose(self) -> None:
        """
        Close the underlying httpx.AsyncClient session.
        (Always remember to do this when you're done with the client!)
        """
        await self._client.aclose()