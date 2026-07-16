"""
hand_tracker.py
----------------
Wraps MediaPipe's HandLandmarker (the current "Tasks" API) to give the rest
of the app a simple, clean interface:
  - fingertip position (index finger) -> used to steer the snake
  - pinch detection (thumb + index)   -> used as a "boost" input
  - open-palm detection               -> used to pause / restart the game

Keeping all the MediaPipe-specific code in one place means the game logic
in game.py never has to know anything about landmarks or CV internals.

Note: this uses mediapipe.tasks (HandLandmarker) rather than the older
mp.solutions.hands API. The legacy `solutions` API has been removed from
recent MediaPipe wheels on some platforms/Python versions, so Tasks is the
more reliable choice going forward. It needs a small model file the first
time you run the app -- see `scripts/download_model.py` / the README.
"""

import math
import os
from dataclasses import dataclass
from typing import Optional, Tuple

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models",
    "hand_landmarker.task",
)
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


@dataclass
class HandState:
    """A single, simplified snapshot of what the hand is doing this frame."""
    found: bool = False
    fingertip: Optional[Tuple[int, int]] = None   # index fingertip (x, y) in pixels
    is_pinching: bool = False                      # thumb tip close to index tip
    is_open_palm: bool = False                      # all fingers extended


class HandTracker:
    # Landmark indices from the MediaPipe Hand Landmark model (21 points)
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    INDEX_PIP = 6
    MIDDLE_TIP = 12
    MIDDLE_PIP = 10
    RING_TIP = 16
    RING_PIP = 14
    PINKY_TIP = 20
    PINKY_PIP = 18

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        max_hands: int = 1,
        detection_confidence: float = 0.6,
        tracking_confidence: float = 0.5,
        pinch_threshold: float = 0.06,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Hand landmark model not found at '{model_path}'.\n"
                f"Run `python scripts/download_model.py` first (needs internet, "
                f"one-time download of ~8MB), then re-run the game.\n"
                f"Manual download URL: {MODEL_URL}"
            )

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._pinch_threshold = pinch_threshold
        self._timestamp_ms = 0

    def process(self, frame_bgr) -> HandState:
        """Run detection on a BGR frame (numpy array) and return a HandState."""
        h, w, _ = frame_bgr.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=_bgr_to_rgb(frame_bgr))

        # VIDEO mode requires strictly increasing timestamps.
        self._timestamp_ms += 33  # ~30fps step; exact value doesn't matter, monotonic does
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        if not result.hand_landmarks:
            return HandState(found=False)

        landmarks = result.hand_landmarks[0]

        fingertip_px = (
            int(landmarks[self.INDEX_TIP].x * w),
            int(landmarks[self.INDEX_TIP].y * h),
        )

        pinch_dist = self._distance(landmarks[self.THUMB_TIP], landmarks[self.INDEX_TIP])
        is_pinching = pinch_dist < self._pinch_threshold
        is_open_palm = self._is_open_palm(landmarks)

        return HandState(
            found=True,
            fingertip=fingertip_px,
            is_pinching=is_pinching,
            is_open_palm=is_open_palm,
        )

    def close(self) -> None:
        self._landmarker.close()

    # -- internal helpers ----------------------------------------------

    @staticmethod
    def _distance(a, b) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def _is_open_palm(self, lm) -> bool:
        """A quick heuristic: an open palm has every fingertip further from
        the wrist than that finger's middle joint (PIP)."""
        wrist = lm[self.WRIST]

        def extended(tip_idx, pip_idx):
            tip_dist = math.hypot(lm[tip_idx].x - wrist.x, lm[tip_idx].y - wrist.y)
            pip_dist = math.hypot(lm[pip_idx].x - wrist.x, lm[pip_idx].y - wrist.y)
            return tip_dist > pip_dist

        fingers = [
            (self.INDEX_TIP, self.INDEX_PIP),
            (self.MIDDLE_TIP, self.MIDDLE_PIP),
            (self.RING_TIP, self.RING_PIP),
            (self.PINKY_TIP, self.PINKY_PIP),
        ]
        return all(extended(tip, pip) for tip, pip in fingers)


def _bgr_to_rgb(frame_bgr):
    # Local import keeps cv2 usage isolated to this one conversion.
    import cv2
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
