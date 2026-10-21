"""End-to-end assessment."""
from . import media as M, transcript as T
from .rubric import fit_cuts, overall, theme_scores, to_label
from . import llm

# Cut-points fitted on all 10 labelled classes (see EVAL.md); refreshed by scripts/eval.py.
import json as _j, os as _o
_cp = _o.path.join(_o.path.dirname(__file__), "cuts.json")
CUTS = _j.load(open(_cp)) if _o.path.exists(_cp) else [0.35, 0.5, 0.65]

THEME_TEXT = {
    "intro_rapport": ("Rapport/intro", "greetings and warm-up in first 5 min; new-joiner introductions"),
    "individual_engagement": ("Individual engagement", "students named, questions asked, spread of student turns"),
    "energy_pleasantness": ("Energy/pleasantness", "praise rate, share of student talk"),
    "homework_conclusion": ("Homework & wrap-up", "homework mentions and closing in last 5 min"),
    "visual_professionalism": ("Camera/face/lighting", "tutor face visible, brightness, camera-off streaks"),
    "av_quality": ("AV quality", "student complaints about audio/video, silence"),
}


def local_observations(f, themes):
    t, fr = f.get("text", {}), f.get("frames", {})
    obs = []
    obs.append(f"Greeting/rapport cues in first 5 min: {t.get('intro_hits_first5')}; new-joiner intro prompts: {t.get('newjoiner_intro_hits')}.")
    obs.append(f"{t.get('n_students_speaking')} students spoke; tutor addressed {t.get('students_addressed_by_name')} by name; "
               f"{t.get('teacher_questions_per_min')} tutor questions/min; tutor talk share {int(100*t.get('teacher_talk_ratio',0))}%.")
    obs.append(f"Homework mentioned {t.get('homework_mentions')}x ({t.get('homework_in_last10')} in last 10 min); wrap-up cues in last 5 min: {t.get('wrapup_hits_last5')}.")
    obs.append(f"Praise words: {t.get('praise_per_min')}/min. AV complaints ('can't hear', 'not visible', ...): {t.get('av_complaints')}.")
    if fr:
        obs.append(f"Face visible in {int(100*fr['face_present_frac'])}% of sampled frames (longest no-face stretch {fr['no_face_streak_max_min']} min); "
                   f"mean brightness {fr['mean_brightness']}/255.")
    weak = sorted(themes, key=themes.get)[:2]
    obs.append("Weakest areas: " + ", ".join(THEME_TEXT[w][0] for w in weak) + ".")
    return obs


def features_from(video=None, transcript_text=None, frame_every_s=20, whisper_model="base"):
    f = {}
    if not transcript_text and video:
        transcript_text = M.transcribe(video, model_size=whisper_model)
        f["asr"] = True
    cues = T.parse_any(transcript_text or "")
    f["text"] = T.features(cues)
    f["evidence"] = T.evidence(cues)
    f["excerpt"] = T.excerpt(cues) if cues else ""
    if video:
        f["frames"] = M.frame_features(video, frame_every_s)
        f["audio"] = M.audio_features(video)
    return f


def assess(f, use_llm=True, multimodal=True, cuts=None):
    themes = theme_scores(f, multimodal=multimodal)
    sc = overall(themes)
    res = {"local_score": sc, "local_label": to_label(sc, cuts or CUTS), "themes": themes,
           "observations": local_observations(f, themes)}
    res["label"] = res["local_label"]; res["source"] = "local rubric scorer"
    if use_llm:
        try:
            out = llm.call(llm.build_prompt(f if multimodal else {**f, "frames": None, "audio": None}, themes))
            res.update(llm=out, label=out["label"], source="LLM (OpenRouter, text-only)")
        except Exception as e:
            res["llm_error"] = str(e)
    return res
