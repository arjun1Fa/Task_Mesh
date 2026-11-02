"""Worker-side YOLO model provisioning and local cache management."""

import hashlib
import logging
import os
import shutil
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("taskmesh.node.provisioner")

# Official Ultralytics YOLOv8 release weights metadata
PINNED_MODELS: Dict[str, Dict[str, Any]] = {
    "yolov8n": {
        "filename": "yolov8n.pt",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt",
        "expected_sha256": "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36",
        "version": "8.4.33",
        "size_bytes": 6549796,
        "classes": 80,
    },
    "yolov8s": {
        "filename": "yolov8s.pt",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt",
        "version": "8.4.33",
        "size_bytes": 22579200,
        "classes": 80,
    },
}

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".taskmesh", "models")


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


class ModelProvisioner:
    """Manages worker-local AI model weight caching, verification, and runtime loading."""

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self.cache_dir = os.path.abspath(cache_dir or os.getenv("TASKMESH_MODEL_CACHE_DIR", DEFAULT_CACHE_DIR))
        os.makedirs(self.cache_dir, exist_ok=True)
        self._loaded_models: Dict[str, Any] = {}
        self._model_metadata: Dict[str, Dict[str, Any]] = {}

    def get_model_path(self, model_name: str) -> str:
        """Returns the canonical local file path for a model."""
        clean_name = model_name.replace(".pt", "")
        meta = PINNED_MODELS.get(clean_name, {})
        filename = meta.get("filename", f"{clean_name}.pt")
        return os.path.join(self.cache_dir, filename)

    def is_model_cached(self, model_name: str) -> bool:
        """Checks if valid model weights exist in the local cache."""
        path = self.get_model_path(model_name)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return False
        clean_name = model_name.replace(".pt", "")
        meta = PINNED_MODELS.get(clean_name)
        if meta and meta.get("expected_sha256"):
            file_sha = compute_file_sha256(path)
            if file_sha != meta["expected_sha256"].lower():
                logger.warning(
                    f"Model {model_name} in {path} failed SHA-256 verification (got {file_sha}, expected {meta['expected_sha256']})"
                )
                return False
        return True

    def ensure_model(self, model_name: str, force_download: bool = False) -> str:
        """Ensures the specified model is present and verified in the worker-local cache.
        
        If missing, attempts to copy from current working directory or download from trusted source.
        Returns the verified file path.
        """
        clean_name = model_name.replace(".pt", "")
        target_path = self.get_model_path(model_name)

        if not force_download and self.is_model_cached(clean_name):
            logger.info(f"Using cached YOLO model at {target_path}")
            return target_path

        # 1. Check if model exists in working directory (e.g. pre-downloaded)
        local_candidate = os.path.join(os.getcwd(), f"{clean_name}.pt")
        if os.path.isfile(local_candidate):
            logger.info(f"Copying pre-existing model from {local_candidate} to cache {target_path}")
            shutil.copy2(local_candidate, target_path)
            if self.is_model_cached(clean_name):
                return target_path

        # 2. Download from official Ultralytics release assets
        meta = PINNED_MODELS.get(clean_name)
        url = meta.get("url") if meta else f"https://github.com/ultralytics/assets/releases/download/v8.4.0/{clean_name}.pt"
        logger.info(f"Downloading model {model_name} from {url} to {target_path}...")

        import urllib.request
        temp_path = f"{target_path}.tmp.{int(time.time())}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TaskMesh-ModelProvisioner/0.2.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as response, open(temp_path, "wb") as out_f:
                shutil.copyfileobj(response, out_f)
            
            # Verify downloaded file
            if meta and meta.get("expected_sha256"):
                downloaded_sha = compute_file_sha256(temp_path)
                if downloaded_sha != meta["expected_sha256"].lower():
                    raise ValueError(
                        f"Downloaded model SHA-256 mismatch: got {downloaded_sha}, expected {meta['expected_sha256']}"
                    )

            os.replace(temp_path, target_path)
            logger.info(f"Model {model_name} provisioned successfully at {target_path}")
            return target_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to provision model {model_name}: {e}")
            raise RuntimeError(f"Could not provision YOLO model '{model_name}': {e}") from e

    def detect_backend(self) -> Tuple[str, Optional[str], Optional[int]]:
        """Detects available hardware inference backend (CPU or CUDA GPU).
        
        Returns: (backend_name, gpu_name, gpu_vram_mb)
        """
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_vram = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
                return "cuda:0", gpu_name, gpu_vram
        except Exception:
            pass
        return "cpu", None, None

    def verify_and_load(self, model_name: str = "yolov8n") -> Tuple[bool, Optional[Any], Dict[str, Any]]:
        """Verifies that the model weights exist, can be parsed by Ultralytics, and are ready for inference.
        
        Returns: (is_ready, loaded_model_or_none, readiness_info_dict)
        """
        clean_name = model_name.replace(".pt", "")
        if clean_name in self._loaded_models:
            return True, self._loaded_models[clean_name], self._model_metadata.get(clean_name, {})

        backend, gpu_name, gpu_vram = self.detect_backend()
        info: Dict[str, Any] = {
            "model_name": clean_name,
            "backend": backend,
            "gpu_name": gpu_name,
            "gpu_vram_mb": gpu_vram,
            "available": False,
            "loadable": False,
            "cached": False,
            "weights_path": self.get_model_path(clean_name),
            "version": PINNED_MODELS.get(clean_name, {}).get("version", "8.4.33"),
            "classes": PINNED_MODELS.get(clean_name, {}).get("classes", 80),
            "error": None,
        }

        try:
            # 1. Ensure weights exist in cache
            weights_path = self.ensure_model(clean_name)
            info["cached"] = True
            info["weights_path"] = weights_path
            info["checksum"] = compute_file_sha256(weights_path)

            # 2. Load model into memory via Ultralytics
            from ultralytics import YOLO
            t0 = time.perf_counter()
            model = YOLO(weights_path)
            # Warm up with device check
            device = "cuda:0" if backend.startswith("cuda") else "cpu"
            model.to(device)
            load_duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            info["load_duration_ms"] = load_duration_ms
            info["available"] = True
            info["loadable"] = True
            info["device"] = device

            # Cache the loaded model
            self._loaded_models[clean_name] = model
            self._model_metadata[clean_name] = info
            logger.info(f"YOLO model '{clean_name}' verified and loaded on {device} ({load_duration_ms}ms)")
            return True, model, info

        except Exception as e:
            err_msg = f"Failed to load YOLO model '{clean_name}': {e}"
            logger.error(err_msg, exc_info=True)
            info["error"] = str(e)
            self._model_metadata[clean_name] = info
            return False, None, info


# Singleton provisioner instance for node agents
_GLOBAL_PROVISIONER: Optional[ModelProvisioner] = None


def get_model_provisioner(cache_dir: Optional[str] = None) -> ModelProvisioner:
    """Returns singleton ModelProvisioner instance."""
    global _GLOBAL_PROVISIONER
    if _GLOBAL_PROVISIONER is None or (cache_dir and _GLOBAL_PROVISIONER.cache_dir != os.path.abspath(cache_dir)):
        _GLOBAL_PROVISIONER = ModelProvisioner(cache_dir=cache_dir)
    return _GLOBAL_PROVISIONER


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TaskMesh YOLO Model Provisioner CLI")
    parser.add_argument("--model", default="yolov8n", help="Model name (e.g. yolov8n)")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Target cache directory")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()

    prov = ModelProvisioner(cache_dir=args.cache_dir)
    print(f"[*] Provisioning model '{args.model}' in cache dir: {prov.cache_dir}")
    ready, _, meta = prov.verify_and_load(args.model)
    if ready:
        print(f"[OK] Model '{args.model}' is provisioned and ready on {meta['backend']}!")
        print(f"     Path: {meta['weights_path']}")
        print(f"     SHA256: {meta.get('checksum')}")
        print(f"     Load Time: {meta.get('load_duration_ms')}ms")
    else:
        print(f"[FAILED] Could not verify model '{args.model}': {meta.get('error')}")

