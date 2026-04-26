"""Face detection (YuNet) and recognition (SFace) engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from afracs import config

log = logging.getLogger(__name__)

_DETECT_W, _DETECT_H = 320, 320
_COSINE_THRESHOLD = config.RECOGNITION_THRESHOLD

_COLOR_GOLD   = (86, 179, 212)
_COLOR_GREEN  = (58, 127,  27)
_COLOR_RED    = (32,   0, 176)


@dataclass
class RecognitionResult:
    face_found: bool
    matched:    bool  = False
    faculty_id: int   | None = None
    name:       str   | None = None
    role:       str   | None = None
    cabinets:   list[str]    = None
    confidence: float        = 0.0
    bbox:       tuple | None = None

    def __post_init__(self):
        if self.cabinets is None:
            self.cabinets = []


def decode_known_faces(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        try:
            emb = np.frombuffer(row["encoding"], dtype=np.float32).reshape(1, 128)
            result.append({
                "id":       row["id"],
                "name":     row["name"],
                "position": row["position"],
                "department": row["department"],
                "cabinets": row.get("cabinets", []),
                "embedding": emb,
            })
        except Exception as exc:
            log.warning("Skipping faculty id=%s: bad encoding (%s)", row.get("id"), exc)
    return result


class FaceEngine:
    def __init__(self) -> None:
        det  = str(config.FACE_DETECTOR_MODEL)
        rec  = str(config.FACE_RECOGNIZER_MODEL)

        if not config.FACE_DETECTOR_MODEL.exists():
            raise FileNotFoundError(
                f"YuNet model not found: {det}\n"
                "Run: python -m afracs.download_models"
            )
        if not config.FACE_RECOGNIZER_MODEL.exists():
            raise FileNotFoundError(
                f"SFace model not found: {rec}\n"
                "Run: python -m afracs.download_models"
            )

        self._detector = cv2.FaceDetectorYN.create(
            det, "",
            (_DETECT_W, _DETECT_H),
            score_threshold=0.80,
            nms_threshold=0.30,
            top_k=5,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(rec, "")
        log.info("FaceEngine initialised (YuNet + SFace)")

    def process_frame(
        self,
        frame: np.ndarray,
        known_faces: list[dict],
    ) -> RecognitionResult:
        h, w = frame.shape[:2]
        self._detector.setInputSize((w, h))
        _, detections = self._detector.detect(frame)

        if detections is None or len(detections) == 0:
            return RecognitionResult(face_found=False)

        best_det = max(detections, key=lambda d: d[-1])
        x, y, fw, fh = (int(v) for v in best_det[:4])

        cv2.rectangle(frame, (x, y), (x + fw, y + fh), _COLOR_GOLD, 2)

        if not known_faces:
            cv2.putText(
                frame, "No faculty enrolled",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, _COLOR_RED, 2,
            )
            return RecognitionResult(face_found=True, bbox=(x, y, fw, fh))

        try:
            aligned = self._recognizer.alignCrop(frame, best_det)
        except Exception:
            return RecognitionResult(face_found=True, bbox=(x, y, fw, fh))

        query_feat = self._recognizer.feature(aligned)

        best_score  = -1.0
        best_person: dict | None = None
        for person in known_faces:
            score = float(self._recognizer.match(
                query_feat,
                person["embedding"],
                cv2.FaceRecognizerSF_FR_COSINE,
            ))
            if score > best_score:
                best_score  = score
                best_person = person

        matched = best_score >= _COSINE_THRESHOLD

        if matched and best_person:
            label = best_person["name"]
            color = _COLOR_GREEN
        else:
            label = f"Unknown  ({best_score:.2f})"
            color = _COLOR_RED

        cv2.putText(
            frame, label,
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
        )

        if matched and best_person:
            return RecognitionResult(
                face_found  = True,
                matched     = True,
                faculty_id  = best_person["id"],
                name        = best_person["name"],
                role        = f"{best_person['position']} · {best_person['department']}",
                cabinets    = best_person.get("cabinets", []),
                confidence  = best_score,
                bbox        = (x, y, fw, fh),
            )

        return RecognitionResult(
            face_found  = True,
            matched     = False,
            confidence  = best_score,
            bbox        = (x, y, fw, fh),
        )

    def encode_from_image(self, img: np.ndarray) -> bytes | None:
        h, w = img.shape[:2]
        self._detector.setInputSize((w, h))
        _, detections = self._detector.detect(img)
        if detections is None or len(detections) == 0:
            return None
        best_det = max(detections, key=lambda d: d[-1])
        try:
            aligned = self._recognizer.alignCrop(img, best_det)
        except Exception:
            return None
        feat = self._recognizer.feature(aligned)
        return feat.tobytes()
