"""Interface text in English, Korean, Portuguese (Brazil) and Spanish.

TEXT holds every interface string (the web page's own are in web_text.py), keyed by a short id. MESSAGES translates the fixed English progress
messages that dubeval/ reports (Perso steps, pipeline and evaluation steps); anything else stays in English.
Placeholders like {n} are filled with str.format, so every translation must use the same placeholders.
"""
from typing import Optional

UI_LANGUAGES = {"en": "English", "ko": "한국어", "pt": "Português", "es": "Español"}
DEFAULT_UI_LANGUAGE = "en"

TEXT = {
    # ----- sidebar -----
    "app.tagline": {
        "en": "Paste a Perso share link and get a detailed quality report on the dub.",
        "ko": "Perso 공유 링크를 붙여 넣으면 더빙 품질에 대한 상세 보고서를 받을 수 있습니다.",
        "pt": "Cole um link de compartilhamento da Perso e receba um relatório detalhado da dublagem.",
        "es": "Pega un enlace compartido de Perso y recibe un informe detallado del doblaje.",
    },
    "ui_language": {"en": "Interface language", "ko": "화면 언어", "pt": "Idioma da interface",
                    "es": "Idioma de la interfaz"},
    "how.title": {"en": "How it works", "ko": "작동 방식", "pt": "Como funciona", "es": "Cómo funciona"},
    "how.body": {
        "en": "1. **Paste** a Perso share link.\n"
              "2. The app **downloads** the original and the dub (the lip-synced one when there is one).\n"
              "3. Both are **measured**: length, loudness, silence, speaking pace, the dub's language and clarity "
              "(speech recognition), when each track speaks, and the video file itself.\n"
              "4. **An AI model checks the translation** (Gemini, or Claude): meaning, missing or added content, names and numbers.\n"
              "5. You get a **report**: a verdict, every measure with Good / Check / Poor and a plain explanation, "
              "and timestamped places to check.",
        "ko": "1. Perso 공유 링크를 **붙여 넣습니다**.\n"
              "2. 앱이 원본과 더빙 영상을 **다운로드**합니다(립싱크 영상이 있으면 그것을 사용).\n"
              "3. 두 영상을 **측정**합니다: 길이, 음량, 무음, 말 속도, 더빙 언어와 명료도(음성 인식), "
              "각 트랙이 말하는 구간, 영상 파일 자체.\n"
              "4. **AI 모델이 번역을 검토**합니다(Gemini 또는 Claude): 의미, 누락·추가된 내용, 이름과 숫자.\n"
              "5. **보고서**를 받습니다: 판정, 항목별 좋음 / 확인 필요 / 미흡과 쉬운 설명, 시간이 표시된 확인할 곳.",
        "pt": "1. **Cole** um link de compartilhamento da Perso.\n"
              "2. O app **baixa** o original e a dublagem (a versão com sincronização labial, se houver).\n"
              "3. Os dois são **medidos**: duração, volume, silêncio, ritmo da fala, idioma e clareza da dublagem "
              "(reconhecimento de fala), quando cada faixa fala e o próprio arquivo de vídeo.\n"
              "4. **Um modelo de IA verifica a tradução** (Gemini ou Claude): sentido, conteúdo faltando ou a mais, nomes e números.\n"
              "5. Você recebe um **relatório**: o resultado, cada medida com Bom / Verificar / Ruim e uma explicação simples, "
              "e os pontos a verificar com horário.",
        "es": "1. **Pega** un enlace compartido de Perso.\n"
              "2. La app **descarga** el original y el doblaje (el de sincronización labial, si existe).\n"
              "3. Se **miden** ambos: duración, volumen, silencio, ritmo del habla, idioma y claridad del doblaje "
              "(reconocimiento de voz), cuándo habla cada pista y el propio archivo de video.\n"
              "4. **Un modelo de IA revisa la traducción** (Gemini o Claude): sentido, contenido que falta o sobra, nombres y números.\n"
              "5. Recibes un **informe**: el resultado, cada medida con Bien / Revisar / Deficiente y una explicación sencilla, "
              "y los puntos a revisar con su momento.",
    },
    "sidebar.last_result": {"en": "Show last result", "ko": "마지막 결과 보기", "pt": "Mostrar último resultado",
                            "es": "Ver último resultado"},

    # ----- stages (progress checklist) -----
    "stage.pack": {"en": "Download", "ko": "다운로드", "pt": "Download", "es": "Descarga"},
    "stage.prepare": {"en": "Check both files", "ko": "두 파일 확인", "pt": "Verificar os dois arquivos",
                      "es": "Comprobar los dos archivos"},
    "stage.fetch": {"en": "Read the share link", "ko": "공유 링크 읽기", "pt": "Ler o link de compartilhamento",
                    "es": "Leer el enlace compartido"},
    "stage.download": {"en": "Download both videos", "ko": "두 영상 다운로드", "pt": "Baixar os dois vídeos",
                       "es": "Descargar ambos videos"},
    "stage.evaluate": {"en": "Measure quality", "ko": "품질 측정", "pt": "Medir a qualidade", "es": "Medir la calidad"},
    "stage.dub_a": {"en": "Evaluate dub A", "ko": "더빙 A 평가", "pt": "Avaliar a dublagem A", "es": "Evaluar el doblaje A"},
    "stage.dub_b": {"en": "Evaluate dub B", "ko": "더빙 B 평가", "pt": "Avaliar a dublagem B", "es": "Evaluar el doblaje B"},
    "stage.dub_c": {"en": "Evaluate dub C", "ko": "더빙 C 평가", "pt": "Avaliar a dublagem C",
                    "es": "Evaluar el doblaje C"},
    "stage.dub_d": {"en": "Evaluate dub D", "ko": "더빙 D 평가", "pt": "Avaliar a dublagem D",
                    "es": "Evaluar el doblaje D"},
    "stage.dub_e": {"en": "Evaluate dub E", "ko": "더빙 E 평가", "pt": "Avaliar a dublagem E",
                    "es": "Evaluar el doblaje E"},
    "stage.dub_f": {"en": "Evaluate dub F", "ko": "더빙 F 평가", "pt": "Avaliar a dublagem F",
                    "es": "Evaluar el doblaje F"},
    "stage.dub_g": {"en": "Evaluate dub G", "ko": "더빙 G 평가", "pt": "Avaliar a dublagem G",
                    "es": "Evaluar el doblaje G"},
    "stage.dub_h": {"en": "Evaluate dub H", "ko": "더빙 H 평가", "pt": "Avaliar a dublagem H",
                    "es": "Evaluar el doblaje H"},
    "stage.batch": {"en": "Evaluate every link", "ko": "모든 링크 평가", "pt": "Avaliar todos os links",
                    "es": "Evaluar todos los enlaces"},
    "stage.compare": {"en": "Compare and recommend", "ko": "비교 및 추천", "pt": "Comparar e recomendar",
                      "es": "Comparar y recomendar"},

    # ----- time -----
    "time.min_sec": {"en": "{m} min {s} s", "ko": "{m}분 {s}초", "pt": "{m} min {s} s", "es": "{m} min {s} s"},
    "time.sec": {"en": "{s} s", "ko": "{s}초", "pt": "{s} s", "es": "{s} s"},

    # ----- progress page -----
    "progress.title": {"en": "Evaluating the dub", "ko": "더빙 평가 중", "pt": "Avaliando a dublagem",
                       "es": "Evaluando el doblaje"},
    "progress.title_compare": {"en": "Evaluating the dubs", "ko": "더빙 평가 중", "pt": "Avaliando as dublagens",
                               "es": "Evaluando los doblajes"},
    "progress.overall": {"en": "Overall", "ko": "전체", "pt": "Total", "es": "Total"},
    "progress.elapsed": {"en": "Elapsed", "ko": "경과 시간", "pt": "Tempo decorrido", "es": "Tiempo transcurrido"},
    "progress.stop": {"en": "Stop waiting", "ko": "기다리기 중지", "pt": "Parar de esperar", "es": "Dejar de esperar"},
    "progress.stop_help": {
        "en": "Stops this evaluation. Nothing on Perso is changed.",
        "ko": "이 평가를 중지합니다. Perso에는 아무것도 바뀌지 않습니다.",
        "pt": "Interrompe esta avaliação. Nada é alterado na Perso.",
        "es": "Detiene esta evaluación. No se cambia nada en Perso.",
    },
    "progress.stopping": {"en": "Stopping... this takes a few seconds.", "ko": "중지하는 중... 몇 초 걸립니다.",
                          "pt": "Parando... isso leva alguns segundos.", "es": "Deteniendo... tarda unos segundos."},

    # ----- results page -----
    "results.title": {"en": "Results", "ko": "결과", "pt": "Resultados", "es": "Resultados"},
    "results.download": {"en": "Data (JSON)", "ko": "데이터 (JSON)", "pt": "Dados (JSON)", "es": "Datos (JSON)"},
    "results.download_help": {"en": "The report plus every measurement as a JSON file.",
                              "ko": "보고서와 모든 측정값을 담은 JSON 파일입니다.",
                              "pt": "O relatório e todas as medições em um arquivo JSON.",
                              "es": "El informe y todas las mediciones en un archivo JSON."},
    "results.new": {"en": "New evaluation", "ko": "새 평가", "pt": "Nova avaliação", "es": "Nueva evaluación"},
    "results.things_to_check": {"en": "Things to check", "ko": "확인할 사항", "pt": "Pontos a verificar",
                                "es": "Cosas que revisar"},
    "results.original": {"en": "Original", "ko": "원본", "pt": "Original", "es": "Original"},
    "results.dubbed": {"en": "Dubbed", "ko": "더빙", "pt": "Dublado", "es": "Doblado"},
    "results.video_gone": {
        "en": "The dubbed video file is no longer on disk (old runs are cleaned up).",
        "ko": "더빙된 영상 파일이 더 이상 디스크에 없습니다(오래된 실행은 정리됩니다).",
        "pt": "O arquivo do vídeo dublado não está mais no disco (execuções antigas são apagadas).",
        "es": "El archivo del video doblado ya no está en el disco (las ejecuciones antiguas se eliminan).",
    },
    "badge.good": {"en": "Good", "ko": "좋음", "pt": "Bom", "es": "Bien"},
    "badge.check": {"en": "Check", "ko": "확인 필요", "pt": "Verificar", "es": "Revisar"},
    "badge.poor": {"en": "Poor", "ko": "미흡", "pt": "Ruim", "es": "Deficiente"},
    "badge.info": {"en": "Info", "ko": "참고", "pt": "Informativo", "es": "Informativo"},
    "badge.na": {"en": "Not measured", "ko": "측정 안 함", "pt": "Não medido", "es": "No medido"},

    # ----- report (results page) -----
    "verdict.good": {"en": "Good", "ko": "좋음", "pt": "Bom", "es": "Bien"},
    "verdict.check": {"en": "Needs review", "ko": "검토 필요", "pt": "Precisa de revisão", "es": "Necesita revisión"},
    "verdict.poor": {"en": "Poor", "ko": "미흡", "pt": "Ruim", "es": "Deficiente"},
    "verdict.counts": {
        "en": "{good} good · {check} needs review · {poor} poor · {na} not measured",
        "ko": "좋음 {good} · 검토 필요 {check} · 미흡 {poor} · 측정 안 함 {na}",
        "pt": "{good} bons · {check} para revisar · {poor} ruins · {na} não medidos",
        "es": "{good} bien · {check} por revisar · {poor} deficientes · {na} sin medir",
    },
    "verdict.rule": {
        "en": "Any Poor makes the verdict Poor; otherwise any Check makes it Needs review. "
              "Info and not-measured items don't count. When DubEval isn't sure (little or unclear speech), only "
              "problems that don't depend on speech can make it Poor; when the dub's words couldn't be checked, it "
              "is never Good.",
        "ko": "미흡 항목이 하나라도 있으면 '미흡', 없고 확인 필요 항목이 있으면 '검토 필요'입니다. "
              "참고와 측정 안 함 항목은 판정에 포함되지 않습니다. DubEval이 확실하지 않을 때(말소리가 적거나 불분명함)는 "
              "말소리와 무관한 문제만 '미흡'이 될 수 있고, 더빙의 말을 확인하지 못했을 때는 '좋음'이 되지 않습니다.",
        "pt": "Qualquer item Ruim torna o resultado Ruim; senão, qualquer item Verificar o torna Precisa de revisão. "
              "Itens informativos e não medidos não contam. Quando o DubEval não tem certeza (pouca fala ou fala "
              "pouco clara), só problemas que não dependem da fala o tornam Ruim; quando as palavras da dublagem não "
              "puderam ser verificadas, ele nunca é Bom.",
        "es": "Cualquier elemento Deficiente hace el resultado Deficiente; si no, cualquier Revisar lo hace Necesita revisión. "
              "Los informativos y los no medidos no cuentan. Cuando DubEval no está seguro (poca voz o voz poco "
              "clara), solo los problemas que no dependen de la voz lo hacen Deficiente; cuando no se pudieron "
              "comprobar las palabras del doblaje, nunca es Bien.",
    },
    # ----- labelling page (dubeval/labeling.py) -----
    "lab.title": {"en": 'Label the test set', "ko": '테스트 세트 라벨링', "pt": 'Rotular o conjunto de teste', "es": 'Etiquetar el conjunto de prueba'},
    "lab.intro": {"en": "Watch each original and dub, then give your own verdict. DubEval's verdict appears only after you answer.", "ko": '원본과 더빙을 보고 직접 판정하세요. DubEval의 판정은 답한 뒤에만 보입니다.', "pt": 'Assista a cada original e dublagem e dê sua avaliação. A avaliação do DubEval só aparece depois da sua resposta.', "es": 'Mira cada original y doblaje y da tu propia valoración. La valoración de DubEval solo aparece después de responder.'},
    "lab.original": {"en": 'Original', "ko": '원본', "pt": 'Original', "es": 'Original'},
    "lab.dub": {"en": 'Dub', "ko": '더빙', "pt": 'Dublagem', "es": 'Doblaje'},
    "lab.listen": {"en": 'Listen to', "ko": '들을 소리', "pt": 'Ouvir', "es": 'Escuchar'},
    "lab.listen_dub": {"en": 'Dub', "ko": '더빙', "pt": 'Dublagem', "es": 'Doblaje'},
    "lab.listen_original": {"en": 'Original', "ko": '원본', "pt": 'Original', "es": 'Original'},
    "lab.play": {"en": 'Play both', "ko": '둘 다 재생', "pt": 'Reproduzir os dois', "es": 'Reproducir ambos'},
    "lab.pause": {"en": 'Pause', "ko": '일시 정지', "pt": 'Pausar', "es": 'Pausar'},
    "lab.q_length": {"en": 'Length and timing', "ko": '길이와 타이밍', "pt": 'Duração e tempo', "es": 'Duración y tiempo'},
    "lab.h_length": {"en": "Good: speech matches the original's timing, nothing rushed or cut. Check: some lines noticeably fast, late or cut, or you're unsure. Poor: clearly out of sync, cut off, or long silences.", "ko": "좋음: 원본 타이밍과 맞고 빠르거나 잘린 곳이 없음. 확인 필요: 일부 대사가 눈에 띄게 빠르거나 늦거나 잘림, 또는 확신이 없음. 나쁨: 확실히 어긋나거나 잘리거나 긴 침묵이 있음.", "pt": "Bom: a fala acompanha o tempo do original, nada apressado ou cortado. Verificar: algumas falas visivelmente rápidas, atrasadas ou cortadas, ou você não tem certeza. Ruim: claramente fora de sincronia, cortado ou com longos silêncios.", "es": "Bien: el habla sigue los tiempos del original, nada apresurado ni cortado. Revisar: algunas frases claramente rápidas, tardías o cortadas, o no estás seguro. Mal: claramente desincronizado, cortado o con silencios largos."},
    "lab.q_meaning": {"en": 'Meaning', "ko": '의미', "pt": 'Sentido', "es": 'Sentido'},
    "lab.h_meaning": {"en": "Good: says what the original says (wording may differ). Check: small errors a viewer might notice, or you're unsure. Poor: wrong or missing meaning that misleads the viewer.", "ko": "좋음: 원본과 같은 내용(표현은 달라도 됨). 확인 필요: 시청자가 알아챌 만한 작은 오류, 또는 확신이 없음. 나쁨: 시청자를 오해하게 하는 틀린 내용이나 빠진 내용.", "pt": "Bom: diz o que o original diz (as palavras podem mudar). Verificar: pequenos erros que o público pode notar, ou você não tem certeza. Ruim: sentido errado ou faltando, que engana o público.", "es": "Bien: dice lo que dice el original (las palabras pueden cambiar). Revisar: pequeños errores que el público podría notar, o no estás seguro. Mal: sentido erróneo o ausente que confunde al público."},
    "lab.q_overall": {"en": 'Overall', "ko": '전체', "pt": 'Geral', "es": 'General'},
    "lab.h_overall": {"en": "Good: I would deliver this dub as it is. Check: deliverable after small fixes, or I'm unsure. Poor: not deliverable; it needs redoing.", "ko": "좋음: 이대로 납품하겠다. 확인 필요: 작은 수정 후 납품 가능하거나, 확신이 없다. 나쁨: 납품 불가, 다시 만들어야 한다.", "pt": "Bom: eu entregaria esta dublagem como está. Verificar: entregável após pequenas correções, ou não tenho certeza. Ruim: não entregável; precisa ser refeita.", "es": "Bien: entregaría este doblaje tal como está. Revisar: entregable tras pequeños arreglos, o no estoy seguro. Mal: no entregable; hay que rehacerlo."},
    "lab.c_good": {"en": 'Good', "ko": '좋음', "pt": 'Bom', "es": 'Bien'},
    "lab.c_check": {"en": 'Check', "ko": '확인 필요', "pt": 'Verificar', "es": 'Revisar'},
    "lab.c_poor": {"en": 'Poor', "ko": '나쁨', "pt": 'Ruim', "es": 'Mal'},
    "lab.c_na": {"en": 'not measured', "ko": '측정 안 됨', "pt": 'não medido', "es": 'no medido'},
    "lab.notes": {"en": 'Notes', "ko": '메모', "pt": 'Notas', "es": 'Notas'},
    "lab.reviewer": {"en": 'Your name', "ko": '이름', "pt": 'Seu nome', "es": 'Tu nombre'},
    "lab.next": {"en": 'Next pair', "ko": '다음 쌍', "pt": 'Próximo par', "es": 'Siguiente par'},
    "lab.answer_all": {"en": 'Answer all three questions first.', "ko": '세 가지 질문에 모두 먼저 답하세요.', "pt": 'Responda às três perguntas primeiro.', "es": 'Responde primero a las tres preguntas.'},
    "lab.tool_hidden": {"en": "DubEval's verdict appears after you answer all three questions.", "ko": '세 가지 질문에 모두 답하면 DubEval의 판정이 보입니다.', "pt": 'A avaliação do DubEval aparece depois que você responder às três perguntas.', "es": 'La valoración de DubEval aparece después de responder a las tres preguntas.'},
    "lab.tool_says": {"en": 'DubEval says', "ko": 'DubEval 판정', "pt": 'O DubEval diz', "es": 'DubEval dice'},
    "lab.saved": {"en": 'Saved to the sheet.', "ko": '시트에 저장했습니다.', "pt": 'Salvo na planilha.', "es": 'Guardado en la hoja.'},
    "lab.save_failed": {"en": "Couldn't save. Is the label command still running?", "ko": '저장하지 못했습니다. label 명령이 아직 실행 중인가요?', "pt": 'Não foi possível salvar. O comando label ainda está rodando?', "es": 'No se pudo guardar. ¿Sigue en marcha el comando label?'},
    "rsec.pairing": {"en": "Same video", "ko": "같은 영상 확인", "pt": "Mesmo vídeo", "es": "Mismo video"},
    "rsec.timing_audio": {"en": "Timing & audio", "ko": "타이밍 & 오디오", "pt": "Tempo e áudio", "es": "Tiempo y audio"},
    "rsec.speech": {"en": "Speech recognition", "ko": "음성 인식", "pt": "Reconhecimento de fala",
                    "es": "Reconocimiento de voz"},
    "rsec.alignment": {"en": "Timing alignment", "ko": "발화 타이밍", "pt": "Alinhamento da fala",
                       "es": "Alineación del habla"},
    "rsec.translation": {"en": "Translation", "ko": "번역", "pt": "Tradução", "es": "Traducción"},
    "rsec.integrity": {"en": "Video integrity", "ko": "영상 무결성", "pt": "Integridade do vídeo",
                       "es": "Integridad del video"},
    "rsec.lipsync": {"en": "Lip movement (experimental)", "ko": "입 움직임 (실험적)",
                     "pt": "Movimento dos lábios (experimental)", "es": "Movimiento de los labios (experimental)"},
    "rsec.lip_sync": {"en": "Lip sync", "ko": "립싱크", "pt": "Sincronia labial", "es": "Sincronía labial"},
    "report.no_things": {"en": "Nothing specific to check.", "ko": "특별히 확인할 곳이 없습니다.",
                         "pt": "Nada específico para verificar.", "es": "Nada específico que revisar."},
    "report.jump_help": {"en": "Play both videos from this moment.", "ko": "두 영상을 이 지점부터 재생합니다.",
                         "pt": "Reproduz os dois vídeos a partir deste momento.",
                         "es": "Reproduce ambos videos desde este momento."},
    "report.not_measured": {"en": "Not measured", "ko": "측정하지 않은 항목", "pt": "Não medido", "es": "No medido"},
    "report.details": {"en": "Detailed measurements", "ko": "상세 측정값", "pt": "Medições detalhadas",
                       "es": "Mediciones detalladas"},
    "report.download_html": {"en": "Report (HTML)", "ko": "보고서 (HTML)", "pt": "Relatório (HTML)",
                             "es": "Informe (HTML)"},
    "report.download_html_help": {
        "en": "A standalone page you can open in any browser or send to your team.",
        "ko": "어느 브라우저에서나 열 수 있고 팀에 보낼 수 있는 단독 페이지입니다.",
        "pt": "Uma página independente para abrir em qualquer navegador ou enviar à equipe.",
        "es": "Una página independiente que puedes abrir en cualquier navegador o enviar a tu equipo.",
    },
    "report.timeline_title": {"en": "When each track speaks", "ko": "각 트랙이 말하는 구간", "pt": "Quando cada faixa fala",
                              "es": "Cuándo habla cada pista"},
    "report.timeline_caption": {
        "en": "Bars show speech. Red boxes mark places where only one track speaks.",
        "ko": "막대는 말하는 구간입니다. 빨간 상자는 한쪽 트랙만 말하는 곳입니다.",
        "pt": "As barras mostram a fala. Caixas vermelhas marcam trechos em que só uma faixa fala.",
        "es": "Las barras muestran el habla. Los recuadros rojos marcan donde solo habla una pista.",
    },
    "report.open_perso": {"en": "Open in Perso", "ko": "Perso에서 열기", "pt": "Abrir na Perso", "es": "Abrir en Perso"},
    "table.title": {"en": "Original vs dubbed", "ko": "원본 vs 더빙", "pt": "Original vs dublado",
                    "es": "Original vs doblado"},
    "table.measure": {"en": "Measure", "ko": "항목", "pt": "Medida", "es": "Medida"},
    "table.difference": {"en": "Difference", "ko": "차이", "pt": "Diferença", "es": "Diferencia"},
    "table.meaning": {"en": "What it means", "ko": "의미", "pt": "O que significa", "es": "Qué significa"},
    "row.duration": {"en": "Duration", "ko": "길이", "pt": "Duração", "es": "Duración"},
    "row.duration_help": {"en": "Total length. A good dub keeps the same length.",
                          "ko": "전체 길이입니다. 좋은 더빙은 길이가 같습니다.",
                          "pt": "Duração total. Uma boa dublagem mantém a mesma duração.",
                          "es": "Duración total. Un buen doblaje mantiene la misma duración."},
    "row.speaking": {"en": "Speaking time", "ko": "발화 시간", "pt": "Tempo de fala", "es": "Tiempo de habla"},
    "row.speaking_help": {"en": "Time with sound above the silence threshold.",
                          "ko": "무음 기준보다 큰 소리가 나는 시간입니다.",
                          "pt": "Tempo com som acima do limite de silêncio.",
                          "es": "Tiempo con sonido por encima del umbral de silencio."},
    "row.loudness": {"en": "Loudness", "ko": "음량", "pt": "Volume", "es": "Volumen"},
    "row.loudness_help": {"en": "Average volume. Within ±2 dB sounds the same.",
                          "ko": "평균 음량입니다. ±2 dB 이내면 같게 들립니다.",
                          "pt": "Volume médio. Até ±2 dB soa igual.",
                          "es": "Volumen medio. Dentro de ±2 dB suena igual."},
    "row.steadiness": {"en": "Volume steadiness", "ko": "음량 안정성", "pt": "Estabilidade do volume",
                       "es": "Estabilidad del volumen"},
    "row.steadiness_help": {"en": "Higher means a more even volume.", "ko": "높을수록 음량이 고릅니다.",
                            "pt": "Quanto maior, mais uniforme o volume.",
                            "es": "Cuanto más alto, más uniforme el volumen."},
    "row.silence": {"en": "Silence", "ko": "무음", "pt": "Silêncio", "es": "Silencio"},
    "row.silence_help": {"en": "Share of the video without sound.", "ko": "소리가 없는 구간의 비율입니다.",
                         "pt": "Parte do vídeo sem som.", "es": "Parte del video sin sonido."},
    "row.rate": {"en": "Speech rate", "ko": "말하기 속도", "pt": "Velocidade da fala", "es": "Velocidad del habla"},
    "row.rate_help": {"en": "How fast the speaker talks. Units differ per language, so compare with care.",
                      "ko": "말하는 속도입니다. 언어마다 단위가 달라 비교에 주의하세요.",
                      "pt": "A velocidade com que a pessoa fala. As unidades variam por idioma, compare com cuidado.",
                      "es": "Qué tan rápido habla la persona. Las unidades varían por idioma, compara con cuidado."},
    "row.lipsync": {"en": "Lip-sync r (experimental)", "ko": "립싱크 r (실험적)",
                    "pt": "Sincronização labial r (experimental)", "es": "Sincronización labial r (experimental)"},
    "row.lipsync_help": {"en": "Mouth opening vs voice loudness. Only meaningful relative to the original.",
                         "ko": "입 벌림과 음성 크기의 관계입니다. 원본과 비교할 때만 의미가 있습니다.",
                         "pt": "Abertura da boca vs volume da voz. Só faz sentido em relação ao original.",
                         "es": "Apertura de la boca frente al volumen de la voz. Solo tiene sentido frente al original."},
    "row.face": {"en": "Face visible", "ko": "얼굴 인식", "pt": "Rosto visível", "es": "Rostro visible"},
    "row.face_help": {"en": "Share of frames where a face was found.", "ko": "얼굴이 발견된 프레임의 비율입니다.",
                      "pt": "Parte dos quadros em que um rosto foi encontrado.",
                      "es": "Parte de los fotogramas en los que se encontró un rostro."},
    "unit.pts": {"en": "pts", "ko": "%p", "pt": "p.p.", "es": "p.p."},
    "unit.words/s": {"en": "words/s", "ko": "단어/초", "pt": "palavras/s", "es": "palabras/s"},
    "unit.chars/s": {"en": "chars/s", "ko": "글자/초", "pt": "caracteres/s", "es": "caracteres/s"},
    "chart.loudness_title": {"en": "Loudness over time", "ko": "시간에 따른 음량", "pt": "Volume ao longo do tempo",
                             "es": "Volumen a lo largo del tiempo"},
    "chart.seconds": {"en": "seconds", "ko": "초", "pt": "segundos", "es": "segundos"},
    "chart.loudness_caption": {
        "en": "Peaks should line up: speech in the dub should start and stop where the original does.",
        "ko": "봉우리가 겹쳐야 합니다. 더빙의 말소리가 원본과 같은 곳에서 시작하고 끝나야 합니다.",
        "pt": "Os picos devem se alinhar: a fala na dublagem deve começar e parar onde o original faz.",
        "es": "Los picos deben coincidir: el habla del doblaje debe empezar y terminar donde lo hace el original.",
    },
    "said.title": {"en": "What was said", "ko": "실제로 말한 내용", "pt": "O que foi dito", "es": "Lo que se dijo"},
    "said.tab_script": {"en": "Your script vs the dub", "ko": "내 스크립트 vs 더빙", "pt": "Seu roteiro vs dublagem",
                        "es": "Tu guion vs el doblaje"},
    "said.tab_dub": {"en": "Dubbed speech", "ko": "더빙 음성", "pt": "Fala dublada", "es": "Habla doblada"},
    "said.tab_original": {"en": "Original speech", "ko": "원본 음성", "pt": "Fala original", "es": "Habla original"},
    "said.legend": {
        "en": "Accuracy {acc} · {metric} {err} · :red-background[struck red] = in your script but not heard · "
              ":green-background[green] = heard but not in your script",
        "ko": "정확도 {acc} · {metric} {err} · :red-background[빨간 취소선] = 스크립트에 있지만 들리지 않음 · "
              ":green-background[초록] = 들렸지만 스크립트에 없음",
        "pt": "Precisão {acc} · {metric} {err} · :red-background[vermelho riscado] = no roteiro, mas não ouvido · "
              ":green-background[verde] = ouvido, mas não está no roteiro",
        "es": "Precisión {acc} · {metric} {err} · :red-background[rojo tachado] = en tu guion pero no se oye · "
              ":green-background[verde] = se oye pero no está en tu guion",
    },
    "said.diff_note": {
        "en": "Differences can come from the translation wording, speech-recognition mistakes, or real dubbing errors.",
        "ko": "차이는 번역 표현, 음성 인식 오류, 또는 실제 더빙 오류 때문일 수 있습니다.",
        "pt": "As diferenças podem vir das palavras da tradução, de erros do reconhecimento de fala "
              "ou de erros reais da dublagem.",
        "es": "Las diferencias pueden deberse a la redacción de la traducción, a errores del reconocimiento de voz "
              "o a errores reales del doblaje.",
    },
    "said.detected": {"en": "Detected language: `{lang}`", "ko": "감지된 언어: `{lang}`",
                      "pt": "Idioma detectado: `{lang}`", "es": "Idioma detectado: `{lang}`"},
    "lips.expander": {"en": "Lip movement details (experimental)", "ko": "입 움직임 상세 (실험적)",
                      "pt": "Detalhes do movimento dos lábios (experimental)",
                      "es": "Detalles del movimiento de los labios (experimental)"},
    "lips.mouth": {"en": "Mouth opening", "ko": "입 벌림", "pt": "Abertura da boca", "es": "Apertura de la boca"},
    "lips.voice": {"en": "Voice loudness", "ko": "음성 크기", "pt": "Volume da voz", "es": "Volumen de la voz"},
    "lips.caption": {
        "en": "When the lips match the voice, the two lines rise and fall together. This simple measure is "
              "easily confused by voice-over, cut-aways and background music, so compare the dub with the "
              "original rather than reading the number on its own.",
        "ko": "입이 목소리와 맞으면 두 선이 함께 오르내립니다. 이 간단한 측정은 내레이션, 장면 전환, 배경 음악에 "
              "쉽게 흔들리므로 숫자만 보지 말고 더빙을 원본과 비교하세요.",
        "pt": "Quando os lábios combinam com a voz, as duas linhas sobem e descem juntas. Esta medida simples se "
              "confunde facilmente com narração, cortes de cena e música de fundo, então compare a dublagem com o "
              "original em vez de ler o número sozinho.",
        "es": "Cuando los labios coinciden con la voz, las dos líneas suben y bajan juntas. Esta medida sencilla se "
              "confunde fácilmente con voz en off, cambios de plano y música de fondo, así que compara el doblaje "
              "con el original en lugar de leer el número por sí solo.",
    },

    # ----- setup page -----
    "setup.title": {"en": "Check the quality of a dubbed video", "ko": "더빙 영상 품질 확인",
                    "pt": "Verifique a qualidade de um vídeo dublado", "es": "Revisa la calidad de un video doblado"},
    "setup.intro": {
        "en": "Paste a Perso share link. The app compares the dub with the original and writes a report with a "
              "verdict and the places to check.",
        "ko": "Perso 공유 링크를 붙여 넣으세요. 앱이 더빙을 원본과 비교해 판정과 확인할 곳이 담긴 보고서를 만듭니다.",
        "pt": "Cole um link de compartilhamento da Perso. O app compara a dublagem com o original e gera um relatório "
              "com o resultado e os pontos a verificar.",
        "es": "Pega un enlace compartido de Perso. La app compara el doblaje con el original y genera un informe con "
              "el resultado y los puntos a revisar.",
    },
    "share.title": {"en": "① Paste a Perso share link", "ko": "① Perso 공유 링크 붙여넣기",
                    "pt": "① Cole um link de compartilhamento da Perso", "es": "① Pega un enlace compartido de Perso"},
    "share.caption": {
        "en": "Open the dubbed video in Perso, choose **Share**, and copy the link. "
              "No Perso account or credits are needed.",
        "ko": "Perso에서 더빙된 영상을 열고 **공유**를 눌러 링크를 복사하세요. Perso 계정이나 크레딧이 필요 없습니다.",
        "pt": "Abra o vídeo dublado na Perso, escolha **Compartilhar** e copie o link. "
              "Não é preciso conta nem créditos da Perso.",
        "es": "Abre el video doblado en Perso, elige **Compartir** y copia el enlace. "
              "No necesitas cuenta ni créditos de Perso.",
    },
    "share.label": {"en": "Share link", "ko": "공유 링크", "pt": "Link de compartilhamento", "es": "Enlace compartido"},
    "share.placeholder": {"en": "https://perso.ai/en/share/video-translator?seq=…",
                          "ko": "https://perso.ai/en/share/video-translator?seq=…",
                          "pt": "https://perso.ai/en/share/video-translator?seq=…",
                          "es": "https://perso.ai/en/share/video-translator?seq=…"},
    "share.info_languages": {"en": "Languages", "ko": "언어", "pt": "Idiomas", "es": "Idiomas"},
    "share.info_length": {"en": "Length", "ko": "길이", "pt": "Duração", "es": "Duración"},
    "share.info_lipsync": {"en": "Lip-sync", "ko": "립싱크", "pt": "Sincronização labial", "es": "Sincronización labial"},
    "share.info_videos": {"en": "Videos in the link", "ko": "링크에 포함된 영상", "pt": "Vídeos no link",
                          "es": "Videos en el enlace"},
    "share.info_created": {"en": "Created", "ko": "생성일", "pt": "Criado em", "es": "Creado"},
    "share.info_owner": {"en": "Owner", "ko": "소유자", "pt": "Proprietário", "es": "Propietario"},
    "share.info_project": {"en": "Perso project", "ko": "Perso 프로젝트", "pt": "Projeto Perso", "es": "Proyecto de Perso"},
    "share.yes": {"en": "Yes", "ko": "예", "pt": "Sim", "es": "Sí"},
    "share.no": {"en": "No", "ko": "아니요", "pt": "Não", "es": "No"},
    "share.video_original": {"en": "original", "ko": "원본", "pt": "original", "es": "original"},
    "share.video_dubbed": {"en": "dubbed", "ko": "더빙", "pt": "dublado", "es": "doblado"},
    "share.video_lipsync": {"en": "lip-synced", "ko": "립싱크", "pt": "com sincronização labial",
                            "es": "con sincronización labial"},
    "share.judge_missing": {
        "en": "No API key found for the translation check, so it will show as not measured. "
              "Add GEMINI_API_KEY to the .env file to turn it on.",
        "ko": "번역 검토용 API 키가 없어 '측정 안 함'으로 표시됩니다. .env 파일에 GEMINI_API_KEY를 추가하면 켜집니다.",
        "pt": "Nenhuma chave de API foi encontrada para a verificação da tradução, então ela aparecerá como não medida. "
              "Adicione GEMINI_API_KEY ao arquivo .env para ativá-la.",
        "es": "No se encontró una clave de API para la revisión de la traducción, así que aparecerá como no medida. "
              "Añade GEMINI_API_KEY al archivo .env para activarla.",
    },
    "share.start": {"en": "Evaluate this dub", "ko": "이 더빙 평가하기", "pt": "Avaliar esta dublagem",
                    "es": "Evaluar este doblaje"},
    "mode.single": {"en": "Check one dub", "ko": "더빙 하나 확인", "pt": "Verificar uma dublagem", "es": "Revisar un doblaje"},
    "mode.compare": {"en": "Compare two dubs", "ko": "더빙 두 개 비교", "pt": "Comparar duas dublagens",
                     "es": "Comparar dos doblajes"},
    "compare.title": {"en": "① Paste two Perso share links", "ko": "① Perso 공유 링크 두 개 붙여넣기",
                      "pt": "① Cole dois links de compartilhamento da Perso", "es": "① Pega dos enlaces compartidos de Perso"},
    "compare.caption": {
        "en": "Two or more dubs of the same video (for example versions, or with and without lip-sync). All are "
              "measured the same way, and the tool ranks them, recommends which one to deliver and explains why.",
        "ko": "같은 영상의 더빙을 두 개 이상 넣으세요(예: 여러 버전, 립싱크 있음/없음). 모두 같은 방식으로 측정해 순위를 "
              "매기고, 어느 쪽을 납품할지 추천하며 이유를 설명합니다.",
        "pt": "Duas ou mais dublagens do mesmo vídeo (por exemplo, versões, ou com e sem sincronização labial). Todas "
              "são medidas do mesmo jeito, e a ferramenta as classifica, recomenda qual entregar e explica por quê.",
        "es": "Dos o más doblajes del mismo video (por ejemplo, versiones, o con y sin sincronización labial). Todos se "
              "miden igual, y la herramienta los clasifica, recomienda cuál entregar y explica por qué.",
    },
    "compare.add": {"en": "Add another dub", "ko": "더빙 추가", "pt": "Adicionar outra dublagem", "es": "Añadir otro doblaje"},
    "compare.remove": {"en": "Remove the last", "ko": "마지막 더빙 빼기", "pt": "Remover a última", "es": "Quitar el último"},
    "compare.start": {"en": "Evaluate and compare", "ko": "평가하고 비교하기", "pt": "Avaliar e comparar",
                      "es": "Evaluar y comparar"},
    "compare.same_link": {
        "en": "Both links point to the same Perso project, so the comparison will show the same dub twice.",
        "ko": "두 링크가 같은 Perso 프로젝트를 가리켜 같은 더빙을 두 번 비교하게 됩니다.",
        "pt": "Os dois links apontam para o mesmo projeto Perso, então a comparação mostrará a mesma dublagem duas vezes.",
        "es": "Los dos enlaces apuntan al mismo proyecto de Perso, así que la comparación mostrará el mismo doblaje dos "
              "veces.",
    },
    "problem.compare": {"en": "Paste two valid Perso share links first.", "ko": "먼저 올바른 Perso 공유 링크 두 개를 붙여 넣으세요.",
                        "pt": "Cole primeiro dois links de compartilhamento válidos da Perso.",
                        "es": "Pega primero dos enlaces compartidos válidos de Perso."},
    "compare.download_html": {"en": "Download comparison", "ko": "비교 보고서 다운로드", "pt": "Baixar comparação",
                              "es": "Descargar comparación"},
    "compare.download_html_help": {
        "en": "One HTML file with the recommendation, problem intervals, reasoning and every check side by side.",
        "ko": "추천, 문제 구간, 판단 근거, 전체 항목 비교가 담긴 HTML 파일 하나입니다.",
        "pt": "Um arquivo HTML com a recomendação, os trechos com problemas, a justificativa e todas as verificações.",
        "es": "Un archivo HTML con la recomendación, los tramos con problemas, el razonamiento y todas las comprobaciones.",
    },
    "compare.download_json": {"en": "Download data (JSON)", "ko": "데이터 다운로드(JSON)", "pt": "Baixar dados (JSON)",
                              "es": "Descargar datos (JSON)"},
    "problem.share": {"en": "Paste a Perso share link first.", "ko": "먼저 Perso 공유 링크를 붙여 넣으세요.",
                      "pt": "Primeiro, cole um link de compartilhamento da Perso.",
                      "es": "Primero, pega un enlace compartido de Perso."},

    # ----- stopped / failed jobs -----
    "stopped.title": {"en": "Dubbing stopped", "ko": "더빙이 중지되었습니다", "pt": "Dublagem interrompida",
                      "es": "Doblaje detenido"},
    "failed.title": {"en": "Something went wrong", "ko": "문제가 발생했습니다", "pt": "Algo deu errado",
                     "es": "Algo salió mal"},
    "stopped.during": {"en": "It stopped during: {stage} · after {time}", "ko": "중지된 단계: {stage} · {time} 후",
                       "pt": "Parou durante: {stage} · depois de {time}", "es": "Se detuvo en: {stage} · tras {time}"},
    "back": {"en": "Back to setup", "ko": "설정으로 돌아가기", "pt": "Voltar à configuração",
             "es": "Volver a la configuración"},
    "untracked": {
        "en": "That evaluation is no longer being tracked (the app was restarted). Paste the share link again.",
        "ko": "앱이 다시 시작되어 해당 평가를 더 이상 추적하지 않습니다. 공유 링크를 다시 붙여 넣으세요.",
        "pt": "Essa avaliação não está mais sendo acompanhada (o app foi reiniciado). Cole o link de novo.",
        "es": "Esa evaluación ya no se está siguiendo (la app se reinició). Vuelve a pegar el enlace.",
    },
}

# Report sentences live in their own module to keep this file readable; they share t() and the tests.
from dubeval.report_text import REPORT_TEXT  # noqa: E402

TEXT.update(REPORT_TEXT)
from dubeval.web_text import WEB_TEXT  # noqa: E402

TEXT.update(WEB_TEXT)

# Fixed English progress messages reported by dubeval/ (Perso steps, pipeline and evaluation), translated by text.
MESSAGES = {
    # The web interface's own errors (dubeval/webapp.py).
    "This evaluation can't continue. Start it again from its draft.": {"ko": "이 평가는 이어서 할 수 없습니다. 초안에서 다시 시작하세요.", "pt": "Esta avaliação não pode continuar. Comece de novo pelo rascunho.", "es": "Esta evaluación no puede continuar. Empiézala de nuevo desde su borrador."},
    "That evaluation is gone. It may have been deleted.": {"ko": "그 평가가 없습니다. 삭제되었을 수 있습니다.", "pt": "Essa avaliação não existe mais. Talvez tenha sido apagada.", "es": "Esa evaluación ya no está. Puede que se haya borrado."},
    "That draft is gone. It may have been deleted or started.": {"ko": "그 초안이 없습니다. 삭제되었거나 이미 시작되었을 수 있습니다.", "pt": "Esse rascunho não existe mais. Talvez tenha sido apagado ou iniciado.", "es": "Ese borrador ya no está. Puede que se haya borrado o iniciado."},
    "This draft is too big to keep.": {"ko": "이 초안은 너무 커서 저장할 수 없습니다.", "pt": "Este rascunho é grande demais para ser guardado.", "es": "Este borrador es demasiado grande para guardarlo."},
    "Couldn't delete this evaluation. Close anything that uses its files, then try again.": {"ko": "이 평가를 삭제하지 못했습니다. 이 평가의 파일을 사용하는 프로그램을 닫고 다시 시도하세요.", "pt": "Não foi possível apagar esta avaliação. Feche o que estiver usando os arquivos dela e tente de novo.", "es": "No se pudo borrar esta evaluación. Cierra lo que esté usando sus archivos e inténtalo de nuevo."},
    "No picture.": {"ko": "그림이 없습니다.", "pt": "Sem imagem.", "es": "Sin imagen."},
    "Type a title for this result.": {"ko": "이 결과의 제목을 입력하세요.", "pt": "Digite um título para este resultado.", "es": "Escribe un título para este resultado."},
    "Couldn't read this link. Check it and your internet connection.": {"ko": "이 링크를 읽지 못했습니다. 링크와 인터넷 연결을 확인하세요.", "pt": "Não foi possível ler este link. Confira o link e a sua internet.", "es": "No se pudo leer este enlace. Revisa el enlace y tu conexión a internet."},
    "There's no video at this path on this computer.": {"ko": "이 컴퓨터의 이 경로에 영상이 없습니다.", "pt": "Não há vídeo neste caminho deste computador.", "es": "No hay ningún video en esta ruta de este equipo."},
    "Choose at least one file to export.": {"ko": "내보낼 파일을 하나 이상 고르세요.", "pt": "Escolha pelo menos um arquivo para exportar.", "es": "Elige al menos un archivo para exportar."},
    "The file is larger than 20 GB. Use a smaller or shorter video.": {"ko": "파일이 20 GB보다 큽니다. 더 작거나 짧은 영상을 쓰세요.", "pt": "O arquivo tem mais de 20 GB. Use um vídeo menor ou mais curto.", "es": "El archivo pesa más de 20 GB. Usa un video más pequeño o más corto."},
    "Open the review page from the link printed by `dubeval label`.": {"ko": "`dubeval label`이 출력한 링크로 검토 페이지를 여세요.", "pt": "Abra a página de revisão pelo link mostrado por `dubeval label`.", "es": "Abre la página de revisión con el enlace que muestra `dubeval label`."},
    "That uploaded file is gone. Choose it again.": {"ko": "업로드한 파일이 없어졌습니다. 다시 선택하세요.", "pt": "Esse arquivo enviado não existe mais. Escolha-o de novo.", "es": "Ese archivo subido ya no está. Elígelo de nuevo."},
    "That file is gone. Run the evaluation again.": {"ko": "파일이 없어졌습니다. 평가를 다시 실행하세요.", "pt": "Esse arquivo não existe mais. Rode a avaliação de novo.", "es": "Ese archivo ya no está. Vuelve a hacer la evaluación."},
    "No job with this id.": {"ko": "이 번호의 작업이 없습니다.", "pt": "Não há tarefa com este número.", "es": "No hay ninguna tarea con este número."},
    "No problem interval with this number.": {"ko": "이 번호의 문제 구간이 없습니다.", "pt": "Não há intervalo de problema com este número.", "es": "No hay ningún intervalo de problema con este número."},
    "Open DubEval at http://127.0.0.1.": {"ko": "DubEval은 http://127.0.0.1에서 여세요.", "pt": "Abra o DubEval em http://127.0.0.1.", "es": "Abre DubEval en http://127.0.0.1."},
    "Open DubEval from the link printed by `dubeval web`.": {"ko": "`dubeval web`이 출력한 링크로 DubEval을 여세요.", "pt": "Abra o DubEval pelo link mostrado por `dubeval web`.", "es": "Abre DubEval con el enlace que muestra `dubeval web`."},
    "Compare at most 8 dubs at a time.": {"ko": "한 번에 최대 8개의 더빙만 비교할 수 있습니다.", "pt": "Compare no máximo 8 dublagens por vez.", "es": "Compara como máximo 8 doblajes a la vez."},
    "Compare between 2 and 8 dubs.": {"ko": "더빙은 2개에서 8개까지 비교할 수 있습니다.", "pt": "Compare de 2 a 8 dublagens.", "es": "Compara entre 2 y 8 doblajes."},
    "There are more dub settings than dubs. Give one per dub, in order.": {"ko": "더빙 설정이 더빙보다 많습니다. 더빙마다 하나씩 순서대로 주세요.", "pt": "Há mais configurações de dublagem do que dublagens. Dê uma por dublagem, na ordem.", "es": "Hay más ajustes de doblaje que doblajes. Da uno por doblaje, en orden."},
    "That report is gone (old runs are pruned). Run it again.": {"ko": "보고서가 없어졌습니다(오래된 실행은 정리됨). 다시 실행하세요.", "pt": "Esse relatório não existe mais (execuções antigas são apagadas). Rode de novo.", "es": "Ese informe ya no está (las ejecuciones antiguas se borran). Vuelve a ejecutarlo."},
    "Choose the original video, or paste Perso share links (they include the original).": {"ko": "원본 영상을 고르거나 Perso 공유 링크를 붙여 넣으세요(공유 링크에는 원본이 포함됨).", "pt": "Escolha o vídeo original, ou cole links de compartilhamento da Perso (eles incluem o original).", "es": "Elige el video original, o pega enlaces compartidos de Perso (incluyen el original)."},
    "Use Perso share links for every dub, or files and other links for every dub, not a mix.": {"ko": "모든 더빙에 Perso 공유 링크를 쓰거나, 모든 더빙에 파일과 다른 링크를 쓰세요. 섞어 쓸 수는 없습니다.", "pt": "Use links de compartilhamento da Perso para todas as dublagens, ou arquivos e outros links para todas, sem misturar.", "es": "Usa enlaces compartidos de Perso para todos los doblajes, o archivos y otros enlaces para todos, sin mezclar."},
    "Downloading...": {"ko": "다운로드 중...", "pt": "Baixando...", "es": "Descargando..."},
    "Installing...": {"ko": "설치 중...", "pt": "Instalando...", "es": "Instalando..."},
    "Installed": {"ko": "설치됨", "pt": "Instalado", "es": "Instalado"},
    "The download didn't match its checksum, so it wasn't installed. Try again.": {"ko": "다운로드한 파일의 체크섬이 맞지 않아 설치하지 않았습니다. 다시 시도하세요.", "pt": "O download não confere com a soma de verificação, então não foi instalado. Tente de novo.", "es": "La descarga no coincide con su suma de comprobación, así que no se instaló. Inténtalo de nuevo."},
    "This download isn't available on this computer.": {"ko": "이 다운로드는 이 컴퓨터에서 사용할 수 없습니다.", "pt": "Este download não está disponível neste computador.", "es": "Esta descarga no está disponible en este equipo."},
    "The download failed. Check your internet connection and try again; it continues where it stopped.": {"ko": "다운로드에 실패했습니다. 인터넷 연결을 확인하고 다시 시도하세요. 멈춘 곳부터 이어서 받습니다.", "pt": "O download falhou. Verifique sua conexão com a internet e tente de novo; ele continua de onde parou.", "es": "La descarga falló. Revisa tu conexión a internet e inténtalo de nuevo; continúa donde se detuvo."},
    "The large speech model isn't installed. Get it on the Downloads page.": {"ko": "큰 음성 인식 모델이 설치되지 않았습니다. 다운로드 페이지에서 받으세요.", "pt": "O modelo de fala grande não está instalado. Baixe-o na página Downloads.", "es": "El modelo de habla grande no está instalado. Consíguelo en la página Descargas."},
    "This network blocked DubEval's secure connection: a company network or security software checks it with a certificate this computer doesn't trust. Ask your IT team to allow DubEval, or try another network.": {'ko': '이 네트워크가 DubEval의 보안 연결을 막았습니다. 회사 네트워크나 보안 프로그램이 이 컴퓨터가 신뢰하지 않는 인증서로 연결을 검사하고 있습니다. IT 팀에 DubEval 허용을 요청하거나 다른 네트워크에서 시도하세요.', 'pt': 'Esta rede bloqueou a conexão segura do DubEval: uma rede corporativa ou um software de segurança a verifica com um certificado em que este computador não confia. Peça à sua equipe de TI para liberar o DubEval ou tente outra rede.', 'es': 'Esta red bloqueó la conexión segura de DubEval: una red corporativa o un software de seguridad la revisa con un certificado en el que este equipo no confía. Pide a tu equipo de TI que permita DubEval o prueba otra red.'},
    "This network's proxy didn't let DubEval through. Ask your IT team to allow DubEval, or try another network.": {'ko': '이 네트워크의 프록시가 DubEval의 연결을 허용하지 않았습니다. IT 팀에 DubEval 허용을 요청하거나 다른 네트워크에서 시도하세요.', 'pt': 'O proxy desta rede não deixou o DubEval passar. Peça à sua equipe de TI para liberar o DubEval ou tente outra rede.', 'es': 'El proxy de esta red no dejó pasar a DubEval. Pide a tu equipo de TI que permita DubEval o prueba otra red.'},
    "No download with this name.": {"ko": "이 이름의 다운로드가 없습니다.", "pt": "Não há download com este nome.", "es": "No hay ninguna descarga con este nombre."},
    "Stop the download first.": {"ko": "먼저 다운로드를 멈추세요.", "pt": "Pare o download primeiro.", "es": "Detén la descarga primero."},
    "That doesn't look like an API key. Paste the whole key, with nothing else.": {"ko": "API 키가 아닌 것 같습니다. 다른 내용 없이 키 전체를 붙여 넣으세요.", "pt": "Isso não parece uma chave de API. Cole a chave inteira, sem mais nada.", "es": "Eso no parece una clave de API. Pega la clave completa, sin nada más."},
    "No setting with this name.": {"ko": "이 이름의 설정이 없습니다.", "pt": "Não há configuração com este nome.", "es": "No hay ningún ajuste con este nombre."},
    "No dub with this letter.": {"ko": "이 문자의 더빙이 없습니다.", "pt": "Não há dublagem com esta letra.", "es": "No hay ningún doblaje con esta letra."},
    "This job evaluated one dub; there is no comparison.": {"ko": "이 작업은 더빙 하나만 평가해 비교 결과가 없습니다.", "pt": "Esta tarefa avaliou uma dublagem; não há comparação.", "es": "Esta tarea evaluó un solo doblaje; no hay comparación."},
    "This link is from an earlier launch. Use the new one.": {"ko": "이전 실행의 링크입니다. 새 링크를 사용하세요.", "pt": "Este link é de uma execução anterior. Use o novo.", "es": "Este enlace es de un inicio anterior. Usa el nuevo."},
    # User-facing errors from dubeval/ (share links, downloads, stopped jobs).
    'Paste a Perso share link, for example https://perso.ai/en/share/video-translator?seq=…': {"ko": 'Perso 공유 링크를 붙여 넣으세요. 예: https://perso.ai/en/share/video-translator?seq=…', "pt": 'Cole um link de compartilhamento da Perso, por exemplo https://perso.ai/en/share/video-translator?seq=…', "es": 'Pega un enlace compartido de Perso, por ejemplo https://perso.ai/en/share/video-translator?seq=…'},
    "This doesn't look like a Perso share link. Open the dubbed video in Perso, choose Share, and copy the link (it contains ?seq=).": {"ko": 'Perso 공유 링크가 아닌 것 같습니다. Perso에서 더빙 영상을 열고 공유를 눌러 링크를 복사하세요(?seq=가 포함됨).', "pt": 'Isso não parece um link de compartilhamento da Perso. Abra o vídeo dublado na Perso, escolha Compartilhar e copie o link (ele contém ?seq=).', "es": 'Esto no parece un enlace compartido de Perso. Abre el video doblado en Perso, elige Compartir y copia el enlace (contiene ?seq=).'},
    'The share link is missing its seq=… part. Copy the whole link from Perso again.': {"ko": '공유 링크에 seq=… 부분이 없습니다. Perso에서 링크 전체를 다시 복사하세요.', "pt": 'O link está sem a parte seq=…. Copie o link inteiro da Perso novamente.', "es": 'Al enlace le falta la parte seq=…. Vuelve a copiar el enlace completo desde Perso.'},
    'Sharing is turned off for this Perso project. Ask the owner to turn sharing on, then try again.': {"ko": '이 Perso 프로젝트는 공유가 꺼져 있습니다. 소유자에게 공유를 켜 달라고 요청한 뒤 다시 시도하세요.', "pt": 'O compartilhamento está desligado neste projeto da Perso. Peça ao proprietário para ativá-lo e tente de novo.', "es": 'El uso compartido está desactivado en este proyecto de Perso. Pide al propietario que lo active y vuelve a intentarlo.'},
    "Perso couldn't find a project for this share link. Check that the link is complete and that sharing is still turned on.": {"ko": 'Perso에서 이 공유 링크의 프로젝트를 찾지 못했습니다. 링크가 완전한지, 공유가 켜져 있는지 확인하세요.', "pt": 'A Perso não encontrou um projeto para este link. Confira se o link está completo e se o compartilhamento continua ativo.', "es": 'Perso no encontró un proyecto para este enlace. Comprueba que el enlace está completo y que el uso compartido sigue activo.'},
    'This shared project has no finished dubbed video yet. Wait until Perso finishes, then try again.': {"ko": '이 공유 프로젝트에는 아직 완성된 더빙 영상이 없습니다. Perso 작업이 끝난 뒤 다시 시도하세요.', "pt": 'Este projeto compartilhado ainda não tem vídeo dublado pronto. Espere a Perso terminar e tente de novo.', "es": 'Este proyecto compartido aún no tiene un video doblado terminado. Espera a que Perso termine y vuelve a intentarlo.'},
    'Perso is rate-limiting requests. Wait a minute and try again.': {"ko": 'Perso가 요청을 제한하고 있습니다. 1분 뒤 다시 시도하세요.', "pt": 'A Perso está limitando as solicitações. Espere um minuto e tente de novo.', "es": 'Perso está limitando las solicitudes. Espera un minuto y vuelve a intentarlo.'},
    'Could not reach Perso. Check your internet connection.': {"ko": 'Perso에 연결할 수 없습니다. 인터넷 연결을 확인하세요.', "pt": 'Não foi possível acessar a Perso. Confira sua conexão com a internet.', "es": 'No se pudo contactar con Perso. Revisa tu conexión a internet.'},
    'Perso request failed after retries.': {"ko": '여러 번 시도했지만 Perso 요청이 실패했습니다.', "pt": 'A solicitação à Perso falhou após várias tentativas.', "es": 'La solicitud a Perso falló tras varios intentos.'},
    'Downloading the videos from Perso failed. Try again in a minute.': {"ko": 'Perso에서 영상을 다운로드하지 못했습니다. 1분 뒤 다시 시도하세요.', "pt": 'O download dos vídeos da Perso falhou. Tente de novo em um minuto.', "es": 'No se pudieron descargar los videos de Perso. Vuelve a intentarlo en un minuto.'},
    "The shared project doesn't say which language it was dubbed into.": {"ko": '공유 프로젝트에 더빙 언어 정보가 없습니다.', "pt": 'O projeto compartilhado não informa o idioma da dublagem.', "es": 'El proyecto compartido no indica el idioma del doblaje.'},
    # Files and links (dubeval/inputs.py, dubeval/pipeline.py).
    'This link opens a web page, not a video file. To evaluate videos from YouTube and other pages, install the links extra: pip install "dubeval[links]".': {"ko": '이 링크는 동영상 파일이 아니라 웹 페이지입니다. YouTube 등 웹 페이지의 영상을 평가하려면 links 추가 기능을 설치하세요: pip install "dubeval[links]".', "pt": 'Este link abre uma página da web, não um arquivo de vídeo. Para avaliar vídeos do YouTube e de outras páginas, instale o extra links: pip install "dubeval[links]".', "es": 'Este enlace abre una página web, no un archivo de video. Para evaluar videos de YouTube y otras páginas, instala el extra links: pip install "dubeval[links]".'},
    "The video couldn't be downloaded. Check the link and your internet connection, then try again.": {"ko": '영상을 다운로드하지 못했습니다. 링크와 인터넷 연결을 확인한 뒤 다시 시도하세요.', "pt": 'Não foi possível baixar o vídeo. Confira o link e sua conexão com a internet e tente de novo.', "es": 'No se pudo descargar el video. Revisa el enlace y tu conexión a internet, y vuelve a intentarlo.'},
    'Links must start with http:// or https://.': {"ko": '링크는 http:// 또는 https://로 시작해야 합니다.', "pt": 'Os links devem começar com http:// ou https://.', "es": 'Los enlaces deben empezar por http:// o https://.'},
    "The dub's language couldn't be detected. Pass it with --target-lang (for example ko).": {"ko": '더빙 언어를 감지하지 못했습니다. --target-lang 옵션으로 지정하세요(예: ko).', "pt": 'Não foi possível detectar o idioma da dublagem. Informe-o com --target-lang (por exemplo, ko).', "es": 'No se pudo detectar el idioma del doblaje. Indícalo con --target-lang (por ejemplo, ko).'},
    'No speech recognizer is installed. Install faster-whisper (pip install faster-whisper).': {"ko": '음성 인식기가 설치되어 있지 않습니다. faster-whisper를 설치하세요(pip install faster-whisper).', "pt": 'Nenhum reconhecedor de fala está instalado. Instale o faster-whisper (pip install faster-whisper).', "es": 'No hay ningún reconocedor de voz instalado. Instala faster-whisper (pip install faster-whisper).'},
    "The original video can't be read. Check that it's a video or audio file and not damaged.": {"ko": '원본 영상을 읽을 수 없습니다. 영상 또는 오디오 파일인지, 손상되지 않았는지 확인하세요.', "pt": 'Não foi possível ler o vídeo original. Confira se é um arquivo de vídeo ou áudio e se não está danificado.', "es": 'No se puede leer el video original. Comprueba que sea un archivo de video o audio y que no esté dañado.'},
    "The dubbed video can't be read. Check that it's a video or audio file and not damaged.": {"ko": '더빙 영상을 읽을 수 없습니다. 영상 또는 오디오 파일인지, 손상되지 않았는지 확인하세요.', "pt": 'Não foi possível ler o vídeo dublado. Confira se é um arquivo de vídeo ou áudio e se não está danificado.', "es": 'No se puede leer el video doblado. Comprueba que sea un archivo de video o audio y que no esté dañado.'},
    'The original video has no audio track, so there is no speech to evaluate.': {"ko": '원본 영상에 오디오 트랙이 없어 평가할 음성이 없습니다.', "pt": 'O vídeo original não tem faixa de áudio, então não há fala para avaliar.', "es": 'El video original no tiene pista de audio, así que no hay voz que evaluar.'},
    'The dubbed video has no audio track, so there is no speech to evaluate.': {"ko": '더빙 영상에 오디오 트랙이 없어 평가할 음성이 없습니다.', "pt": 'O vídeo dublado não tem faixa de áudio, então não há fala para avaliar.', "es": 'El video doblado no tiene pista de audio, así que no hay voz que evaluar.'},
    'The original subtitles must be an .srt or .vtt file.': {"ko": '원본 자막은 .srt 또는 .vtt 파일이어야 합니다.', "pt": 'As legendas originais devem ser um arquivo .srt ou .vtt.', "es": 'Los subtítulos originales deben ser un archivo .srt o .vtt.'},
    'The dub subtitles must be an .srt or .vtt file.': {"ko": '더빙 자막은 .srt 또는 .vtt 파일이어야 합니다.', "pt": 'As legendas da dublagem devem ser um arquivo .srt ou .vtt.', "es": 'Los subtítulos del doblaje deben ser un archivo .srt o .vtt.'},
    "The original subtitle file has no timed lines. Check that it's a valid .srt or .vtt file.": {"ko": '원본 자막 파일에 시간이 지정된 줄이 없습니다. 올바른 .srt 또는 .vtt 파일인지 확인하세요.', "pt": 'O arquivo de legendas original não tem linhas com tempo. Confira se é um .srt ou .vtt válido.', "es": 'El archivo de subtítulos original no tiene líneas con tiempo. Comprueba que sea un .srt o .vtt válido.'},
    "The dub subtitle file has no timed lines. Check that it's a valid .srt or .vtt file.": {"ko": '더빙 자막 파일에 시간이 지정된 줄이 없습니다. 올바른 .srt 또는 .vtt 파일인지 확인하세요.', "pt": 'O arquivo de legendas da dublagem não tem linhas com tempo. Confira se é um .srt ou .vtt válido.', "es": 'El archivo de subtítulos del doblaje no tiene líneas con tiempo. Comprueba que sea un .srt o .vtt válido.'},
    "These look like different videos: their pictures don't match, so comparing them would be meaningless. Check that you chose the right files, or run again with --allow-different-videos if you're sure they belong together.": {"ko": '서로 다른 영상으로 보입니다. 화면이 일치하지 않아 비교하는 의미가 없습니다. 파일을 올바르게 골랐는지 확인하거나, 같은 영상이 확실하면 --allow-different-videos 옵션으로 다시 실행하세요.', "pt": 'Estes parecem ser vídeos diferentes: as imagens não coincidem, então compará-los não faria sentido. Confira se escolheu os arquivos certos ou execute de novo com --allow-different-videos se tiver certeza de que combinam.', "es": 'Parecen videos distintos: las imágenes no coinciden, así que compararlos no tendría sentido. Comprueba que elegiste los archivos correctos o vuelve a ejecutar con --allow-different-videos si estás seguro de que van juntos.'},
    "Checking that both files are the same video...": {"ko": "두 파일이 같은 영상인지 확인 중...", "pt": "Verificando se os dois arquivos são o mesmo vídeo...", "es": "Comprobando que ambos archivos sean el mismo video..."},
    "The dub type must be ai_clone, ai_stock or human.": {"ko": '더빙 유형은 ai_clone, ai_stock, human 중 하나여야 합니다.', "pt": 'O tipo de dublagem deve ser ai_clone, ai_stock ou human.', "es": 'El tipo de doblaje debe ser ai_clone, ai_stock o human.'},
    "Comparing the meaning of each line...": {"ko": "대사별 의미 비교 중...", "pt": "Comparando o sentido de cada fala...", "es": "Comparando el sentido de cada frase..."},
    "Reading the sound of both videos...": {"ko": "두 영상의 소리를 읽는 중...", "pt": "Lendo o som dos dois vídeos...", "es": "Leyendo el sonido de los dos videos..."},
    "Reading the picture of both videos...": {"ko": "두 영상의 화면을 읽는 중...", "pt": "Lendo a imagem dos dois vídeos...", "es": "Leyendo la imagen de los dos videos..."},
    "Matching the two videos...": {"ko": "두 영상을 맞춰 보는 중...", "pt": "Comparando os dois vídeos...", "es": "Comparando los dos videos..."},
    "Checking the files...": {"ko": "파일 확인 중...", "pt": "Verificando os arquivos...", "es": "Comprobando los archivos..."},
    "Getting the original video...": {"ko": "원본 영상 가져오는 중...", "pt": "Obtendo o vídeo original...", "es": "Obteniendo el video original..."},
    "Getting the dubbed video...": {"ko": "더빙 영상 가져오는 중...", "pt": "Obtendo o vídeo dublado...", "es": "Obteniendo el video doblado..."},
    "Detecting the dub's language...": {"ko": "더빙 언어 감지 중...", "pt": "Detectando o idioma da dublagem...", "es": "Detectando el idioma del doblaje..."},
    'You stopped this job.': {"ko": '이 작업을 중지했습니다.', "pt": 'Você interrompeu este trabalho.', "es": 'Detuviste este trabajo.'},
    "Starting...": {"ko": "시작하는 중...", "pt": "Iniciando...", "es": "Iniciando..."},
    "Finished": {"ko": "완료", "pt": "Concluído", "es": "Terminado"},
    "Downloading the dubbed video...": {"ko": "더빙된 영상 다운로드 중...", "pt": "Baixando o vídeo dublado...",
                                        "es": "Descargando el video doblado..."},
    "Loading the speech recognition model...": {"ko": "음성 인식 모델 불러오는 중...",
                                                "pt": "Carregando o modelo de reconhecimento de fala...",
                                                "es": "Cargando el modelo de reconocimiento de voz..."},
    "Extracting audio from both videos...": {"ko": "두 영상에서 오디오 추출 중...",
                                             "pt": "Extraindo o áudio dos dois vídeos...",
                                             "es": "Extrayendo el audio de ambos videos..."},
    "Measuring loudness and silence...": {"ko": "음량과 무음 측정 중...", "pt": "Medindo volume e silêncio...",
                                          "es": "Midiendo volumen y silencio..."},
    "Transcribing the original speech...": {"ko": "원본 음성 받아쓰는 중...", "pt": "Transcrevendo a fala original...",
                                            "es": "Transcribiendo el habla original..."},
    "Transcribing the dubbed speech...": {"ko": "더빙 음성 받아쓰는 중...", "pt": "Transcrevendo a fala dublada...",
                                          "es": "Transcribiendo el habla doblada..."},
    "Analyzing lip movement in the dubbed video...": {"ko": "더빙 영상의 입 움직임 분석 중...",
                                                      "pt": "Analisando o movimento dos lábios no vídeo dublado...",
                                                      "es": "Analizando el movimiento de los labios en el video doblado..."},
    "An evaluation or a download is running. Clear the downloads when it has finished.": {
        "ko": "평가나 다운로드가 진행 중입니다. 끝난 뒤에 비우세요.",
        "pt": "Uma avaliação ou um download está em andamento. Limpe os downloads quando terminar.",
        "es": "Hay una evaluación o una descarga en curso. Vacía las descargas cuando termine."},
    "Checking lip sync in both videos...": {"ko": "두 영상의 립싱크 확인 중...",
                                            "pt": "Verificando a sincronia labial nos dois vídeos...",
                                            "es": "Comprobando la sincronía labial en los dos videos..."},
    "Analyzing lip movement in the original video...": {"ko": "원본 영상의 입 움직임 분석 중...",
                                                        "pt": "Analisando o movimento dos lábios no vídeo original...",
                                                        "es": "Analizando el movimiento de los labios en el video original..."},
    "Done": {"ko": "완료", "pt": "Pronto", "es": "Listo"},
    "Reading the shared Perso project...": {"ko": "공유된 Perso 프로젝트 읽는 중...",
                                            "pt": "Lendo o projeto compartilhado da Perso...",
                                            "es": "Leyendo el proyecto compartido de Perso..."},
    "Downloading the original video...": {"ko": "원본 영상 다운로드 중...", "pt": "Baixando o vídeo original...",
                                          "es": "Descargando el video original..."},
    "Checking which language the dub is in...": {"ko": "더빙 언어 확인 중...", "pt": "Verificando o idioma da dublagem...",
                                                 "es": "Comprobando el idioma del doblaje..."},
    "Rating the voice quality of both tracks...": {"ko": "두 트랙의 목소리 품질 평가 중...",
                                                   "pt": "Avaliando a qualidade da voz das duas faixas...",
                                                   "es": "Calificando la calidad de la voz de ambas pistas..."},
    "Comparing the dub voice with the original speakers...": {"ko": "더빙 목소리를 원래 화자와 비교 중...",
                                                              "pt": "Comparando a voz da dublagem com os falantes originais...",
                                                              "es": "Comparando la voz del doblaje con los hablantes originales..."},
    "The app restarted while this job was running, so it stopped. Start it again.": {
        "ko": "작업 도중 앱이 다시 시작되어 작업이 중단됐습니다. 다시 시작하세요.",
        "pt": "O app reiniciou enquanto esta tarefa rodava, então ela parou. Comece de novo.",
        "es": "La app se reinició mientras esta tarea se ejecutaba, así que se detuvo. Vuelve a empezarla."},
    "Comparing the dubs...": {"ko": "더빙 비교 중...", "pt": "Comparando as dublagens...",
                              "es": "Comparando los doblajes..."},
    "This share link has no original video. Pass the original with --original <file or URL> (command line), then try again.": {
        "ko": "이 공유 링크에는 원본 영상이 없습니다. 명령줄에서 --original <파일 또는 URL>로 원본을 지정한 뒤 다시 시도하세요.",
        "pt": "Este link não tem o vídeo original. Informe o original com --original <arquivo ou URL> (linha de comando) "
              "e tente de novo.",
        "es": "Este enlace no tiene el video original. Indica el original con --original <archivo o URL> (línea de "
              "comandos) y vuelve a intentarlo."},
    "Checking the dub's language part by part...": {"ko": "더빙 언어를 구간별로 확인 중...",
                                                    "pt": "Verificando o idioma da dublagem por trechos...",
                                                    "es": "Comprobando el idioma del doblaje por partes..."},
    "Comparing when each track speaks...": {"ko": "각 트랙이 말하는 구간 비교 중...",
                                            "pt": "Comparando quando cada faixa fala...",
                                            "es": "Comparando cuándo habla cada pista..."},
    "Checking the translation...": {"ko": "번역 검토 중...", "pt": "Verificando a tradução...",
                                    "es": "Revisando la traducción..."},
    "Writing the report...": {"ko": "보고서 작성 중...", "pt": "Escrevendo o relatório...", "es": "Escribiendo el informe..."},
}


def t(key: str, lang: str, /, **values) -> str:
    """The text for key in lang (English if that translation is missing), with {placeholders} filled in."""
    entry = TEXT[key]
    text = entry.get(lang) or entry[DEFAULT_UI_LANGUAGE]
    return text.format(**values) if values else text


def translate_message(message: str, lang: str) -> str:
    """Translates a fixed progress message from dubeval/; anything unknown is returned unchanged."""
    return (MESSAGES.get(message) or {}).get(lang, message)


def pick_ui_language(locale: Optional[str]) -> str:
    """The interface language for a browser locale such as ko-KR or pt-BR; English if it isn't one of ours."""
    code = (locale or "").split("-")[0].lower()
    return code if code in UI_LANGUAGES else DEFAULT_UI_LANGUAGE
