"""UDP broadcast discovery for zero-config Wi-Fi/LAN TaskMesh nodes."""

import asyncio
import json
import logging
import platform
import socket
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from taskmesh.core.models import NodeCapabilities

logger = logging.getLogger("taskmesh.discovery")

DEFAULT_DISCOVERY_PORT = 37020
DISCOVER_QUERY_TYPE = "TASKMESH_DISCOVER"
ANNOUNCE_TYPE = "TASKMESH_ANNOUNCE"


def get_lan_ip() -> str:
    """Discovers the active primary local LAN / Wi-Fi IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to public DNS IP (no packets sent, routes via active interface)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class DiscoveredNode(BaseModel):
    """Information gathered from a discovered TaskMesh node."""
    node_id: str
    hostname: str = "unknown"
    ip_address: str
    port: int = 8000
    orchestrator_url: Optional[str] = None
    cpu_cores: int = 1
    cpu_frequency_mhz: float = 2000.0
    ram_total_mb: int = 1024
    ram_available_mb: int = 1024
    has_gpu: bool = False
    gpu_name: Optional[str] = None
    gpu_vram_mb: int = 0
    supported_handlers: List[str] = Field(default_factory=list)
    models_loaded: List[str] = Field(default_factory=list)
    current_status: str = "online"
    discovered_at: float = Field(default_factory=time.time)


class NodeDiscoveryAdvertiser:
    """Advertises a compute node or orchestrator on the local Wi-Fi / LAN via UDP broadcast."""

    def __init__(
        self,
        node_id: str,
        capabilities: NodeCapabilities,
        port: int = DEFAULT_DISCOVERY_PORT,
        ws_port: int = 8000,
        status: str = "online",
        orchestrator_url: Optional[str] = None,
        lan_ip: Optional[str] = None,
    ) -> None:
        self.node_id = node_id
        self.caps = capabilities
        self.port = port
        self.ws_port = ws_port
        self.status = status
        self.orchestrator_url = orchestrator_url
        self.ip_address = lan_ip or get_lan_ip()
        self.hostname = platform.node() or "taskmesh-node"
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._sock: Optional[socket.socket] = None

    def build_announcement(self) -> Dict[str, Any]:
        """Creates the advertisement payload dictionary."""
        return {
            "type": ANNOUNCE_TYPE,
            "node_id": self.node_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "port": self.ws_port,
            "orchestrator_url": self.orchestrator_url,
            "cpu_cores": self.caps.cpu_cores,
            "cpu_frequency_mhz": self.caps.cpu_frequency_mhz,
            "ram_total_mb": self.caps.ram_total_mb,
            "ram_available_mb": self.caps.ram_available_mb,
            "has_gpu": self.caps.has_gpu,
            "gpu_name": self.caps.gpu_name,
            "gpu_vram_mb": self.caps.gpu_vram_mb,
            "supported_handlers": self.caps.supported_handlers,
            "models_loaded": self.caps.models_loaded or ["yolov8n"],
            "current_status": self.status,
            "timestamp": time.time(),
        }

    async def start(self) -> None:
        """Starts discovery listener in the background without blocking."""
        self.is_running = True
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            sock.bind(("", self.port))
            self._sock = sock
            self._task = asyncio.create_task(self._listener_loop())
            logger.info(f"Discovery advertiser active for [{self.node_id}] on UDP port {self.port}")
        except Exception as e:
            logger.warning(f"Could not bind discovery socket on port {self.port}: {e}. Discovery advertising disabled.")
            self.is_running = False

    async def _listener_loop(self) -> None:
        loop = asyncio.get_running_loop()
        announcement_bytes = json.dumps(self.build_announcement()).encode("utf-8")

        while self.is_running and self._sock:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 4096)
                try:
                    query = json.loads(data.decode("utf-8"))
                    if query.get("type") == DISCOVER_QUERY_TYPE:
                        # Reply directly to the sender
                        await loop.sock_sendto(self._sock, announcement_bytes, addr)
                except Exception:
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Discovery listener loop tick: {e}")
                await asyncio.sleep(0.5)

    async def stop(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        if self._sock:
            self._sock.close()
            self._sock = None


class DiscoveryClient:
    """Broadcasts probe queries across local Wi-Fi to locate TaskMesh nodes."""

    @staticmethod
    async def discover(
        timeout_seconds: float = 2.0,
        port: int = DEFAULT_DISCOVERY_PORT,
    ) -> List[DiscoveredNode]:
        """Probes the network and returns discovered nodes."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.2)

        probe = json.dumps({"type": DISCOVER_QUERY_TYPE, "timestamp": time.time()}).encode("utf-8")

        try:
            sock.sendto(probe, ("<broadcast>", port))
        except Exception as e:
            logger.warning(f"Failed to broadcast discovery probe: {e}")
            sock.close()
            return []

        discovered: Dict[str, DiscoveredNode] = {}
        end_time = time.time() + timeout_seconds

        loop = asyncio.get_running_loop()

        def _collect() -> None:
            while time.time() < end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    parsed = json.loads(data.decode("utf-8"))
                    if parsed.get("type") == ANNOUNCE_TYPE:
                        node_id = parsed.get("node_id")
                        if node_id and node_id not in discovered:
                            discovered[node_id] = DiscoveredNode(
                                node_id=node_id,
                                hostname=parsed.get("hostname", "unknown"),
                                ip_address=parsed.get("ip_address", addr[0]),
                                port=parsed.get("port", 8000),
                                orchestrator_url=parsed.get("orchestrator_url"),
                                cpu_cores=parsed.get("cpu_cores", 1),
                                cpu_frequency_mhz=parsed.get("cpu_frequency_mhz", 2000.0),
                                ram_total_mb=parsed.get("ram_total_mb", 1024),
                                ram_available_mb=parsed.get("ram_available_mb", 1024),
                                has_gpu=parsed.get("has_gpu", False),
                                gpu_name=parsed.get("gpu_name"),
                                gpu_vram_mb=parsed.get("gpu_vram_mb", 0),
                                supported_handlers=parsed.get("supported_handlers", []),
                                models_loaded=parsed.get("models_loaded", []),
                                current_status=parsed.get("current_status", "online"),
                            )
                except socket.timeout:
                    continue
                except Exception:
                    break

        await loop.run_in_executor(None, _collect)
        sock.close()
        return list(discovered.values())

    @staticmethod
    def discover_sync(timeout_seconds: float = 2.0, port: int = DEFAULT_DISCOVERY_PORT) -> List[DiscoveredNode]:
        """Synchronous version for CLI execution."""
        try:
            return asyncio.run(DiscoveryClient.discover(timeout_seconds=timeout_seconds, port=port))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(DiscoveryClient.discover(timeout_seconds=timeout_seconds, port=port))
            finally:
                loop.close()
