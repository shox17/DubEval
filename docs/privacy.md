# Privacy

DubEval runs on your own computer. Here is exactly what stays there and what leaves it.

## Stays on your computer
- The videos you evaluate, once downloaded, and all the audio and video analysis: speech recognition, loudness,
  timing, voice quality and similarity, lip movement.
- Reports, the evaluation history (`data/history.jsonl`) and reviewer votes (`data/feedback.jsonl`), under `data/` or
  the folder set by `DUBEVAL_DATA`.
- Your API keys, in your local `.env` file.

DubEval sends no usage statistics or crash reports. It connects the way your browser does: through this computer's
proxy, trusting the certificates this computer trusts (`dubeval/network.py`; `DUBEVAL_SYSTEM_NETWORK=0` turns this
off).

## Leaves your computer
| What | Where to | When |
|---|---|---|
| The share link's id | Perso (`api.perso.ai`), and the media host (`portal-media.perso.ai`) to download the videos | When you evaluate a Perso share link |
| Links you pass as the original or the dub | That link's host (for pages such as YouTube, through yt-dlp) | When you use a link |
| **The lines of both sides** (text only, never audio or video), and subtitle text when you give subtitles | Anthropic Claude or Google Gemini | Only when the translation check uses a cloud judge: a key is set and `--judge` isn't `ollama` or `off` |
| Requests for models | Hugging Face (speech recognition, speaker model) and, with the optional OpenAI Whisper, OpenAI's model servers | Once, the first time a model is needed |
| A check for a newer version (no data about you or your videos) | GitHub (this repository's Releases) | When the desktop app starts |

To keep everything local, use the local judge (`--judge ollama`, with Ollama and `qwen3:8b` installed) or none
(`--judge off`): the offline meaning similarity runs on your computer either way.
