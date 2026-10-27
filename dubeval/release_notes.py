"""What's new in each version, as the app's "What's new" card shows it: a few plain lines per language.

Add the new version's lines here (en, ko, pt, es) whenever TOOL_VERSION changes; tests check the current one exists.
"""

NOTES = {
    "0.1.1": {
        "en": ["Works on company networks: downloads and Perso links now use this computer's trusted certificates and "
               "proxy, as your browser does.",
               "When a network still blocks DubEval, the message says so and what to ask your IT team, instead of "
               "\"check your internet connection\"."],
        "ko": ["회사 네트워크에서도 작동합니다: 다운로드와 Perso 링크가 브라우저처럼 이 컴퓨터의 신뢰하는 인증서와 프록시를 "
               "사용합니다.",
               "네트워크가 여전히 DubEval을 막으면 \"인터넷 연결을 확인하세요\" 대신 그 사실과 IT 팀에 요청할 내용을 "
               "알려 줍니다."],
        "pt": ["Funciona em redes corporativas: downloads e links da Perso agora usam os certificados confiáveis e o "
               "proxy deste computador, como o navegador.",
               "Quando uma rede ainda bloqueia o DubEval, a mensagem diz isso e o que pedir à equipe de TI, em vez de "
               "\"verifique sua conexão\"."],
        "es": ["Funciona en redes corporativas: las descargas y los enlaces de Perso ahora usan los certificados de "
               "confianza y el proxy de este equipo, como el navegador.",
               "Cuando una red sigue bloqueando DubEval, el mensaje lo dice y qué pedirle a tu equipo de TI, en lugar "
               "de \"revisa tu conexión\"."],
    },
    "0.1.0": {
        "en": ["Evaluate a dub against its original: timing, voice, meaning and sound, with every problem on a timeline.",
               "Every evaluation is kept on the Evaluations screen, with a picture: open, rename or delete it; a page you've started filling in is kept as a draft.",
               "Compare up to 8 dubs of one video and get a recommendation with the reason.",
               "Paste YouTube, TikTok, Reels or Perso share links, or choose files on this computer.",
               "Offline meaning check, faster recognition on NVIDIA cards and a large speech model in Settings → Models.",
               "Translation check with Claude, Gemini or ChatGPT.",
               "Export the results as a report, a problem list, a summary or data."],
        "ko": ["원본과 비교해 더빙을 평가합니다: 타이밍, 목소리, 의미, 소리, 그리고 모든 문제를 타임라인에 표시합니다.",
               "모든 평가가 평가 목록 화면에 그림과 함께 남습니다. 열기, 이름 바꾸기, 삭제가 가능하고, 입력하다 만 화면은 초안으로 남습니다.",
               "한 영상의 더빙을 최대 8개까지 비교하고, 이유와 함께 추천을 받습니다.",
               "YouTube, TikTok, Reels, Perso 공유 링크를 붙여 넣거나 이 컴퓨터의 파일을 고르세요.",
               "설정 → 모델에서 오프라인 의미 검사, NVIDIA 그래픽 카드 가속, 큰 음성 인식 모델을 받을 수 있습니다.",
               "Claude, Gemini 또는 ChatGPT로 번역을 검사합니다.",
               "결과를 보고서, 문제 목록, 요약 또는 데이터로 내보냅니다."],
        "pt": ["Avalie uma dublagem em relação ao original: tempo, voz, sentido e som, com cada problema numa linha do tempo.",
               "Cada avaliação fica na tela Avaliações, com uma imagem: abra, renomeie ou apague; uma página começada fica como rascunho.",
               "Compare até 8 dublagens de um vídeo e receba uma recomendação com o motivo.",
               "Cole links do YouTube, TikTok, Reels ou de compartilhamento do Perso, ou escolha arquivos neste computador.",
               "Verificação de sentido offline, reconhecimento mais rápido em placas NVIDIA e um modelo de fala grande em "
               "Configurações → Modelos.",
               "Verificação da tradução com Claude, Gemini ou ChatGPT.",
               "Exporte os resultados como relatório, lista de problemas, resumo ou dados."],
        "es": ["Evalúa un doblaje frente a su original: tiempos, voz, sentido y sonido, con cada problema en una línea de "
               "Cada evaluación queda en la pantalla Evaluaciones, con una imagen: ábrela, cámbiale el nombre o bórrala; una página empezada queda como borrador.",
               "tiempo.",
               "Compara hasta 8 doblajes de un video y recibe una recomendación con el motivo.",
               "Pega enlaces de YouTube, TikTok, Reels o para compartir de Perso, o elige archivos de este equipo.",
               "Comprobación de sentido sin conexión, reconocimiento más rápido en tarjetas NVIDIA y un modelo de habla "
               "grande en Ajustes → Modelos.",
               "Comprobación de la traducción con Claude, Gemini o ChatGPT.",
               "Exporta los resultados como informe, lista de problemas, resumen o datos."],
    },
}


def notes(version: str, lang: str) -> list[str]:
    """The lines for version in lang (English when that language has none; empty for an unknown version)."""
    entry = NOTES.get(version) or {}
    return list(entry.get(lang) or entry.get("en") or [])
