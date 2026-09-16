import base64
import json
import time

import requests

from .config import (
    GITHUB_TOKEN,
    GITHUB_REPOSITORY,
    GITHUB_STATE_FILE,
    SKY_AUTHORIZED_GROUPS_FILE,
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

        # -------------------------------------------------
        # SKY SEARCH AUTHORIZED GROUPS
        # -------------------------------------------------

        self.authorized_groups_file = (
            SKY_AUTHORIZED_GROUPS_FILE
        )

        self.authorized_groups_api_url = (
            "https://api.github.com/repos/"
            f"{self.repository}/contents/"
            f"{self.authorized_groups_file}"
        )

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        return url.strip()

    @staticmethod
    def _normalize_chat_id(
        chat_id,
    ) -> str:
        return str(chat_id).strip()

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

        if not self.authorized_groups_file:
            raise RuntimeError(
                "SKY_AUTHORIZED_GROUPS_FILE is missing."
            )

    # =====================================================
    # GENERIC GITHUB STATE READER
    # =====================================================

    def _get_github_state(
        self,
        api_url: str,
        default_state: dict,
    ):
        self._check_config()

        response = self.session.get(
            api_url,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 404:
            return default_state.copy(), None

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
            return default_state.copy(), sha

        decoded = base64.b64decode(
            content
        ).decode("utf-8")

        try:
            state = json.loads(
                decoded
            )

        except json.JSONDecodeError:
            state = default_state.copy()

        if not isinstance(
            state,
            dict,
        ):
            state = default_state.copy()

        return state, sha

    # =====================================================
    # PROCESSED POSTS
    # =====================================================

    def _get_state(self):
        return self._get_github_state(
            self.api_url,
            {
                "posts": []
            },
        )

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

    # =====================================================
    # SKY SEARCH GROUP AUTHORIZATION
    # =====================================================

    def _get_authorized_groups_state(self):
        return self._get_github_state(
            self.authorized_groups_api_url,
            {
                "groups": []
            },
        )

    def is_group_authorized(
        self,
        chat_id,
    ) -> bool:

        chat_id = self._normalize_chat_id(
            chat_id
        )

        if not chat_id:
            return False

        state, _ = (
            self._get_authorized_groups_state()
        )

        groups = state.get(
            "groups",
            [],
        )

        if not isinstance(
            groups,
            list,
        ):
            return False

        return chat_id in {
            self._normalize_chat_id(group_id)
            for group_id in groups
        }

    def add_authorized_group(
        self,
        chat_id,
    ) -> bool:

        chat_id = self._normalize_chat_id(
            chat_id
        )

        if not chat_id:
            return False

        for attempt in range(3):

            state, sha = (
                self._get_authorized_groups_state()
            )

            groups = state.setdefault(
                "groups",
                [],
            )

            groups = [
                self._normalize_chat_id(
                    group_id
                )
                for group_id in groups
                if str(group_id).strip()
            ]

            if chat_id in groups:
                return False

            groups.append(
                chat_id
            )

            new_state = {
                "groups": groups
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
                    "Add Sky authorized group"
                ),
                "content": encoded,
            }

            if sha:
                payload["sha"] = sha

            response = self.session.put(
                self.authorized_groups_api_url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code in (
                200,
                201,
            ):
                return True

            if response.status_code == 409:
                time.sleep(
                    1 + attempt
                )
                continue

            response.raise_for_status()

        raise RuntimeError(
            "Failed to update Sky authorized "
            "groups after multiple attempts."
        )

    def remove_authorized_group(
        self,
        chat_id,
    ) -> bool:

        chat_id = self._normalize_chat_id(
            chat_id
        )

        if not chat_id:
            return False

        for attempt in range(3):

            state, sha = (
                self._get_authorized_groups_state()
            )

            groups = state.get(
                "groups",
                [],
            )

            if not isinstance(
                groups,
                list,
            ):
                groups = []

            normalized_groups = [
                self._normalize_chat_id(
                    group_id
                )
                for group_id in groups
            ]

            if chat_id not in normalized_groups:
                return False

            new_groups = [
                group_id
                for group_id in normalized_groups
                if group_id != chat_id
            ]

            new_state = {
                "groups": new_groups
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
                    "Remove Sky authorized group"
                ),
                "content": encoded,
            }

            if sha:
                payload["sha"] = sha

            response = self.session.put(
                self.authorized_groups_api_url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code in (
                200,
                201,
            ):
                return True

            if response.status_code == 409:
                time.sleep(
                    1 + attempt
                )
                continue

            response.raise_for_status()

        raise RuntimeError(
            "Failed to update Sky authorized "
            "groups after multiple attempts."
        )
