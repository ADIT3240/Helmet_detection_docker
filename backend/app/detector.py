import cv2
import numpy as np
from ultralytics import YOLO
import os

# Models loaded once at startup — not per request
_BASE = os.path.dirname(os.path.dirname(__file__))
yolo_model = YOLO(os.path.join(_BASE, "models", "yolov8n.pt"))
helmet_model = YOLO(os.path.join(_BASE, "models", "best_helmet.pt"))

PERSON_CLASS = 0
MOTORCYCLE_CLASS = 3
CONF_THRESHOLD = 0.4
IOU_THRESHOLD = 0.45
HELMET_CONF_THRESHOLD = 0.3
HELMET_IOU_THRESHOLD = 0.45
MAX_DISTANCE = 100
MIN_OVERLAP_RATIO = 0.1

COLORS = {
    "person": (0, 255, 255),
    "with_helmet": (0, 255, 0),
    "no_helmet": (0, 0, 255),
    "motorcycle": (255, 0, 255),
}


def _iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    if x2 <= x1 or y2 <= y1:
        return 0
    inter = (x2 - x1) * (y2 - y1)
    a1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    a2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return inter / (a1 + a2 - inter) if (a1 + a2 - inter) > 0 else 0


def _distance(box1, box2):
    cx1, cy1 = (box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2
    cx2, cy2 = (box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2
    return np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)


def _merge(box1, box2):
    return (min(box1[0], box2[0]), min(box1[1], box2[1]),
            max(box1[2], box2[2]), max(box1[3], box2[3]))


def _pair_persons_and_bikes(persons, motorcycles):
    pairs, used_p, used_m = [], set(), set()
    for i, p in enumerate(persons):
        if i in used_p:
            continue
        for j, m in enumerate(motorcycles):
            if j in used_m:
                continue
            if _iou(p["box"], m["box"]) > MIN_OVERLAP_RATIO or _distance(p["box"], m["box"]) < MAX_DISTANCE:
                pairs.append({
                    "person": p,
                    "motorcycle": m,
                    "merged_box": _merge(p["box"], m["box"]),
                    "avg_conf": (p["conf"] + m["conf"]) / 2,
                })
                used_p.add(i)
                used_m.add(j)
                break
    return pairs, used_p, used_m


def _has_helmet(crop):
    results = helmet_model(crop, verbose=False, conf=HELMET_CONF_THRESHOLD, iou=HELMET_IOU_THRESHOLD)
    max_conf = 0
    found = False
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            if int(box.cls[0]) == 1:
                c = float(box.conf[0])
                if c > max_conf:
                    max_conf = c
                    found = True
    return found, max_conf


def _draw_label(frame, text, x1, y1, color):
    size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cv2.rectangle(frame, (x1, y1 - size[1] - 10), (x1 + size[0], y1), color, -1)
    cv2.putText(frame, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)


def run_detection(input_path: str, output_path: str, progress_callback=None) -> dict:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    stats = {
        "total_frames": 0,
        "standalone_persons": 0,
        "standalone_motorcycles": 0,
        "total_riders": 0,
        "with_helmet": 0,
        "without_helmet": 0,
        "compliance_rate": None,
    }

    frame_idx = 0
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        results = yolo_model(frame, verbose=False, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD)
        persons, motorcycles = [], []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                det = {"box": (x1, y1, x2, y2), "conf": conf}
                if cls == PERSON_CLASS:
                    persons.append(det)
                elif cls == MOTORCYCLE_CLASS:
                    motorcycles.append(det)

        pairs, used_p, used_m = _pair_persons_and_bikes(persons, motorcycles)

        for pair in pairs:
            x1, y1, x2, y2 = pair["merged_box"]
            pad = 20
            crop = frame[max(0, y1 - pad):min(height, y2 + pad),
                         max(0, x1 - pad):min(width, x2 + pad)]
            if crop.size == 0:
                continue
            helmet, h_conf = _has_helmet(crop)
            if helmet:
                color = COLORS["with_helmet"]
                label = f"Rider WITH Helmet ({pair['avg_conf']:.2f}, {h_conf:.2f})"
                stats["with_helmet"] += 1
            else:
                color = COLORS["no_helmet"]
                label = f"Rider NO Helmet ({pair['avg_conf']:.2f})"
                stats["without_helmet"] += 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            _draw_label(frame, label, x1, y1, color)
            stats["total_riders"] += 1

        for i, p in enumerate(persons):
            if i not in used_p:
                x1, y1, x2, y2 = p["box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), COLORS["person"], 2)
                _draw_label(frame, f"Person ({p['conf']:.2f})", x1, y1, COLORS["person"])
                stats["standalone_persons"] += 1

        for j, m in enumerate(motorcycles):
            if j not in used_m:
                x1, y1, x2, y2 = m["box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), COLORS["motorcycle"], 2)
                _draw_label(frame, f"Motorcycle ({m['conf']:.2f})", x1, y1, COLORS["motorcycle"])
                stats["standalone_motorcycles"] += 1

        cv2.putText(frame, f"Frame: {frame_idx}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Riders: {stats['total_riders']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"With Helmet: {stats['with_helmet']}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"No Helmet: {stats['without_helmet']}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        out.write(frame)

        if progress_callback and total_frames > 0:
            progress_callback(int(frame_idx / total_frames * 100))

    cap.release()
    out.release()

    stats["total_frames"] = frame_idx
    if stats["total_riders"] > 0:
        stats["compliance_rate"] = round(stats["with_helmet"] / stats["total_riders"] * 100, 1)

    return stats
