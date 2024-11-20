import json
import logging
from hashlib import md5, sha256
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


class KeeneticAPI:
    is_authenticated = False

    def __init__(self, base_url, username, password):
        self._base_url = base_url
        self._username = username
        self._password = password

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def connect(self):
        logger.debug("Connecting to {self._base_url}")
        self._session = aiohttp.ClientSession()
        await self.login(self._username, self._password)

    async def close(self):
        if self.is_authenticated:
            await self.logout()
        await self._session.close()

    def get_url(self, path):
        return urljoin(self._base_url, path)

    def get_headers(self, extra_headers):
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def get(self, path, extra_headers=None):
        return await self._session.get(
            self.get_url(path), headers=self.get_headers(extra_headers)
        )

    async def post(self, path, data, extra_headers=None):
        url = self.get_url(path)
        serialized_data = json.dumps(data) if data else None
        logger.debug(f"POST {url}: {serialized_data}")
        return await self._session.post(
            url,
            data=serialized_data,
            headers=self.get_headers(extra_headers),
        )

    def prepare_auth_data(self, username, password, realm, challenge):
        hash1 = md5(f"{username}:{realm}:{password}".encode("utf-8"))
        hash2 = sha256(f"{challenge}{hash1.hexdigest()}".encode("utf-8"))

        return {"login": username, "password": hash2.hexdigest()}

    async def login(self, username, password):
        challenge_response = await self.get("/auth")
        realm = challenge_response.headers.get("X-NDM-Realm")
        challenge = challenge_response.headers.get("X-NDM-Challenge")

        auth_data = self.prepare_auth_data(username, password, realm, challenge)

        auth_response = await self.post("/auth", data=auth_data)
        auth_response.raise_for_status()

        control_response = await self.get("/auth")

        control_response.raise_for_status()
        self.is_authenticated = True

    async def logout(self):
        url = self.get_url("/auth")
        logger.debug(f"DELETE {url}")
        response = await self._session.delete(url)
        response.raise_for_status()
        self.is_authenticated = False

    async def rci_interface(self):
        response = await self.get("/rci/interface")
        response.raise_for_status()
        return await response.json()

    async def get_interfaces(self):
        response = await self.post("/rci/", data={"show": {"interface": {}}})
        response.raise_for_status()
        return await response.json()

    def _is_mobile_interface(self, if_data):
        return "Mobile" in if_data.get("traits", [])

    async def get_mobile_interfaces(self):
        rci_data = await self.get_interfaces()
        return {
            if_name: if_data
            for if_name, if_data in rci_data["show"]["interface"].items()
            if self._is_mobile_interface(if_data)
        }

    async def get_sms_by_interface(self, interface_name):
        response = await self.post(
            "/rci/", data={"sms": {"interface": interface_name, "list": {}}}
        )
        return await response.json()

    async def mark_sms_as_read(self, interface_name: str, msg_ids: list[str]):
        response = await self.post(
            "/rci/",
            data={
                "sms": {
                    "interface": interface_name,
                    "read": [{"id": msg_id} for msg_id in msg_ids],
                }
            },
        )
        return await response.json()

    async def delete_sms(self, interface_name: str, msg_ids: list[str]):
        response = await self.post(
            "/rci/",
            data={
                "sms": {
                    "interface": interface_name,
                    "delete": [{"id": msg_id} for msg_id in msg_ids],
                }
            },
        )
        return await response.json()
