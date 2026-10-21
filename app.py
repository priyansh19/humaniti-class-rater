"""Gradio UI: upload an MP4 and/or a VTT/TXT transcript -> Poor/Average/Good/Excellent with evidence."""
import json
import os

import tempfile

import gradio as gr
import requests

from api.rate import fetch as fetch_text, _check_url

from classq.llm import enabled as llm_enabled
from classq.pipeline import THEME_TEXT, assess, features_from


def _download_video(url, max_bytes=1_500_000_000):
    _check_url(url)
    fd, path = tempfile.mkstemp(suffix=".mp4", dir=os.environ.get("TMPDIR"))
    n = 0
    with requests.get(url, stream=True, timeout=30, allow_redirects=False) as r, os.fdopen(fd, "wb") as out:
        r.raise_for_status()
        for c in r.iter_content(1 << 20):
            n += len(c)
            if n > max_bytes:
                raise ValueError("Video too large")
            out.write(c)
    return path


def run(video, transcript, use_llm, whisper_model, link=""):
    tmp_video = None
    if link and link.strip():
        link = link.strip()
        try:
            if link.lower().split("?")[0].endswith((".mp4", ".mov", ".mkv", ".webm")):
                video = tmp_video = _download_video(link)
            else:
                ttxt_link = fetch_text(link)
                fd, transcript = tempfile.mkstemp(suffix=".txt")
                with os.fdopen(fd, "w") as fh:
                    fh.write(ttxt_link)
        except Exception as e:
            return f"Could not fetch link: {e}", "", "{}"
    try:
        return _run(video, transcript, use_llm, whisper_model)
    finally:
        if tmp_video and os.path.exists(tmp_video):
            os.remove(tmp_video)


def _run(video, transcript, use_llm, whisper_model):
    if not video and not transcript:
        return "Please upload a recording (MP4) and/or a transcript (VTT/TXT).", "", "{}"
    ttxt = open(transcript, encoding="utf-8", errors="ignore").read() if transcript else None
    f = features_from(video=video, transcript_text=ttxt, whisper_model=whisper_model)
    r = assess(f, use_llm=use_llm, multimodal=bool(video))
    md = [f"## Rating: **{r['label']}**", f"_Source: {r['source']}; local rubric score {r['local_score']:.2f} → {r['local_label']}_"]
    if f.get("asr"):
        md.append("_Transcript produced locally with faster-whisper (no speaker labels → student-level features are weaker)._")
    if "llm" in r:
        L = r["llm"]
        md += [f"**Summary:** {L.get('summary','')}", "### Strengths"] + [f"- {s}" for s in L["strengths"]]
        md += ["### Improvements"] + [f"- {s}" for s in L["improvements"]]
    if r.get("llm_error"):
        md.append(f"> LLM unavailable ({r['llm_error']}); showing the local rubric assessment.")
    md += ["### Evidence from the recording"] + [f"- {o}" for o in r["observations"]]
    md += ["### Rubric themes (0-1)"] + [f"- {THEME_TEXT[k][0]}: **{v:.2f}** ({THEME_TEXT[k][1]})" for k, v in r["themes"].items()]
    ev = "\n".join(f.get("evidence", [])[:40])
    feats = {k: f.get(k) for k in ("text", "frames", "audio")}
    return "\n".join(md), ev, json.dumps(feats, indent=1)


with gr.Blocks(title="8x8 Class Quality Assessor") as demo:
    gr.Markdown("# 8x8 Class Quality Assessor\nUpload a class recording and/or its transcript. Video and audio are processed **locally** "
                "(ffmpeg, OpenCV, faster-whisper). Only anonymised transcript snippets and numeric features go to the LLM. Uploads are not stored.")
    with gr.Row():
        v = gr.File(label="Class recording (MP4)", file_types=[".mp4", ".mkv", ".mov", ".webm"], type="filepath")
        t = gr.File(label="Transcript (VTT/TXT, optional; skips ASR)", file_types=[".vtt", ".txt"], type="filepath")
    with gr.Row():
        use_llm = gr.Checkbox(value=llm_enabled(), label="Use LLM judge (Gemini/OpenAI/Anthropic, text-only)")
        link = gr.Textbox(label="...or a public link to an MP4 or a VTT/TXT transcript")
        wm = gr.Dropdown(["tiny", "base", "small"], value="base", label="Whisper model (CPU)")
    btn = gr.Button("Assess", variant="primary")
    out = gr.Markdown()
    with gr.Accordion("Tagged transcript lines (anonymised)", open=False):
        ev = gr.Textbox(lines=15)
    with gr.Accordion("Raw features", open=False):
        js = gr.Code(language="json")
    btn.click(run, [v, t, use_llm, wm, link], [out, ev, js])

if __name__ == "__main__":
    demo.queue(max_size=8).launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)),
                share=os.environ.get("GRADIO_SHARE") == "1", max_file_size="2gb")
