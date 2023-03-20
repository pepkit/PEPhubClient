import json
from typing import Optional

import requests

from error_handling.exceptions import ResponseError


class RequestManager:
    @staticmethod
    def send_request(
        method: str,
        url: str,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> requests.Response:
        return requests.request(
            method=method,
            url=url,
            verify=False,
            cookies=cookies,
            headers=headers,
            params=params,
        )

    @staticmethod
    def decode_response(response: requests.Response) -> str:
        """
        Decode the response from GitHub and pack the returned data into appropriate model.

        Args:
            response: Response from GitHub.
            model: Model that the data will be packed to.

        Returns:
            Response data as an instance of correct model.
        """
        try:
            return response.content.decode("utf-8")
        except json.JSONDecodeError:
            raise ResponseError()