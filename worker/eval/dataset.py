"""Local dataset index. Labels follow SPEC A6 (weak and quality issue -> Poor). Ids are folder + batch code only."""
from __future__ import annotations

import glob
import os

FOLDER_LABEL = {"excellent": "Excellent", "good": "Good", "average": "Average", "weak": "Poor",
                "quality issue": "Poor", "demo": None}


def items(root: str) -> list[dict]:
    out = []
    for folder, label in FOLDER_LABEL.items():
        vids = sorted(glob.glob(os.path.join(root, folder, "*.mp4")))
        vtts = sorted(glob.glob(os.path.join(root, folder, "*.vtt")))
        for v in vids:
            base = os.path.basename(v)
            if folder == "demo":
                lang = "english" if "english" in base.lower() else "malayalam"
                vtt = next(t for t in vtts if lang in t.lower())
                cid = f"demo-{lang}"
            else:
                code = base.split()[0]
                vtt = next(t for t in vtts if os.path.basename(t).split()[0] == code)
                date = base.rsplit(" - ", 1)[-1].replace(".mp4", "") if " - " in base else ""
                cid = f"{folder.replace(' ', '_')}-{code}-{date}"
            out.append({"id": cid, "folder": folder, "label": label, "video": v, "vtt": vtt})
    return out
