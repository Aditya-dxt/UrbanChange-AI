"""
Download weights for SatQuery Siamese U-Net model from Google Drive or local cache.
Google Drive File ID: 1vaNaT8FkHY-ysYwJWhyoEVOw6A7_vPq-
File size: ~285 MB
"""
import os
import sys
import shutil
from pathlib import Path

GOOGLE_DRIVE_FILE_ID = "1vaNaT8FkHY-ysYwJWhyoEVOw6A7_vPq-"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "weights"
DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "best_siamese_model.pth"
MIN_FILE_SIZE = 250 * 1024 * 1024  # 250 MB


def ensure_weights(output_path: Path = DEFAULT_OUTPUT_FILE) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and output_path.stat().st_size >= MIN_FILE_SIZE:
        print(f"[weights] Model weights already present: {output_path} ({output_path.stat().st_size / (1024*1024):.1f} MB)")
        return output_path

    print(f"[weights] Checking local fallback locations for {output_path.name}...")
    local_candidates = [
        Path.home() / ".gemini" / "antigravity" / "brain" / "22f1c17a-1f9d-4bfe-a417-d6c2b0981a34" / "scratch" / "Satquery-1.O" / "models" / "best_siamese_model.pth",
        Path.home() / "Desktop" / "Satquery-1.O" / "models" / "best_siamese_model.pth",
        Path.home() / "OneDrive" / "Desktop" / "Satquery-1.O" / "models" / "best_siamese_model.pth",
        Path("/models/best_siamese_model.pth"),
    ]

    for candidate in local_candidates:
        if candidate.exists() and candidate.stat().st_size >= MIN_FILE_SIZE:
            print(f"[weights] Found local weights at {candidate}. Copying to {output_path}...")
            shutil.copy2(candidate, output_path)
            print("[weights] Successfully copied local weights.")
            return output_path

    print(f"[weights] Downloading from Google Drive ID: {GOOGLE_DRIVE_FILE_ID}...")
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, str(output_path), quiet=False)
    except Exception as exc:
        print(f"[weights] gdown failed or not available ({exc}). Falling back to requests...")
        import requests

        url = "https://docs.google.com/uc?export=download"
        session = requests.Session()
        response = session.get(url, params={"id": GOOGLE_DRIVE_FILE_ID}, stream=True)
        token = None
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                token = value
                break

        params = {"id": GOOGLE_DRIVE_FILE_ID}
        if token:
            params["confirm"] = token

        response = session.get(url, params=params, stream=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

    if not output_path.exists() or output_path.stat().st_size < MIN_FILE_SIZE:
        actual_size = output_path.stat().st_size if output_path.exists() else 0
        raise RuntimeError(
            f"Failed to obtain complete weights file. Size={actual_size} bytes (expected >= {MIN_FILE_SIZE} bytes)."
        )

    print(f"[weights] Successfully acquired weights at {output_path} ({output_path.stat().st_size / (1024*1024):.1f} MB)")
    return output_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT_FILE
    ensure_weights(Path(target))
