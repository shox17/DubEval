"""What's new in each version, as the app's "What's new" card shows it: a few plain lines per language.

Add the new version's lines here (en, ko, pt, es) whenever TOOL_VERSION changes; tests check the current one exists.
"""

NOTES = {
    "0.1.3": {
        "en": ["Fixed: in the installed app, evaluations stopped at Measure quality with a NO_SUCHFILE error (silero_vad_v6.onnx).",
               "If the voice detector ever can't load, the evaluation now goes on without it instead of stopping."],
        "ko": ["수정: 설치한 앱에서 평가가 품질 측정 단계에서 NO_SUCHFILE 오류(silero_vad_v6.onnx)로 멈추던 문제를 고쳤습니다.",
               "음성 감지기를 불러오지 못하더라도 이제 평가가 멈추지 않고 감지기 없이 계속됩니다."],
        "pt": ["Corrigido: no app instalado, as avaliações paravam em Medir a qualidade com um erro NO_SUCHFILE (silero_vad_v6.onnx).",
               "Se o detector de voz não puder ser carregado, a avaliação agora continua sem ele em vez de parar."],
        "es": ["Corregido: en la app instalada, las evaluaciones se detenían en Medir la calidad con un error NO_SUCHFILE (silero_vad_v6.onnx).",
               "Si el detector de voz no se puede cargar, la evaluación ahora sigue sin él en lugar de detenerse."],
    },
    "0.1.2": {
        "en": ["Start from Home: upload the dubbed video or paste its link, and the new evaluation opens with it in place.",
               "Any video link works: Dropbox, Google Drive, OneDrive and links to video files download too, as well as YouTube, TikTok and Reels.",
               "Fewer false alarms: music is no longer read as speech, lines the speech recognizer skipped are recovered, and differences too small to notice aren't flagged.",
               "New check: whether the dub's sound is in step with its picture. Original-language speech left in the dub is found more reliably.",
               "DubEval says when it isn't sure: with little or unclear speech, or no translation check, the verdict is Needs review with the reason, never a confident Good.",
               "Fairer meaning grade: Poor needs three or more badly translated lines, and a line that may just be misheard becomes a moment to listen to.",
               "Lip-sync check (optional download in Settings → Models): how often the lips follow the dubbed speech, next to the original, shown for information.",
               "Translation check on this computer (optional download): nothing is sent out, but it's less exact than Claude or Gemini.",
               "Review the problems: step through every flagged moment with Previous and Next.",
               "New Settings (API keys, Models, Storage, Privacy, About, with Save), new Help, a new icon, and Home and Evaluation history fill the window.",
               "Many fixes: renaming a comparison renames every dub, votes stay after renaming, and Settings no longer closes when an evaluation finishes."],
        "ko": ["홈에서 시작: 더빙 영상을 올리거나 링크를 붙여 넣으면 그 영상이 들어간 새 평가가 열립니다.",
               "어떤 영상 링크든 됩니다: YouTube, TikTok, Reels와 함께 Dropbox, Google Drive, OneDrive, 영상 파일 링크도 내려받습니다.",
               "잘못된 경고가 줄었습니다: 음악을 말소리로 읽지 않고, 음성 인식이 건너뛴 대사를 되찾고, 알아차리기 어려운 작은 차이는 표시하지 않습니다.",
               "새 검사: 더빙 소리가 화면과 맞는지 확인합니다. 더빙에 남은 원어 음성도 더 잘 찾습니다.",
               "확실하지 않을 때는 그렇게 알려 줍니다: 말소리가 적거나 불분명하거나 번역 검사를 하지 않았으면, 판정은 이유와 함께 검토 필요이고 좋음으로 단정하지 않습니다.",
               "더 공정한 의미 판정: 미흡은 잘못 번역된 대사가 세 줄 이상일 때만이고, 잘못 들었을 수 있는 대사는 들어 볼 순간으로 표시합니다.",
               "립싱크 검사(설정 → 모델에서 선택해 다운로드): 원본과 비교해 입 모양이 더빙 음성을 얼마나 따라가는지 참고용으로 보여 줍니다.",
               "이 컴퓨터에서 하는 번역 검사(선택 다운로드): 아무것도 밖으로 보내지 않지만 Claude나 Gemini보다 덜 정확합니다.",
               "문제 하나씩 검토: 표시된 모든 순간을 이전과 다음으로 살펴봅니다.",
               "새 설정(API 키, 모델, 저장 공간, 개인정보, 정보, 저장 버튼), 새 도움말, 새 아이콘, 그리고 홈과 평가 기록이 창 너비에 맞춰 넓어집니다.",
               "여러 문제를 고쳤습니다: 비교 평가 이름을 바꾸면 모든 더빙에 반영되고, 이름을 바꿔도 투표가 남으며, 평가가 끝나도 설정 창이 닫히지 않습니다."],
        "pt": ["Comece pelo Início: envie o vídeo dublado ou cole o link dele, e a nova avaliação abre com ele no lugar.",
               "Qualquer link de vídeo funciona: Dropbox, Google Drive, OneDrive e links de arquivos de vídeo também são baixados, além de YouTube, TikTok e Reels.",
               "Menos alarmes falsos: a música não é mais lida como fala, falas que o reconhecimento pulou são recuperadas e diferenças pequenas demais para notar não são marcadas.",
               "Nova verificação: se o som da dublagem está alinhado com a imagem. A fala no idioma original que ficou na dublagem é encontrada com mais segurança.",
               "O DubEval diz quando não tem certeza: com pouca fala, fala pouco clara ou sem verificação da tradução, o resultado é Precisa de revisão com o motivo, nunca um Bom confiante.",
               "Nota de sentido mais justa: Ruim exige três ou mais falas mal traduzidas, e uma fala que pode ter sido mal ouvida vira um momento para ouvir.",
               "Verificação de sincronia labial (download opcional em Configurações → Modelos): quantas vezes os lábios acompanham a fala dublada, ao lado do original, só como informação.",
               "Verificação da tradução neste computador (download opcional): nada é enviado, mas é menos precisa que Claude ou Gemini.",
               "Revisar os problemas: passe por cada momento marcado com Anterior e Próximo.",
               "Novas Configurações (Chaves de API, Modelos, Armazenamento, Privacidade, Sobre, com Salvar), nova Ajuda, novo ícone, e o Início e o Histórico de avaliações ocupam a janela toda.",
               "Muitas correções: renomear uma comparação renomeia todas as dublagens, os votos ficam depois de renomear e as Configurações não fecham mais quando uma avaliação termina."],
        "es": ["Empieza desde Inicio: sube el video doblado o pega su enlace, y la nueva evaluación se abre con él en su lugar.",
               "Cualquier enlace de video funciona: también se descargan Dropbox, Google Drive, OneDrive y enlaces a archivos de video, además de YouTube, TikTok y Reels.",
               "Menos falsas alarmas: la música ya no se lee como habla, se recuperan las frases que el reconocimiento se saltó y no se marcan diferencias demasiado pequeñas para notarse.",
               "Nueva comprobación: si el sonido del doblaje va a la par de la imagen. La voz en el idioma original que quedó en el doblaje se encuentra con más seguridad.",
               "DubEval dice cuándo no está seguro: con poca habla, habla poco clara o sin comprobación de la traducción, el resultado es Necesita revisión con el motivo, nunca un Bien seguro.",
               "Nota de sentido más justa: Deficiente requiere tres o más frases mal traducidas, y una frase que quizá se oyó mal se convierte en un momento para escuchar.",
               "Comprobación de sincronía labial (descarga opcional en Ajustes → Modelos): cuántas veces los labios siguen la voz doblada, junto al original, solo como información.",
               "Comprobación de la traducción en este equipo (descarga opcional): no se envía nada, pero es menos precisa que Claude o Gemini.",
               "Revisar los problemas: recorre cada momento marcado con Anterior y Siguiente.",
               "Nuevos Ajustes (Claves de API, Modelos, Almacenamiento, Privacidad, Acerca de, con Guardar), nueva Ayuda, nuevo icono, e Inicio e Historial de evaluaciones ocupan toda la ventana.",
               "Muchas correcciones: cambiar el nombre de una comparación lo cambia en todos los doblajes, los votos se mantienen al cambiar el nombre y los Ajustes ya no se cierran cuando termina una evaluación."],
    },
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
               "tiempo.",
               "Cada evaluación queda en la pantalla Evaluaciones, con una imagen: ábrela, cámbiale el nombre o bórrala; una página empezada queda como borrador.",
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
