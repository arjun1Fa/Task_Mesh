"""Real-world AI Vision and OpenCV Dominant Colour Analysis Handler."""

import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("taskmesh.handlers.ai_inference")

# Standard perceptual named color dictionary (RGB tuples)
PERCEPTUAL_COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "Black": (0, 0, 0),
    "Charcoal": (40, 40, 40),
    "Dim Gray": (105, 105, 105),
    "Slate Gray": (112, 128, 144),
    "Silver": (192, 192, 192),
    "Light Gray": (211, 211, 211),
    "White": (255, 255, 255),
    "Navy Blue": (0, 0, 128),
    "Midnight Blue": (25, 25, 112),
    "Cobalt Blue": (0, 71, 171),
    "Royal Blue": (65, 105, 225),
    "Blue": (0, 0, 255),
    "Steel Blue": (70, 130, 180),
    "Dodger Blue": (30, 144, 255),
    "Sky Blue": (135, 206, 235),
    "Teal": (0, 128, 128),
    "Cyan": (0, 255, 255),
    "Forest Green": (34, 139, 34),
    "Dark Green": (0, 100, 0),
    "Emerald": (80, 200, 120),
    "Olive": (128, 128, 0),
    "Olive Drab": (107, 142, 35),
    "Lime Green": (50, 205, 50),
    "Sea Green": (46, 139, 87),
    "Sage Green": (157, 193, 131),
    "Crimson": (220, 20, 60),
    "Red": (255, 0, 0),
    "Scarlet": (255, 36, 0),
    "Dark Red": (139, 0, 0),
    "Maroon": (128, 0, 0),
    "Firebrick": (178, 34, 34),
    "Coral": (255, 127, 80),
    "Salmon": (250, 128, 114),
    "Hot Pink": (255, 105, 180),
    "Rose": (255, 0, 127),
    "Burgundy": (128, 0, 32),
    "Orange": (255, 140, 0),
    "Dark Orange": (255, 140, 0),
    "Tangerine": (242, 133, 0),
    "Amber": (255, 191, 0),
    "Gold": (255, 215, 0),
    "Yellow": (255, 255, 0),
    "Khaki": (240, 230, 140),
    "Mustard": (255, 219, 88),
    "Purple": (128, 0, 128),
    "Indigo": (75, 0, 130),
    "Violet": (238, 130, 238),
    "Plum": (221, 160, 221),
    "Lavender": (230, 230, 250),
    "Magenta": (255, 0, 255),
    "Chocolate": (123, 63, 0),
    "Saddle Brown": (139, 69, 19),
    "Brown": (165, 42, 42),
    "Tan": (210, 180, 140),
    "Beige": (245, 245, 220),
    "Sand": (194, 178, 128),
    "Ochre": (204, 119, 34),
    "Terracotta": (226, 114, 91),
}

# Precompute CIELAB vectors for named colors for constant-time nearest color matching
_NAMED_LABS: Optional[Dict[str, np.ndarray]] = None


def _get_named_labs() -> Dict[str, np.ndarray]:
    global _NAMED_LABS
    if _NAMED_LABS is None:
        labs = {}
        for name, rgb in PERCEPTUAL_COLOR_MAP.items():
            bgr_pixel = np.uint8([[[rgb[2], rgb[1], rgb[0]]]])
            lab_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2LAB)[0][0]
            labs[name] = lab_pixel.astype(np.float32)
        _NAMED_LABS = labs
    return _NAMED_LABS


def find_nearest_color_name(rgb: List[int]) -> str:
    """Finds the nearest human-readable color name using perceptual Delta-E in CIELAB space."""
    named_labs = _get_named_labs()
    bgr_pixel = np.uint8([[[int(rgb[2]), int(rgb[1]), int(rgb[0])]]])
    lab_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2LAB)[0][0].astype(np.float32)

    best_name = "Unknown"
    best_dist = float("inf")
    for name, n_lab in named_labs.items():
        dist = float(np.linalg.norm(lab_pixel - n_lab))
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def extract_dominant_colors(
    bgr_img: np.ndarray,
    k: int = 8,
    sample_limit: int = 25000,
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """Extracts dominant image colors using OpenCV K-means in CIELAB color space.
    
    Returns:
        (dominant_colors_list, rgb_centers)
    """
    k = max(3, min(12, int(k)))
    h, w = bgr_img.shape[:2]

    # Convert to CIELAB space for perceptual uniformity
    lab_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
    pixels = lab_img.reshape(-1, 3).astype(np.float32)

    # Sample pixels if image is large for speed while preserving distribution
    if len(pixels) > sample_limit:
        indices = np.random.choice(len(pixels), sample_limit, replace=False)
        sample_pixels = pixels[indices]
    else:
        sample_pixels = pixels

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 0.5)
    flags = cv2.KMEANS_PP_CENTERS
    _, labels, centers = cv2.kmeans(sample_pixels, k, None, criteria, 5, flags)

    counts = np.bincount(labels.flatten(), minlength=k)
    total_sample = np.sum(counts)
    order = np.argsort(-counts)

    # Convert centers back to RGB
    centers_uint8 = np.uint8(np.clip(centers, 0, 255)).reshape(k, 1, 3)
    rgb_centers = cv2.cvtColor(centers_uint8, cv2.COLOR_LAB2RGB).reshape(k, 3)

    palette = []
    pct_sum = 0.0
    for i, idx in enumerate(order):
        rgb = [int(x) for x in rgb_centers[idx]]
        hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}".upper()
        name = find_nearest_color_name(rgb)
        pct = round(float(counts[idx] / total_sample) * 100.0, 2)
        pct_sum += pct
        pixel_count = int(counts[idx])
        palette.append({
            "name": name,
            "nearest_name": name,
            "hex": hex_code,
            "rgb": rgb,
            "percentage": pct,
            "pixel_count": pixel_count,
        })

    # Adjust rounding discrepancy on the largest cluster so percentages sum exactly to ~100.0%
    if palette and abs(pct_sum - 100.0) > 0.001:
        palette[0]["percentage"] = round(palette[0]["percentage"] + (100.0 - pct_sum), 2)

    return palette, rgb_centers


def estimate_object_color(bgr_img: np.ndarray, bbox: List[float]) -> Dict[str, Any]:
    """Estimates dominant color of a detected object bounding box using OpenCV K-means crop."""
    h, w = bgr_img.shape[:2]
    x1 = max(0, min(w - 1, int(bbox[0])))
    y1 = max(0, min(h - 1, int(bbox[1])))
    x2 = max(x1 + 1, min(w, int(bbox[2])))
    y2 = max(y1 + 1, min(h, int(bbox[3])))

    crop = bgr_img[y1:y2, x1:x2]
    if crop.shape[0] < 4 or crop.shape[1] < 4:
        # Fallback to single center pixel
        center_bgr = bgr_img[min(h - 1, (y1 + y2) // 2), min(w - 1, (x1 + x2) // 2)]
        rgb = [int(center_bgr[2]), int(center_bgr[1]), int(center_bgr[0])]
        hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}".upper()
        return {
            "hex": hex_code,
            "rgb": rgb,
            "name": find_nearest_color_name(rgb),
            "percentage": 100.0,
            "approximation": "bounding_box_crop",
        }

    colors, _ = extract_dominant_colors(crop, k=2, sample_limit=5000)
    top = colors[0] if colors else {"hex": "#808080", "rgb": [128, 128, 128], "name": "Gray", "percentage": 100.0}
    top["approximation"] = "bounding_box_crop"
    return top


def generate_annotated_image(
    bgr_img: np.ndarray,
    detections: List[Dict[str, Any]],
    dominant_colors: List[Dict[str, Any]],
) -> bytes:
    """Renders professional bounding boxes, object color swatches, and a dominant color palette bar."""
    annotated = bgr_img.copy()
    h, w = annotated.shape[:2]

    # Draw detected objects
    for d in detections:
        bbox = d["bbox"]
        cls_name = d["class"]
        conf = d["confidence"]
        x1, y1, x2, y2 = [int(c) for c in bbox]
        
        # Determine box color from object's dominant color if available
        obj_color = d.get("object_color", {})
        rgb = obj_color.get("rgb", [0, 255, 0])
        bgr = (int(rgb[2]), int(rgb[1]), int(rgb[0]))

        # Draw bounding rectangle
        cv2.rectangle(annotated, (x1, y1), (x2, y2), bgr, 2)

        # Label banner text
        label_text = f"{cls_name} {int(conf * 100)}% ({obj_color.get('name', '')})"
        font_scale = max(0.45, min(0.7, w / 1200.0))
        thickness = 1
        (txt_w, txt_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        # Label background
        label_y1 = max(0, y1 - txt_h - 8)
        label_y2 = y1
        cv2.rectangle(annotated, (x1, label_y1), (x1 + txt_w + 24, label_y2), bgr, -1)

        # Swatch circle
        circle_x = x1 + 10
        circle_y = label_y1 + (label_y2 - label_y1) // 2
        cv2.circle(annotated, (circle_x, circle_y), 5, (255, 255, 255), -1)
        cv2.circle(annotated, (circle_x, circle_y), 4, bgr, -1)

        # Label text
        txt_color = (0, 0, 0) if (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114) > 160 else (255, 255, 255)
        cv2.putText(
            annotated,
            label_text,
            (x1 + 20, label_y2 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            txt_color,
            thickness,
            cv2.LINE_AA,
        )

    # Draw bottom dominant color palette bar (height: 28px)
    palette_height = max(24, int(h * 0.04))
    bar_y1 = h - palette_height
    curr_x = 0
    total_pct = sum(c["percentage"] for c in dominant_colors) or 100.0

    for c in dominant_colors:
        rgb = c["rgb"]
        bgr = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
        slice_w = int(round((c["percentage"] / total_pct) * w))
        next_x = min(w, curr_x + slice_w)
        cv2.rectangle(annotated, (curr_x, bar_y1), (next_x, h), bgr, -1)
        curr_x = next_x

    # Encode as JPEG
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    _, enc = cv2.imencode(".jpg", annotated, encode_params)
    return enc.tobytes()


def image_inference_handler(
    payload: Dict[str, Any],
    binary_payload: Optional[bytes] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Real Computer Vision Workload: YOLO Object Detection + OpenCV CIELAB Colour Analysis.
    
    Processes genuine binary images, runs Ultralytics YOLO inference, extracts dominant color
    clusters via OpenCV K-means in CIELAB, computes per-object color estimations, and generates
    an annotated image artifact.
    """
    start_total = time.perf_counter()
    model_name = payload.get("model", "yolov8n")
    conf_threshold = float(payload.get("confidence_threshold", payload.get("conf", 0.25)))
    palette_size = int(payload.get("palette_size", payload.get("num_colors", 8)))

    # Legacy synthetic tensor handling if no binary payload is provided
    if not binary_payload:
        batch_size = int(payload.get("batch_size", 1))
        image_dim = int(payload.get("image_dim", 640))
        use_gpu = payload.get("use_gpu", False)
        arr = np.zeros([batch_size, 16, image_dim, image_dim], dtype=np.float32)
        elapsed = round((time.perf_counter() - start_total) * 1000.0, 2)
        return {
            "model": model_name,
            "backend": "numpy-cpu",
            "input_dim": [batch_size, 3, image_dim, image_dim],
            "output_shape": list(arr.shape),
            "detections": [],
            "dominant_colors": [],
            "inference_latency_ms": elapsed,
            "inference_time_ms": elapsed,
        }

    # 1. Decode & Validate Image
    t_prep_start = time.perf_counter()
    nparr = np.frombuffer(binary_payload, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid or corrupted binary image payload: cv2.imdecode failed")

    h, w = img.shape[:2]
    prep_ms = round((time.perf_counter() - t_prep_start) * 1000.0, 2)

    # 2. YOLO Object Detection
    t_infer_start = time.perf_counter()
    from taskmesh.node.model_provisioner import get_model_provisioner
    node_id_hint = payload.get("assigned_node_id") or payload.get("node_id") or kwargs.get("node_id")
    cache_dir = None
    if node_id_hint:
        node_spec_dir = os.path.join(os.path.expanduser("~"), ".taskmesh", node_id_hint, "models")
        if os.path.exists(node_spec_dir):
            cache_dir = node_spec_dir
    provisioner = get_model_provisioner(cache_dir=cache_dir)
    ready, yolo_model, model_info = provisioner.verify_and_load(model_name)
    if not ready or yolo_model is None:
        raise RuntimeError(
            f"Cannot execute YOLO inference: model '{model_name}' could not be loaded ({model_info.get('error')})"
        )

    backend = model_info.get("backend", "cpu")
    model_version = model_info.get("version", "8.4.33")

    yolo_results = yolo_model(img, conf=conf_threshold, verbose=False)
    detections: List[Dict[str, Any]] = []

    for r in yolo_results:
        for box in r.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = r.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0].item())
            coords = [round(float(c), 1) for c in box.xyxy[0].tolist()]
            detections.append({
                "class": cls_name,
                "class_id": cls_id,
                "confidence": round(conf, 4),
                "bbox": coords,
            })
    infer_ms = round((time.perf_counter() - t_infer_start) * 1000.0, 2)

    # 3. Dominant Colour Extraction (OpenCV CIELAB K-Means)
    t_color_start = time.perf_counter()
    dominant_colors, _ = extract_dominant_colors(img, k=palette_size)

    # 4. Per-Object Colour Estimation
    for d in detections:
        col = estimate_object_color(img, d["bbox"])
        d["object_color"] = col
        d["dominant_color"] = col

    color_ms = round((time.perf_counter() - t_color_start) * 1000.0, 2)

    # 5. Generate Annotated Image
    t_ann_start = time.perf_counter()
    annotated_bytes = generate_annotated_image(img, detections, dominant_colors)
    ann_ms = round((time.perf_counter() - t_ann_start) * 1000.0, 2)

    total_execution_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

    task_id = payload.get("task_id", f"task_{hashlib.sha256(binary_payload).hexdigest()[:12]}")
    annotated_artifact_id = f"art_out_{task_id}"

    return {
        "model": {
            "name": model_name,
            "version": model_version,
            "backend": backend,
            "weights_path": model_info.get("weights_path"),
            "cache_dir": provisioner.cache_dir,
        },
        "image_dimensions": [w, h],
        "detections_count": len(detections),
        "detections": detections,
        "dominant_colors": dominant_colors,
        "annotated_image_artifact_id": annotated_artifact_id,
        "input_checksum": hashlib.sha256(binary_payload).hexdigest(),
        "timings": {
            "preprocessing_ms": prep_ms,
            "inference_ms": infer_ms,
            "color_extraction_ms": color_ms,
            "annotation_ms": ann_ms,
            "total_execution_ms": total_execution_ms,
        },
        # Internal byte payload passed back to worker node for artifact storage
        "_annotated_image_bytes": annotated_bytes,
        "inference_latency_ms": infer_ms,
        "inference_time_ms": infer_ms,
        "execution_time_seconds": round(total_execution_ms / 1000.0, 4),
    }
