"""Compute and cache features for the local dataset (cache is git-ignored)."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from classq import transcript as T, media as M

ROOT = os.environ.get("DATA_DIR", "../dataset/class recordings")
CACHE = "cache"; os.makedirs(CACHE, exist_ok=True)
FOLDER2LABEL = {"excellent": "Excellent", "good": "Good", "average": "Average",
                "weak": "Poor", "quality issue": "Poor", "demo": None}
rows = []
for folder, label in FOLDER2LABEL.items():
    mp4s = sorted(glob.glob(f"{ROOT}/{folder}/*.mp4")); vtts = sorted(glob.glob(f"{ROOT}/{folder}/*.vtt"))
    for mp4 in mp4s:
        code = os.path.basename(mp4).split()[0] + ("_" + os.path.basename(mp4).split()[1] if folder == "demo" else "")
        date = mp4.split(" - ")[-1].replace(".mp4", "") if " - " in mp4 else ""
        if folder == "demo":
            lang = "english" if "english" in mp4.lower() else "malayalam"
            vtt = next(v for v in vtts if lang in v.lower())
        else:
          vtt = next((v for v in vtts if os.path.basename(v).split()[0] == os.path.basename(mp4).split()[0] and (folder != "demo" or os.path.basename(mp4).split()[-1][:4].lower() in v.lower())), None)
        cid = f"{folder.replace(' ','_')}_{code}_{date}".strip("_")
        out = f"{CACHE}/{cid}.json"
        d = M.cache_json(out) or {}
        d.update(id=cid, folder=folder, label=label)
        cues = T.parse_vtt(open(vtt, encoding="utf-8").read())
        d["text"] = T.features(cues)
        d["evidence"] = T.evidence(cues)
        d["excerpt"] = T.excerpt(cues)
        if "frames" not in d and "--no-media" not in sys.argv:
            d["frames"] = M.frame_features(mp4); d["audio"] = M.audio_features(mp4)
        M.cache_json(out, d); print(cid, flush=True)
