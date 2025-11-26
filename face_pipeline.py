import cv2
import torch
import numpy as np
import time

# Load DNN face detector (instead of Haar)
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
modelFile = os.path.join(script_dir, "res10_300x300_ssd_iter_140000.caffemodel")
configFile = os.path.join(script_dir, "deploy.prototxt")
net = cv2.dnn.readNetFromCaffe(configFile, modelFile)

def device_summary():
    return {
        "torch_installed": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }

def detect_faces_dnn(frame, conf_threshold=0.4):
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()
    faces = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            w_box, h_box = x2 - x1, y2 - y1
            faces.append((x1, y1, w_box, h_box))
    return faces

class Track:
    def __init__(self, track_id, box):
        self.id = track_id
        self.box = box
        self.missed = 0
        self.last_update = time.time()

class TrackerDB:
    def __init__(self, iou_thresh=0.3, max_missed=30):
        self.tracks = []
        self.next_id = 1
        self.iou_thresh = iou_thresh
        self.max_missed = max_missed

    def update(self, detections):
        assigned_det = set()
        for tr in self.tracks:
            best_iou, best_j = 0.0, -1
            for j, det in enumerate(detections):
                if j in assigned_det:
                    continue
                i = iou(tr.box, det)
                if i > best_iou:
                    best_iou, best_j = i, j
            if best_iou >= self.iou_thresh and best_j != -1:
                tr.box = detections[best_j]
                tr.missed = 0
                tr.last_update = time.time()
                assigned_det.add(best_j)
            else:
                tr.missed += 1

        for j, det in enumerate(detections):
            if j not in assigned_det:
                self.tracks.append(Track(self.next_id, det))
                self.next_id += 1

        self.tracks = [t for t in self.tracks if t.missed <= self.max_missed]
        return self.tracks

def iou(b1, b2):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa, ya = max(x1, x2), max(y1, y2)
    xb, yb = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    inter = max(0, xb - xa) * max(0, yb - ya)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0

def process_frame(frame, trackerdb):
    faces = detect_faces_dnn(frame)   # use DNN instead of Haar
    tracks = trackerdb.update(faces)

    outputs = []
    for tr in tracks:
        x, y, w, h = tr.box
        outputs.append({
            "box": (x, y, w, h),
            "id": f"Student_{tr.id}"
        })
    return outputs

def draw_overlays(frame, outputs):
    for person in outputs:
        (x, y, w, h) = person['box']
        color = (0, 255, 0)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame, f"{person['id']}",
                   (x, max(0, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame
