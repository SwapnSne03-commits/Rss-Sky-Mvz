import base64
import json
import time

import requests

from .config import (
    GITHUB_TOKEN,
    GITHUB_REPOSITORY,
    GITHUB_STATE_FILE,
    REQUEST_TIMEOUT,
)


class Database:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.repository = GITHUB_REPOSITORY
        self.file_path = GITHUB_STATE_FILE

        self.api_url = (
            "https://api.github.com/repos/"
            f"{self.repository}/contents/{self.file_path}"
        )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization": (
                    f"Bearer {self.token}"
                ),
                "Accept": (
                    "application/vnd.github+json"
                ),
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "RSS-Sky-Mvz-Bot",
            }
        )

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        return url.strip()

    def _check_config(self):
        if not self.token:
            raise RuntimeError(
                "GITHUB_TOKEN is missing."
            )

        if not self.repository:
            raise RuntimeError(
                "GITHUB_REPOSITORY is missing."
            )

        if not self.file_path:
            raise RuntimeError(
                "GITHUB_STATE_FILE is missing."
            )

    def _get_state(self):
        self._check_config()

        response = self.session.get(
            self.api_url,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 404:
            return {
                "posts": []
            }, None

        response.raise_for_status()

        data = response.json()

        content = data.get(
            "content",
            "",
        )

        sha = data.get(
            "sha"
        )

        if not content:
            return {
                "posts": []
            }, sha

        decoded = base64.b64decode(
            content
        ).decode("utf-8")

        try:
            state = json.loads(
                decoded
            )
        except json.JSONDecodeError:
            state = {
                "posts": []
            }

        if not isinstance(
            state,
            dict,
        ):
            state = {
                "posts": []
            }

        posts = state.get(
            "posts",
            [],
        )

        if not isinstance(
            posts,
            list,
        ):
            state["posts"] = []

        return state, sha

    def post_exists(
        self,
        post_url: str,
    ) -> bool:
        post_url = self._normalize_url(
            post_url
        )

        if not post_url:
            return False

        state, _ = self._get_state()

        return post_url in state.get(
            "posts",
            [],
        )

    def save_post(
        self,
        post_url: str,
        title: str = "",
    ) -> bool:
        post_url = self._normalize_url(
            post_url
        )

        if not post_url:
            return False

        for attempt in range(3):

            state, sha = self._get_state()

            posts = state.setdefault(
                "posts",
                [],
            )

            if post_url in posts:
                return False

            posts.append(
                post_url
            )

            new_state = {
                "posts": posts
            }

            encoded = base64.b64encode(
                json.dumps(
                    new_state,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
            ).decode("ascii")

            payload = {
                "message": (
                    "Update processed posts"
                ),
                "content": encoded,
            }

            if sha:
                payload["sha"] = sha

            response = self.session.put(
                self.api_url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code in (
                200,
                201,
            ):
                return True

            # Another update may have changed
            # the file SHA. Reload and retry.
            if response.status_code == 409:
                time.sleep(
                    1 + attempt
                )
                continue

            response.raise_for_status()

        raise RuntimeError(
            "Failed to update GitHub state file "
            "after multiple attempts."
        )
