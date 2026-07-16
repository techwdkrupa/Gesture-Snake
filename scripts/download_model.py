"""
One-time setup: downloads Google's pretrained hand-landmark model (~8 MB)
into models/hand_landmarker.task.

MediaPipe's Tasks API ships the runtime but not the model weights, so this
file has to be fetched once before the first run. Re-running this script is
safe -- it skips the download if the file already exists.
"""

import os
import sys
import urllib.request

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(HERE), "models", "hand_landmarker.task")


def main():
    os.makedirs(os.path.dirname(DEST), exist_ok=True)

    if os.path.exists(DEST) and os.path.getsize(DEST) > 0:
        print(f"Model already present at {DEST} -- nothing to do.")
        return

    print(f"Downloading hand landmark model from:\n  {MODEL_URL}")
    try:
        urllib.request.urlretrieve(MODEL_URL, DEST)
    except Exception as exc:  # noqa: BLE001 - want to surface any network error clearly
        print(f"Download failed: {exc}", file=sys.stderr)
        print(f"You can also download it manually and save it to:\n  {DEST}", file=sys.stderr)
        sys.exit(1)

    size_kb = os.path.getsize(DEST) / 1024
    print(f"Saved model to {DEST} ({size_kb:.0f} KB). You're ready to run `python main.py`.")


if __name__ == "__main__":
    main()
