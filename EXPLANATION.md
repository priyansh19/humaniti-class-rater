# Approach (≤300 words)

**Approach.** I used the organiser's tutor feedback as the rubric. It covers rapport and intro (including new joiners), questioning each child individually, energy, homework and wrap-up, camera/face/lighting, and AV problems. The app measures proxies for these themes, and all of it runs locally: ffmpeg handles audio and frames, OpenCV checks face and brightness, and faster-whisper or the Zoom VTT supplies the transcript. The proxies include student turns per minute, questions per minute, early greetings, homework mentions, dead air, praise rate and "can't hear you" complaints. A transparent rubric scorer turns them into theme scores and a label. An optional LLM judge (Gemini, OpenAI or Anthropic, the client-approved APIs) receives only anonymised transcript snippets and numbers, never video, and writes timestamped reasons. This protects children's privacy.

**Labels.** The dataset has five folders, but the output has four classes. I mapped both *weak* (pedagogy gaps: no rapport, no intro for new joiners) and *quality issue* (no background, face not visible, AV complaints) to **Poor**. Both received the most negative feedback, and the app's reasons still say which kind of failure it was.

**What worked.** Interaction density was the strongest signal: student turns per minute and the absence of long silences separated both Excellent classes. The anonymised evidence lines make the explanations specific.

**What failed.** Haar face detection is unreliable on Zoom gallery layouts. Leave-one-out accuracy is 50% exact and 80% within one class, against a 40% majority baseline. No approved LLM key was available, so the LLM judge is not yet evaluated.

**Limitations.** There are only 10 labelled classes, and I tuned the weights once after seeing them, so some optimism is built in. The cues are English-centric, Whisper has no diarisation, and CPU transcription of a long class takes minutes.
