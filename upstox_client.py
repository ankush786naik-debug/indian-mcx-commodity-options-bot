import os
import logging
from urllib.parse import urlparse

import requests


logger = logging.getLogger(__name__)


class UpstoxClient:
    BASE_URL = "https://api.upstox.com"

    def __init__(self, access_token=None, timeout=20):
        self.access_token = (
            access_token or os.getenv("UPSTOX_ACCESS_TOKEN")
        )

        if not self.access_token:
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is missing. "
                "Configure it as an environment variable."
            )

        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        })

    def get(self, endpoint, params=None):
        """
        Perform a read-only GET request to the Upstox API.
        Example endpoint: /v2/user/profile
        """

        parsed = urlparse(endpoint)

        if parsed.scheme or parsed.netloc:
            raise ValueError("Only relative API endpoints are allowed.")

        if not endpoint.startswith("/") or endpoint.startswith("//"):
            raise ValueError("Endpoint must start with a single slash.")

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )

            if not response.ok:
                logger.error(
                    "Upstox API returned HTTP %s for %s",
                    response.status_code,
                    endpoint,
                )
                raise RuntimeError(
                    f"Upstox API request failed: HTTP "
                    f"{response.status_code}"
                )

            try:
                result = response.json()
            except ValueError as exc:
                raise RuntimeError(
                    "Upstox returned an invalid JSON response."
                ) from exc

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Unexpected response format from Upstox."
                )

            return result

        except requests.Timeout as exc:
            raise RuntimeError(
                "Upstox API request timed out."
            ) from exc

        except requests.RequestException as exc:
            raise RuntimeError(
                "Unable to connect to Upstox API."
            ) from exc

    def close(self):
        self.session.close()
      
