# Privacy

DubEval runs on your own computer. Here is exactly what stays there and what leaves it.

## Stays on your computer
- The videos you evaluate, once downloaded, and all the audio and video analysis: speech recognition, loudness,
  timing, voice quality and similarity, lip sync.
- Reports, the evaluation history (`data/history.jsonl`) and reviewer votes (`data/feedback.jsonl`), under `data/` or the
  folder set by `DUBEVAL_DATA`.
- Your API keys, in your local `.env` file.
- Your answer about usage stats (`data/usage_stats.json`).

DubEval sends usage stats only if you say yes (the table below lists them), and no other usage data or crash reports. The
command line and the REST API never send them. It connects the way your browser does: through this computer's
proxy, trusting the certificates this computer trusts (`dubeval/network.py`; `DUBEVAL_SYSTEM_NETWORK=0` turns this
off).

## Leaves your computer
| What | Where to | When |
|---|---|---|
| The share link's id | Perso (`api.perso.ai`), and the media host (`portal-media.perso.ai`) to download the videos | When you evaluate a Perso share link |
| Links you pass as the original or the dub | That link's host (for pages such as YouTube, through yt-dlp) | When you use a link |
| **The lines of both sides** (text only, never audio or video), the video's title, and subtitle text when you give subtitles | Anthropic Claude, Google Gemini or OpenAI ChatGPT (the first one whose key is set) | Only when the translation check uses a cloud judge: a key is set and `--judge` isn't `ollama` or `off` |
| Requests for models | Hugging Face (speech recognition, speaker model, and the downloads you choose in Settings → Models, such as the lip-sync model) and, with the optional OpenAI Whisper, OpenAI's model servers | Once, the first time a model is needed or when you choose a download |
| Usage stats: events (app opened; new evaluation opened, dub added, original added, result opened, by name only and never which video; evaluation started, finished, failed or stopped; feature used), the mode, how many dubs, the step that failed and the kind of error (such as `MemoryError`, never its message), the verdict, the language codes, the kind of dub, a time rounded to 10 seconds, the app version, your system (such as Windows 11) and a random number replaced every week, which counts active apps and can't follow one across weeks. Never a video, audio, a transcript, a title, a file name, a link, an API key or a measured value | dubeval.com, hosted by Cloudflare. It stores the day, not the time, and no IP address; an address is used only to limit repeated requests | Only if you say yes to the question at launch or turn it on in Settings → Privacy. Turn it off there anytime; `DUBEVAL_USAGE_STATS=0` turns the feature off completely |
| A check for a newer version (no data about you or your videos) | GitHub (this repository's Releases) | When the desktop app starts |

To keep everything local, use the local judge (`--judge ollama`, with Ollama and `qwen3:8b` installed) or none
(`--judge off`): the offline meaning similarity runs on your computer either way.
