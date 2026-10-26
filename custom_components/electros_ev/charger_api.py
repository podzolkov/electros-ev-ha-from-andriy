"""ElectroS EV Charger WebSocket API client."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import ssl
import struct

import aiohttp

from .const import (
    AMP_TO_INDEX,
    DEFAULT_BASE_URL,
    DEFAULT_WS_HOST,
    DEFAULT_WS_ORIGIN,
    DEFAULT_WS_PATH,
    DEFAULT_WS_PROTOCOL,
    STATUS_TEXT_EN,
    SUPPORTED_AMPS,
)

_LOGGER = logging.getLogger(__name__)


def normalize_amps(amps: int) -> int:
    """Normalize amps to nearest supported value."""
    if amps <= 0:
        return 0
    supported = [value for value in SUPPORTED_AMPS if value <= amps]
    if not supported:
        return 0
    return max(supported)


def parse_charger_state(message: str) -> dict:
    """Parse charger state from WebSocket message."""
    parts = message.split("\n")
    current_amps = int(parts[7]) if len(parts) > 7 and parts[7].isdigit() else None
    status_code = parts[8] if len(parts) > 8 else None
    measured_current = (
        int(parts[9]) / 10 if len(parts) > 9 and parts[9].isdigit() else None
    )
    mains_voltage = None
    if len(parts) > 16 and parts[16].isdigit():
        mains_voltage = int(parts[16])
    elif len(parts) > 10 and parts[10].isdigit():
        mains_voltage = int(parts[10])
    # [11] consumed energy (kWh x 1e6), [12] power (kW x 1e4), as in the web panel.
    energy_kwh = (
        round(int(parts[11]) / 1_000_000, 3)
        if len(parts) > 11 and parts[11].isdigit()
        else None
    )
    charging_power_w = (
        round(int(parts[12]) / 10, 1) if len(parts) > 12 and parts[12].isdigit() else None
    )
    return {
        "online": status_code != "7",
        "status_code": status_code,
        "status_text": STATUS_TEXT_EN.get(status_code, "unknown"),
        "current_amps": current_amps,
        "measured_current": measured_current,
        "mains_voltage": mains_voltage,
        "charging_power_w": charging_power_w,
        "energy_kwh": energy_kwh,
    }


class ElectroSApi:
    """API client for ElectroS EV Charger."""

    def __init__(
        self,
        login: str,
        password: str,
        base_url: str = DEFAULT_BASE_URL,
        ws_host: str = DEFAULT_WS_HOST,
        ws_path: str = DEFAULT_WS_PATH,
        ws_origin: str = DEFAULT_WS_ORIGIN,
        ws_protocol: str = DEFAULT_WS_PROTOCOL,
    ) -> None:
        """Initialize the API client."""
        self._login = login
        self._password = password
        self._base_url = base_url
        self._ws_host = ws_host
        self._ws_path = ws_path
        self._ws_origin = ws_origin
        self._ws_protocol = ws_protocol
        self._cookies: dict[str, str] | None = None

    async def _login_session(self) -> dict[str, str]:
        """Login and return session cookies."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            await session.get(self._base_url + "main.php", timeout=aiohttp.ClientTimeout(total=30))
            await session.post(
                self._base_url + "login.php",
                data={"username": self._login, "password": self._password},
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=True,
            )
            cookies = {cookie.key: cookie.value for cookie in session.cookie_jar}
            self._cookies = cookies
            return cookies

    async def _ws_communicate(self, message: str) -> str | None:
        """Open WebSocket, send message, receive response."""
        if not self._cookies:
            await self._login_session()

        cookie_header = "; ".join(
            f"{name}={value}" for name, value in self._cookies.items()
        )
        key = base64.b64encode(os.urandom(16)).decode()

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                self._ws_host, 443, ssl=ssl_context
            ),
            timeout=10,
        )

        request = (
            f"GET {self._ws_path} HTTP/1.1\r\n"
            f"Host: {self._ws_host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Protocol: {self._ws_protocol}\r\n"
            f"Origin: {self._ws_origin}\r\n"
            f"Cookie: {cookie_header}\r\n"
            "\r\n"
        )
        writer.write(request.encode("utf-8"))
        await writer.drain()

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=10)
            if not chunk:
                break
            response += chunk

        if b"101 Switching Protocols" not in response:
            writer.close()
            raise RuntimeError("WebSocket upgrade failed")

        # Send WebSocket text frame
        payload = message.encode("utf-8")
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        writer.write(header + masked)
        await writer.drain()

        # Receive WebSocket frame
        first = await asyncio.wait_for(reader.readexactly(2), timeout=10)
        byte1, byte2 = first
        opcode = byte1 & 0x0F
        frame_length = byte2 & 0x7F
        is_masked = (byte2 & 0x80) != 0
        if frame_length == 126:
            frame_length = struct.unpack("!H", await reader.readexactly(2))[0]
        elif frame_length == 127:
            frame_length = struct.unpack("!Q", await reader.readexactly(8))[0]
        frame_mask = await reader.readexactly(4) if is_masked else b""
        recv_payload = b""
        while len(recv_payload) < frame_length:
            chunk = await asyncio.wait_for(
                reader.read(frame_length - len(recv_payload)), timeout=10
            )
            if not chunk:
                break
            recv_payload += chunk
        if is_masked:
            recv_payload = bytes(
                byte ^ frame_mask[i % 4] for i, byte in enumerate(recv_payload)
            )

        writer.close()

        if opcode != 1:
            return None
        return recv_payload.decode("utf-8", errors="replace")

    async def get_state(self) -> dict:
        """Get charger state."""
        try:
            self._cookies = None
            await self._login_session()
            response = await self._ws_communicate(f"site {self._login}")
            if response is None:
                return self._offline_state("invalid_response")
            return parse_charger_state(response)
        except Exception as exc:
            _LOGGER.error("Failed to get charger state: %s", exc)
            return self._offline_state(f"error: {exc}")

    async def start_charging(self, amps: int) -> bool:
        """Start charging at specified amperage."""
        amps = normalize_amps(amps)
        if amps <= 0:
            return await self.stop_charging()
        try:
            self._cookies = None
            await self._login_session()
            index = AMP_TO_INDEX[amps]
            await self._ws_communicate(
                f"site {self._login}\nstart\n{index}\n0\n"
            )
            _LOGGER.info("Sent start command with %dA", amps)
            return True
        except Exception as exc:
            _LOGGER.error("Failed to start charging: %s", exc)
            return False

    async def stop_charging(self) -> bool:
        """Stop charging."""
        try:
            self._cookies = None
            await self._login_session()
            await self._ws_communicate(f"site {self._login}\nstop")
            _LOGGER.info("Sent stop command")
            return True
        except Exception as exc:
            _LOGGER.error("Failed to stop charging: %s", exc)
            return False

    async def reset_energy(self) -> bool:
        """Reset the consumed-energy (kWh) counter."""
        try:
            self._cookies = None
            await self._login_session()
            await self._ws_communicate(f"site {self._login}\nresetkwt")
            _LOGGER.info("Sent energy counter reset command")
            return True
        except Exception as exc:
            _LOGGER.error("Failed to reset energy counter: %s", exc)
            return False

    async def test_connection(self) -> bool:
        """Test connection to charger."""
        state = await self.get_state()
        return state.get("status_text") != "unknown" and "error" not in state.get(
            "status_text", ""
        )

    @staticmethod
    def _offline_state(reason: str) -> dict:
        """Return offline state dict."""
        return {
            "online": False,
            "status_code": None,
            "status_text": reason,
            "current_amps": None,
            "measured_current": None,
            "mains_voltage": None,
            "charging_power_w": None,
            "energy_kwh": None,
        }
