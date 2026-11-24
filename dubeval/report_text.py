"""Every sentence of the quality report in English, Korean, Portuguese (Brazil) and Spanish.

Keys start with "r."; dubeval/i18n.py merges them into TEXT, so tests/test_i18n.py checks that every entry has all four
languages with the same {placeholders}. Counted texts come in _one / _many pairs (see report._pl).
"""

REPORT_TEXT = {
    # ----- measure names -----
    "r.m.length_match": {"en": "Length match", "ko": "길이 일치", "pt": "Duração total", "es": "Duración total"},
    "r.m.loudness_match": {"en": "Loudness match", "ko": "음량 일치", "pt": "Volume", "es": "Volumen"},
    "r.m.silence": {"en": "Silence", "ko": "무음", "pt": "Silêncio", "es": "Silencio"},
    "r.m.noise": {"en": "Noise", "ko": "잡음", "pt": "Ruído", "es": "Ruido"},
    "r.m.clipping": {"en": "Distortion", "ko": "소리 왜곡", "pt": "Distorção", "es": "Distorsión"},
    "r.m.speech_rate": {"en": "Speaking pace", "ko": "말 속도", "pt": "Ritmo da fala", "es": "Ritmo del habla"},
    "r.m.language": {"en": "Dub language", "ko": "더빙 언어", "pt": "Idioma da dublagem", "es": "Idioma del doblaje"},
    "r.m.clarity": {"en": "Voice clarity", "ko": "음성 명료도", "pt": "Clareza da voz", "es": "Claridad de la voz"},
    "r.m.script_accuracy": {"en": "Matches your script", "ko": "내 스크립트 일치", "pt": "Fidelidade ao seu roteiro",
                            "es": "Coincide con tu guion"},
    "r.m.speech_overlap": {"en": "Speech timing", "ko": "발화 타이밍", "pt": "Momento da fala", "es": "Momento del habla"},
    "r.m.speech_offsets": {"en": "Start and end of speech", "ko": "말의 시작과 끝", "pt": "Início e fim da fala",
                           "es": "Inicio y fin del habla"},
    "r.m.translation_check": {"en": "Translation check", "ko": "번역 검토", "pt": "Verificação da tradução",
                              "es": "Revisión de la traducción"},
    "r.m.meaning": {"en": "Meaning preserved", "ko": "의미 보존", "pt": "Sentido preservado", "es": "Sentido conservado"},
    "r.m.completeness": {"en": "Missing or added content", "ko": "누락·추가된 내용", "pt": "Conteúdo faltando ou a mais",
                         "es": "Contenido que falta o sobra"},
    "r.m.voice_quality": {"en": "Voice quality", "ko": "목소리 품질", "pt": "Qualidade da voz", "es": "Calidad de la voz"},
    "r.m.voice_similarity": {"en": "Voice similarity", "ko": "목소리 유사도", "pt": "Semelhança da voz",
                             "es": "Parecido de la voz"},
    "r.m.names_numbers": {"en": "Names and numbers", "ko": "이름과 숫자", "pt": "Nomes e números", "es": "Nombres y números"},
    "r.m.mistranslations": {"en": "Mistranslations", "ko": "오역", "pt": "Erros de tradução", "es": "Errores de traducción"},
    "r.m.file_check": {"en": "Video file", "ko": "영상 파일", "pt": "Arquivo de vídeo", "es": "Archivo de video"},
    "r.m.lip_sync": {"en": "Lip sync", "ko": "립싱크", "pt": "Sincronia labial", "es": "Sincronía labial"},

    # ----- length -----
    "r.length.same": {
        "en": "The dub is exactly as long as the original ({dub} s and {orig} s). Nothing is cut off at the end and no "
              "silence was added.",
        "ko": "더빙이 원본과 길이가 정확히 같습니다({dub}초, {orig}초). 끝부분이 잘리거나 무음이 추가되지 않았습니다.",
        "pt": "A dublagem tem exatamente a mesma duração do original ({dub} s e {orig} s). Nada foi cortado no final e "
              "nenhum silêncio foi adicionado.",
        "es": "El doblaje dura exactamente lo mismo que el original ({dub} s y {orig} s). No se corta nada al final ni "
              "se añadió silencio.",
    },
    "r.length.longer_ok": {
        "en": "The dub is {diff} s longer than the original ({pct}%). That is small enough that viewers won't notice.",
        "ko": "더빙이 원본보다 {diff}초 깁니다({pct}%). 시청자가 알아차리지 못할 만큼 작은 차이입니다.",
        "pt": "A dublagem é {diff} s mais longa que o original ({pct}%). A diferença é pequena demais para ser notada.",
        "es": "El doblaje dura {diff} s más que el original ({pct}%). La diferencia es tan pequeña que no se nota.",
    },
    "r.length.shorter_ok": {
        "en": "The dub is {diff} s shorter than the original ({pct}%). That is small enough that viewers won't notice.",
        "ko": "더빙이 원본보다 {diff}초 짧습니다({pct}%). 시청자가 알아차리지 못할 만큼 작은 차이입니다.",
        "pt": "A dublagem é {diff} s mais curta que o original ({pct}%). A diferença é pequena demais para ser notada.",
        "es": "El doblaje dura {diff} s menos que el original ({pct}%). La diferencia es tan pequeña que no se nota.",
    },
    "r.length.longer_bad": {
        "en": "The dub is {diff} s longer than the original ({pct}%). The end of the dubbed speech may be cut off, or the "
              "voice may run past the picture. Watch the last seconds.",
        "ko": "더빙이 원본보다 {diff}초 깁니다({pct}%). 더빙 음성의 끝이 잘리거나 화면보다 길게 이어질 수 있습니다. "
              "마지막 몇 초를 확인하세요.",
        "pt": "A dublagem é {diff} s mais longa que o original ({pct}%). O final da fala dublada pode ser cortado ou "
              "passar do vídeo. Assista aos últimos segundos.",
        "es": "El doblaje dura {diff} s más que el original ({pct}%). El final del habla doblada puede cortarse o "
              "pasar del video. Mira los últimos segundos.",
    },
    "r.length.shorter_bad": {
        "en": "The dub is {diff} s shorter than the original ({pct}%). The speech may finish early and leave silence at "
              "the end, or part of the content may be missing. Watch the last seconds.",
        "ko": "더빙이 원본보다 {diff}초 짧습니다({pct}%). 말이 일찍 끝나 끝부분에 무음이 남거나 내용 일부가 빠졌을 수 "
              "있습니다. 마지막 몇 초를 확인하세요.",
        "pt": "A dublagem é {diff} s mais curta que o original ({pct}%). A fala pode terminar antes e deixar silêncio no "
              "final, ou parte do conteúdo pode faltar. Assista aos últimos segundos.",
        "es": "El doblaje dura {diff} s menos que el original ({pct}%). El habla puede terminar antes y dejar silencio al "
              "final, o puede faltar parte del contenido. Mira los últimos segundos.",
    },
    "r.length.na": {
        "en": "The original video has no audio, so the length couldn't be compared.",
        "ko": "원본 영상에 오디오가 없어 길이를 비교할 수 없습니다.",
        "pt": "O vídeo original não tem áudio, então a duração não pôde ser comparada.",
        "es": "El video original no tiene audio, así que no se pudo comparar la duración.",
    },
    "r.g.length": {
        "en": "Good when the lengths differ by at most {good}%, Needs review up to {check}%, otherwise Poor.",
        "ko": "길이 차이가 {good}% 이하면 좋음, {check}% 이하면 검토 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se as durações diferem até {good}%, Precisa de revisão até {check}%, acima disso Ruim.",
        "es": "Bien si las duraciones difieren como mucho un {good}%, Necesita revisión hasta un {check}%, si no Deficiente.",
    },

    # ----- loudness -----
    "r.loud.same": {
        "en": "The dub is as loud as the original, so viewers won't need to change the volume.",
        "ko": "더빙이 원본과 같은 음량이라 시청자가 볼륨을 바꿀 필요가 없습니다.",
        "pt": "A dublagem tem o mesmo volume do original, então o público não precisa ajustar o volume.",
        "es": "El doblaje suena igual de fuerte que el original, así que no hace falta cambiar el volumen.",
    },
    "r.loud.louder_ok": {
        "en": "The dub is slightly louder than the original ({db} dB). A difference this small is hard to hear.",
        "ko": "더빙이 원본보다 조금 큽니다({db} dB). 이 정도 차이는 귀로 거의 구분되지 않습니다.",
        "pt": "A dublagem está um pouco mais alta que o original ({db} dB). Uma diferença tão pequena quase não se ouve.",
        "es": "El doblaje suena un poco más fuerte que el original ({db} dB). Una diferencia tan pequeña casi no se oye.",
    },
    "r.loud.quieter_ok": {
        "en": "The dub is slightly quieter than the original ({db} dB). A difference this small is hard to hear.",
        "ko": "더빙이 원본보다 조금 작습니다({db} dB). 이 정도 차이는 귀로 거의 구분되지 않습니다.",
        "pt": "A dublagem está um pouco mais baixa que o original ({db} dB). Uma diferença tão pequena quase não se ouve.",
        "es": "El doblaje suena un poco más bajo que el original ({db} dB). Una diferencia tan pequeña casi no se oye.",
    },
    "r.loud.louder_bad": {
        "en": "The dub is {db} dB louder than the original. Viewers will likely notice the jump in volume and may have "
              "to turn it down.",
        "ko": "더빙이 원본보다 {db} dB 큽니다. 시청자가 소리가 커진 것을 느끼고 볼륨을 줄여야 할 수 있습니다.",
        "pt": "A dublagem está {db} dB mais alta que o original. O público provavelmente vai notar o salto de volume e "
              "precisar abaixá-lo.",
        "es": "El doblaje suena {db} dB más fuerte que el original. Es probable que se note el salto de volumen y haya "
              "que bajarlo.",
    },
    "r.loud.quieter_bad": {
        "en": "The dub is {db} dB quieter than the original. Viewers will likely notice the drop in volume and may have "
              "to turn it up.",
        "ko": "더빙이 원본보다 {db} dB 작습니다. 시청자가 소리가 작아진 것을 느끼고 볼륨을 키워야 할 수 있습니다.",
        "pt": "A dublagem está {db} dB mais baixa que o original. O público provavelmente vai notar a queda de volume e "
              "precisar aumentá-lo.",
        "es": "El doblaje suena {db} dB más bajo que el original. Es probable que se note la bajada de volumen y haya "
              "que subirlo.",
    },
    "r.loud.na": {
        "en": "The original video is silent, so the loudness couldn't be compared.",
        "ko": "원본 영상이 무음이라 음량을 비교할 수 없습니다.",
        "pt": "O vídeo original está em silêncio, então o volume não pôde ser comparado.",
        "es": "El video original está en silencio, así que no se pudo comparar el volumen.",
    },
    "r.g.loudness": {
        "en": "Good within {good} dB of the original, Needs review within {check} dB, otherwise Poor. About 1 dB is the "
              "smallest change most people can hear.",
        "ko": "원본과의 차이가 {good} dB 이내면 좋음, {check} dB 이내면 검토 필요, 그보다 크면 미흡입니다. 대부분의 "
              "사람은 약 1 dB부터 차이를 느낍니다.",
        "pt": "Bom até {good} dB de diferença do original, Precisa de revisão até {check} dB, acima disso Ruim. Cerca de 1 dB é a "
              "menor mudança que a maioria das pessoas percebe.",
        "es": "Bien hasta {good} dB de diferencia con el original, Necesita revisión hasta {check} dB, si no Deficiente. Cerca de "
              "1 dB es el cambio más pequeño que la mayoría percibe.",
    },

    # ----- silence -----
    "r.silence.ok": {
        "en": "The dub has about as much silence as the original ({orig} → {dub} of the time), so there are no "
              "unexpected gaps in the voice.",
        "ko": "더빙의 무음 비율이 원본과 비슷해({orig} → {dub}) 목소리가 갑자기 끊기는 곳이 없습니다.",
        "pt": "A dublagem tem quase o mesmo silêncio que o original ({orig} → {dub} do tempo), então não há pausas "
              "inesperadas na voz.",
        "es": "El doblaje tiene casi el mismo silencio que el original ({orig} → {dub} del tiempo), así que no hay pausas "
              "inesperadas en la voz.",
    },
    "r.silence.bad": {
        "en": "The dub is silent much more often than the original ({orig} → {dub} of the time, {pts} points more). "
              "Look for places where the voice drops out.",
        "ko": "더빙이 원본보다 훨씬 자주 조용합니다({orig} → {dub}, {pts}%p 증가). 목소리가 끊기는 곳이 있는지 확인하세요.",
        "pt": "A dublagem fica em silêncio com muito mais frequência que o original ({orig} → {dub} do tempo, {pts} pontos "
              "a mais). Procure trechos em que a voz some.",
        "es": "El doblaje está en silencio mucho más a menudo que el original ({orig} → {dub} del tiempo, {pts} puntos "
              "más). Busca partes donde la voz desaparece.",
    },
    "r.g.silence": {
        "en": "Good when the dub is silent at most {good} points more of the time than the original, Needs review up to "
              "{check} points, otherwise Poor.",
        "ko": "더빙의 무음 비율이 원본보다 {good}%p 이하로 많으면 좋음, {check}%p 이하면 검토 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se a dublagem fica em silêncio no máximo {good} pontos a mais que o original, Precisa de revisão até {check} "
              "pontos, acima disso Ruim.",
        "es": "Bien si el doblaje está en silencio como mucho {good} puntos más que el original, Necesita revisión hasta {check} "
              "puntos, si no Deficiente.",
    },

    # ----- clipping -----
    "r.noise.ok": {
        "en": "No burst of noise: the dub doesn't fill with hiss or static the original doesn't have.",
        "ko": "잡음 구간이 없습니다. 더빙에 원본에 없는 쉿 소리나 지직거림이 끼지 않았습니다.",
        "pt": "Sem trechos de ruído: a dublagem não se enche de chiado ou estática que o original não tem.",
        "es": "Sin ráfagas de ruido: el doblaje no se llena de siseo o estática que el original no tenga.",
    },
    "r.noise.check_one": {
        "en": "The dub fills with noise at {n} moment, a hiss or static the original doesn't have. Listen there.",
        "ko": "더빙에 원본에 없는 잡음(쉿 소리, 지직거림)이 끼는 구간이 {n}곳 있습니다. 그 부분을 들어 보세요.",
        "pt": "A dublagem se enche de ruído em {n} momento, um chiado ou estática que o original não tem. Ouça esse trecho.",
        "es": "El doblaje se llena de ruido en {n} momento, un siseo o estática que el original no tiene. Escucha ese punto.",
    },
    "r.noise.check_many": {
        "en": "The dub fills with noise at {n} moments, a hiss or static the original doesn't have. Listen there.",
        "ko": "더빙에 원본에 없는 잡음(쉿 소리, 지직거림)이 끼는 구간이 {n}곳 있습니다. 그 부분들을 들어 보세요.",
        "pt": "A dublagem se enche de ruído em {n} momentos, um chiado ou estática que o original não tem. Ouça esses trechos.",
        "es": "El doblaje se llena de ruido en {n} momentos, un siseo o estática que el original no tiene. Escucha esos puntos.",
    },
    "r.noise.display_one": {"en": "1 found", "ko": "1곳", "pt": "1 encontrado", "es": "1 encontrado"},
    "r.noise.display_many": {"en": "{n} found", "ko": "{n}곳", "pt": "{n} encontrados", "es": "{n} encontrados"},
    "r.g.noise": {
        "en": "Compares how far the dub fills with noise against its own usual level and the original at the same moment. "
              "Needs review when it rises {rise} dB or more for {sec} s or longer, otherwise Good; never Poor. Hum, buzz and crackle "
              "aren't detected.",
        "ko": "더빙에 잡음이 얼마나 차는지를 더빙의 평소 수준 및 같은 순간의 원본과 비교합니다. {rise} dB 이상 높아진 상태가 {sec}초 "
              "이상 이어지면 검토 필요, 아니면 좋음이며 미흡은 없습니다. 웅웅거림, 윙윙거림, 탁탁거림은 찾지 못합니다.",
        "pt": "Compara o quanto a dublagem se enche de ruído com o nível habitual dela e com o original no mesmo momento. "
              "Precisa de revisão quando sobe {rise} dB ou mais por {sec} s ou mais, senão Bom; nunca Ruim. Zumbido, vibração e estalos "
              "não são detectados.",
        "es": "Compara cuánto se llena de ruido el doblaje con su nivel habitual y con el original en el mismo momento. "
              "Necesita revisión cuando sube {rise} dB o más durante {sec} s o más; si no, Bien; nunca Deficiente. El zumbido, la vibración "
              "y los chasquidos no se detectan.",
    },
    "r.clip.ok": {
        "en": "The dub's audio never hits the maximum level, so there is no crackling or distortion.",
        "ko": "더빙 오디오가 최대 음량 한계에 닿지 않아 지직거림이나 왜곡이 없습니다.",
        "pt": "O áudio da dublagem nunca atinge o nível máximo, então não há chiado nem distorção.",
        "es": "El audio del doblaje nunca llega al nivel máximo, así que no hay crujidos ni distorsión.",
    },
    "r.clip.bad": {
        "en": "{pct}% of the dub's audio hits the maximum level. That can sound like crackling or distortion; listen to "
              "the loud parts.",
        "ko": "더빙 오디오의 {pct}%가 최대 음량 한계에 닿습니다. 지직거리거나 찌그러진 소리로 들릴 수 있으니 큰 소리 "
              "부분을 들어 보세요.",
        "pt": "{pct}% do áudio da dublagem atinge o nível máximo. Isso pode soar como chiado ou distorção; ouça as partes "
              "mais altas.",
        "es": "El {pct}% del audio del doblaje llega al nivel máximo. Puede sonar a crujidos o distorsión; escucha las "
              "partes más fuertes.",
    },
    "r.g.clipping": {
        "en": "Good when at most {good}% of the audio hits the maximum level, Needs review up to {check}%, otherwise Poor.",
        "ko": "최대 음량에 닿는 비율이 {good}% 이하면 좋음, {check}% 이하면 검토 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se no máximo {good}% do áudio atinge o nível máximo, Precisa de revisão até {check}%, acima disso Ruim.",
        "es": "Bien si como mucho el {good}% del audio llega al nivel máximo, Necesita revisión hasta el {check}%, si no Deficiente.",
    },

    # ----- speaking pace -----
    "r.pace.good": {
        "en": "The dub speaks at a natural pace ({rate}). The translation fits the time available.",
        "ko": "더빙이 자연스러운 속도로 말합니다({rate}). 번역문이 주어진 시간에 잘 맞습니다.",
        "pt": "A dublagem fala em um ritmo natural ({rate}). A tradução cabe no tempo disponível.",
        "es": "El doblaje habla a un ritmo natural ({rate}). La traducción cabe en el tiempo disponible.",
    },
    "r.pace.check": {
        "en": "The dub speaks quickly ({rate}). The translation may be a little long for the time available, so some "
              "lines may sound hurried.",
        "ko": "더빙이 빠르게 말합니다({rate}). 번역문이 주어진 시간보다 조금 길어서 일부 문장이 급하게 들릴 수 있습니다.",
        "pt": "A dublagem fala rápido ({rate}). A tradução pode estar um pouco longa para o tempo disponível, então algumas "
              "falas podem soar apressadas.",
        "es": "El doblaje habla rápido ({rate}). La traducción puede ser algo larga para el tiempo disponible, así que "
              "algunas frases pueden sonar apresuradas.",
    },
    "r.pace.poor": {
        "en": "The dub speaks very fast ({rate}). The translation is probably too long for the time available, so lines "
              "will sound rushed. A shorter translation would help.",
        "ko": "더빙이 매우 빠르게 말합니다({rate}). 번역문이 주어진 시간에 비해 너무 길어 문장이 쫓기듯 들릴 것입니다. "
              "번역을 더 짧게 하면 좋아집니다.",
        "pt": "A dublagem fala muito rápido ({rate}). A tradução provavelmente é longa demais para o tempo disponível, "
              "então as falas vão soar corridas. Uma tradução mais curta ajudaria.",
        "es": "El doblaje habla muy rápido ({rate}). La traducción probablemente es demasiado larga para el tiempo "
              "disponible, así que las frases sonarán atropelladas. Una traducción más corta ayudaría.",
    },
    "r.pace.no_rule": {
        "en": "There is no speaking-pace rule for {lang} yet, so the pace ({rate}) is not graded.",
        "ko": "아직 이 언어({lang})의 말 속도 기준이 없어 속도({rate})를 평가하지 않습니다.",
        "pt": "Ainda não há regra de ritmo de fala para {lang}, então o ritmo ({rate}) não é avaliado.",
        "es": "Todavía no hay una regla de ritmo para {lang}, así que el ritmo ({rate}) no se califica.",
    },
    "r.g.pace": {
        "en": "Good up to {good} {unit}, Needs review up to {check} {unit}, otherwise Poor (faster than people normally speak).",
        "ko": "{good} {unit}까지 좋음, {check} {unit}까지 검토 필요, 그보다 빠르면 미흡입니다(보통 사람이 말하는 속도보다 빠름).",
        "pt": "Bom até {good} {unit}, Precisa de revisão até {check} {unit}, acima disso Ruim (mais rápido do que se fala "
              "normalmente).",
        "es": "Bien hasta {good} {unit}, Necesita revisión hasta {check} {unit}, si no Deficiente (más rápido de lo que se habla "
              "normalmente).",
    },
    "r.no_speech": {
        "en": "No speech was recognised in the dub, so this couldn't be measured.",
        "ko": "더빙에서 말소리가 인식되지 않아 측정할 수 없습니다.",
        "pt": "Nenhuma fala foi reconhecida na dublagem, então isso não pôde ser medido.",
        "es": "No se reconoció habla en el doblaje, así que no se pudo medir.",
    },

    # ----- dub language -----
    "r.lang.good": {
        "en": "Speech recognition hears {lang} in the dub ({prob} sure), which is the language it was dubbed into.",
        "ko": "음성 인식 결과 더빙에서 들리는 언어: {lang}(확신도 {prob}). 요청한 더빙 언어와 같습니다.",
        "pt": "O reconhecimento de fala ouve {lang} na dublagem ({prob} de certeza), que é o idioma escolhido.",
        "es": "El reconocimiento de voz oye {lang} en el doblaje ({prob} de seguridad), que es el idioma elegido.",
    },
    "r.lang.subs": {"en": "The dub says what its {lang} subtitle file says ({match} of the letters match), so it is in {lang}. From the sound alone, speech recognition guessed another language ({detected}), which is common for less common languages.", "ko": "더빙이 {lang} 자막 파일과 같은 내용을 말합니다(글자 일치율 {match}). 따라서 더빙 언어는 {lang}입니다. 소리만으로는 음성 인식이 다른 언어({detected})로 추측했는데, 덜 흔한 언어에서 자주 생기는 일입니다.", "pt": "A dublagem diz o que o arquivo de legendas em {lang} diz ({match} das letras coincidem), então está em {lang}. Só pelo som, o reconhecimento de fala supôs outro idioma ({detected}), o que é comum em idiomas menos comuns.", "es": "El doblaje dice lo que dice su archivo de subtítulos en {lang} (coincide el {match} de las letras), así que está en {lang}. Solo por el sonido, el reconocimiento de voz supuso otro idioma ({detected}), algo habitual en idiomas menos comunes."},
    "r.lang.subs_display": {"en": "{lang} (matches its subtitles: {match})", "ko": "{lang} (자막 일치율: {match})", "pt": "{lang} (coincide com as legendas: {match})", "es": "{lang} (coincide con los subtítulos: {match})"},
    "r.g.language_subs": {"en": "Good when the dub is in the requested language and speech recognition is at least {prob} sure, or when the dub's speech matches its subtitle file in that language (at least {match} of the letters).", "ko": "요청한 언어이고 음성 인식 확신도가 {prob} 이상이거나, 더빙의 말이 그 언어의 자막 파일과 일치하면(글자 일치율 {match} 이상) 좋음입니다.", "pt": "Bom quando a dublagem está no idioma pedido e o reconhecimento tem pelo menos {prob} de certeza, ou quando a fala da dublagem coincide com o arquivo de legendas nesse idioma (pelo menos {match} das letras).", "es": "Bueno cuando el doblaje está en el idioma pedido y el reconocimiento tiene al menos un {prob} de certeza, o cuando el habla del doblaje coincide con su archivo de subtítulos en ese idioma (al menos un {match} de las letras)."},
    "r.lang.check": {
        "en": "The dub is probably in {lang}, but speech recognition is only {prob} sure. Listen to confirm the right "
              "language was used.",
        "ko": "더빙 언어가 {lang}(으)로 보이지만 음성 인식의 확신도가 {prob}뿐입니다. 올바른 언어인지 직접 들어 확인하세요.",
        "pt": "A dublagem provavelmente está em {lang}, mas o reconhecimento de fala tem só {prob} de certeza. Ouça para "
              "confirmar o idioma.",
        "es": "El doblaje probablemente está en {lang}, pero el reconocimiento de voz solo tiene un {prob} de seguridad. "
              "Escucha para confirmar el idioma.",
    },
    "r.lang.poor": {
        "en": "Speech recognition hears a different language ('{detected}') instead of {lang}. The wrong language may have "
              "been generated, or the original voice was left in.",
        "ko": "요청한 언어는 {lang}인데 음성 인식 결과 다른 언어('{detected}')가 들립니다. 잘못된 언어로 생성되었거나 원본 "
              "음성이 그대로 남아 있을 수 있습니다.",
        "pt": "O reconhecimento de fala ouve outro idioma ('{detected}') em vez de {lang}. O idioma errado pode ter sido "
              "gerado, ou a voz original ficou no vídeo.",
        "es": "El reconocimiento de voz oye otro idioma ('{detected}') en lugar de {lang}. Pudo generarse el idioma "
              "equivocado o quedar la voz original.",
    },
    "r.lang.unsupported": {
        "en": "Speech recognition can't identify {lang}, so the language couldn't be checked.",
        "ko": "음성 인식이 이 언어({lang})를 구분하지 못해 언어를 확인할 수 없습니다.",
        "pt": "O reconhecimento de fala não identifica {lang}, então o idioma não pôde ser verificado.",
        "es": "El reconocimiento de voz no identifica {lang}, así que no se pudo comprobar el idioma.",
    },
    "r.lang.display": {"en": "{lang} ({prob} sure)", "ko": "{lang} (확신도 {prob})", "pt": "{lang} ({prob} de certeza)",
                       "es": "{lang} ({prob} de seguridad)"},
    "r.g.language": {
        "en": "Good when the dub is in the requested language and speech recognition is at least {prob} sure.",
        "ko": "요청한 언어이고 음성 인식 확신도가 {prob} 이상이면 좋음입니다.",
        "pt": "Bom se a dublagem está no idioma pedido e o reconhecimento de fala tem pelo menos {prob} de certeza.",
        "es": "Bien si el doblaje está en el idioma pedido y el reconocimiento de voz tiene al menos un {prob} de "
              "seguridad.",
    },

    # ----- voice clarity -----
    "r.clarity.good": {
        "en": "Speech recognition understood {pct} of the dub without trouble, so the voice is easy to understand.",
        "ko": "음성 인식이 더빙의 {pct}를 문제없이 알아들었습니다. 목소리가 알아듣기 쉽습니다.",
        "pt": "O reconhecimento de fala entendeu {pct} da dublagem sem dificuldade, então a voz é fácil de entender.",
        "es": "El reconocimiento de voz entendió el {pct} del doblaje sin problemas, así que la voz se entiende bien.",
    },
    "r.clarity.check": {
        "en": "Speech recognition struggled with {unclear} of the dub ({n} parts). Those parts may be mumbled or unclear; "
              "they are listed under Things to check.",
        "ko": "음성 인식이 더빙의 {unclear}({n}곳)를 알아듣기 어려워했습니다. 발음이 뭉개졌거나 불분명할 수 있으며, "
              "확인할 사항에 목록이 있습니다.",
        "pt": "O reconhecimento de fala teve dificuldade com {unclear} da dublagem ({n} trechos). Esses trechos podem estar "
              "abafados ou pouco claros; eles aparecem em Pontos a verificar.",
        "es": "El reconocimiento de voz tuvo problemas con el {unclear} del doblaje ({n} partes). Pueden estar poco claras; "
              "aparecen en Cosas que revisar.",
    },
    "r.clarity.poor": {
        "en": "A large part of the dub ({unclear}, {n} parts) was hard to understand. Listen to the parts listed under "
              "Things to check.",
        "ko": "더빙의 상당 부분({unclear}, {n}곳)을 알아듣기 어렵습니다. 확인할 사항에 있는 부분을 들어 보세요.",
        "pt": "Grande parte da dublagem ({unclear}, {n} trechos) foi difícil de entender. Ouça os trechos em Pontos a "
              "verificar.",
        "es": "Gran parte del doblaje ({unclear}, {n} partes) fue difícil de entender. Escucha las partes de Cosas que "
              "revisar.",
    },
    "r.clarity.display": {"en": "{pct} clear", "ko": "{pct} 명료", "pt": "{pct} claro", "es": "{pct} claro"},
    "r.g.clarity": {
        "en": "Good when at least {good}% of the speech is understood clearly, Needs review from {check}%, otherwise Poor.",
        "ko": "말소리의 {good}% 이상을 또렷하게 알아들으면 좋음, {check}% 이상이면 검토 필요, 그보다 낮으면 미흡입니다.",
        "pt": "Bom se pelo menos {good}% da fala é entendida com clareza, Precisa de revisão a partir de {check}%, abaixo disso Ruim.",
        "es": "Bien si al menos el {good}% del habla se entiende con claridad, Necesita revisión desde el {check}%, si no Deficiente.",
    },
    "r.script": {
        "en": "{acc} of your script was heard in the dub. A different but correct wording also lowers this score.",
        "ko": "스크립트의 {acc}가 더빙에서 들렸습니다. 표현이 다르지만 올바른 번역도 점수를 낮춥니다.",
        "pt": "{acc} do seu roteiro foi ouvido na dublagem. Uma redação diferente, mas correta, também baixa esta nota.",
        "es": "Se oyó el {acc} de tu guion en el doblaje. Una redacción distinta pero correcta también baja esta nota.",
    },
    "r.g.script": {
        "en": "Good from {good}%, Needs review from {check}%, otherwise Poor.",
        "ko": "{good}% 이상이면 좋음, {check}% 이상이면 검토 필요, 그보다 낮으면 미흡입니다.",
        "pt": "Bom a partir de {good}%, Precisa de revisão a partir de {check}%, abaixo disso Ruim.",
        "es": "Bien desde el {good}%, Necesita revisión desde el {check}%, si no Deficiente.",
    },

    # ----- speech timing -----
    "r.align.good": {
        "en": "The dub speaks at the same moments as the original ({ov} of the speaking time lines up), so the voice "
              "matches when the speaker talks on screen.",
        "ko": "더빙이 원본과 같은 순간에 말합니다(말하는 시간의 {ov}가 일치). 화면 속 화자가 말할 때 목소리가 맞게 "
              "나옵니다.",
        "pt": "A dublagem fala nos mesmos momentos que o original ({ov} do tempo de fala coincide), então a voz combina "
              "com quando a pessoa fala na tela.",
        "es": "El doblaje habla en los mismos momentos que el original (coincide el {ov} del tiempo de habla), así que la "
              "voz encaja con cuando la persona habla en pantalla.",
    },
    "r.align.check": {
        "en": "The dub mostly speaks at the same moments as the original ({ov} lines up), but some parts are off.",
        "ko": "더빙이 대체로 원본과 같은 순간에 말하지만({ov} 일치) 어긋나는 부분이 있습니다.",
        "pt": "A dublagem fala quase sempre nos mesmos momentos que o original ({ov} coincide), mas alguns trechos "
              "estão fora.",
        "es": "El doblaje habla casi siempre en los mismos momentos que el original (coincide el {ov}), pero algunas "
              "partes no.",
    },
    "r.align.poor": {
        "en": "The dub often speaks when the original is silent, or stays silent when the original speaks (only {ov} "
              "lines up). The voice won't match the picture in those places.",
        "ko": "원본이 조용할 때 더빙이 말하거나 원본이 말할 때 더빙이 조용한 경우가 많습니다({ov}만 일치). 그 부분에서는 "
              "목소리가 화면과 맞지 않습니다.",
        "pt": "A dublagem muitas vezes fala quando o original está em silêncio, ou fica calada quando o original fala "
              "(só {ov} coincide). Nesses trechos a voz não combina com a imagem.",
        "es": "El doblaje a menudo habla cuando el original calla, o calla cuando el original habla (solo coincide el "
              "{ov}). En esas partes la voz no encaja con la imagen.",
    },
    "r.align.na": {
        "en": "Speech wasn't found in one of the videos, so the timing couldn't be compared.",
        "ko": "한쪽 영상에서 말소리를 찾지 못해 타이밍을 비교할 수 없습니다.",
        "pt": "Não foi encontrada fala em um dos vídeos, então o tempo não pôde ser comparado.",
        "es": "No se encontró habla en uno de los videos, así que no se pudo comparar el momento.",
    },
    "r.align.spots_one": {
        "en": "{n} short moment doesn't line up; it is listed under Things to check.",
        "ko": "짧게 어긋나는 곳이 {n}곳 있으며 확인할 사항에 나와 있습니다.",
        "pt": "{n} momento curto não coincide; ele aparece em Pontos a verificar.",
        "es": "{n} momento corto no coincide; aparece en Cosas que revisar.",
    },
    "r.align.spots_many": {
        "en": "{n} short moments don't line up; they are listed under Things to check.",
        "ko": "짧게 어긋나는 곳이 {n}곳 있으며 확인할 사항에 나와 있습니다.",
        "pt": "{n} momentos curtos não coincidem; eles aparecem em Pontos a verificar.",
        "es": "{n} momentos cortos no coinciden; aparecen en Cosas que revisar.",
    },
    "r.align.no_spots": {
        "en": "Each part that is off is too short to show on the timeline: the timing slips a little in many "
              "places, not a lot in one.",
        "ko": "어긋나는 부분이 하나하나는 짧아 타임라인에 표시하지 않았습니다. 한곳에서 크게 어긋나기보다 여러 곳에서 조금씩 어긋납니다.",
        "pt": "Cada trecho fora do tempo é curto demais para aparecer na linha do tempo: a fala adianta ou "
              "atrasa um pouco em vários pontos, e não muito em um só.",
        "es": "Cada parte desfasada es demasiado corta para mostrarse en la línea de tiempo: la sincronización "
              "se desvía un poco en muchos sitios, no mucho en uno solo.",
    },
    "r.align.display": {"en": "{ov} lined up", "ko": "{ov} 일치", "pt": "{ov} coincide", "es": "{ov} coincide"},
    "r.g.align": {
        "en": "Good when at least {good}% of the speaking time lines up, Needs review from {check}%, otherwise Poor. Languages "
              "have different rhythms, so 100% isn't expected.",
        "ko": "말하는 시간의 {good}% 이상이 일치하면 좋음, {check}% 이상이면 검토 필요, 그보다 낮으면 미흡입니다. 언어마다 "
              "리듬이 달라 100%는 기대하지 않습니다.",
        "pt": "Bom se pelo menos {good}% do tempo de fala coincide, Precisa de revisão a partir de {check}%, abaixo disso Ruim. Cada "
              "idioma tem seu ritmo, então 100% não é esperado.",
        "es": "Bien si coincide al menos el {good}% del tiempo de habla, Necesita revisión desde el {check}%, si no Deficiente. Cada "
              "idioma tiene su ritmo, así que no se espera un 100%.",
    },
    "r.offsets": {
        "en": "The dub starts speaking {start} s {start_way} and stops {end} s {end_way} than the original. Shown for "
              "information; it doesn't change the verdict.",
        "ko": "더빙은 원본보다 {start}초 {start_way} 말하기 시작해 {end}초 {end_way} 끝납니다. 참고용이며 판정에는 영향이 "
              "없습니다.",
        "pt": "A dublagem começa a falar {start} s {start_way} e termina {end} s {end_way} que o original. É só "
              "informação; não muda o resultado.",
        "es": "El doblaje empieza a hablar {start} s {start_way} y termina {end} s {end_way} que el original. Es solo "
              "informativo; no cambia el resultado.",
    },
    "r.later": {"en": "later", "ko": "늦게", "pt": "depois", "es": "más tarde"},
    "r.lang_code": {"en": "en", "ko": "ko", "pt": "pt", "es": "es"},
    "r.sec": {"en": "{sec} s", "ko": "{sec}초", "pt": "{sec} s", "es": "{sec} s"},
    "r.sec_pct": {"en": "{sec} s ({pct}%)", "ko": "{sec}초 ({pct}%)", "pt": "{sec} s ({pct}%)", "es": "{sec} s ({pct}%)"},
    "r.offsets.display": {
        "en": "Against the original: starts {start} · ends {end}",
        "ko": "원본 대비 · 시작 {start} · 끝 {end}",
        "pt": "Em relação ao original: começa {start} · termina {end}",
        "es": "Frente al original: empieza {start} · termina {end}",
    },
    "r.offset.early": {"en": "{sec} s early", "ko": "{sec}초 일찍", "pt": "{sec} s antes", "es": "{sec} s antes"},
    "r.offset.late": {"en": "{sec} s late", "ko": "{sec}초 늦게", "pt": "{sec} s depois", "es": "{sec} s después"},
    "r.offset.same": {
        "en": "on time",
        "ko": "차이 없음",
        "pt": "na hora",
        "es": "a tiempo",
    },
    "r.silence.display": {"en": "{dub} vs {orig} original", "ko": "원본 {orig} 대비 {dub}",
                          "pt": "{dub} vs. {orig} do original", "es": "{dub} frente a {orig} del original"},
    "r.clip.none": {"en": "None", "ko": "없음", "pt": "Nenhuma", "es": "Ninguna"},
    "r.vs.cant_tell": {
        "en": "Can't tell on this video",
        "ko": "이 영상에서는 판단할 수 없음",
        "pt": "Não dá para dizer neste vídeo",
        "es": "No se puede saber en este video",
    },
    "r.earlier": {"en": "earlier", "ko": "일찍", "pt": "antes", "es": "antes"},

    # ----- translation -----
    "r.meaning.good": {
        "en": "The meaning comes across correctly.", "ko": "의미가 올바르게 전달됩니다.",
        "pt": "O sentido é transmitido corretamente.", "es": "El sentido se transmite correctamente.",
    },
    "r.meaning.check": {
        "en": "Some meaning is lost or changed; the lines are listed under Things to check.",
        "ko": "일부 의미가 빠지거나 달라졌습니다. 해당 대사는 확인할 사항에 표시했습니다.",
        "pt": "Parte do sentido se perdeu ou mudou; as falas aparecem em Pontos a verificar.",
        "es": "Parte del sentido se perdió o cambió; las frases aparecen en Cosas que revisar.",
    },
    "r.meaning.poor": {
        "en": "The dub often says something different from the original; the translation needs to be redone.",
        "ko": "더빙이 원본과 다른 내용을 말하는 경우가 많습니다. 번역을 다시 해야 합니다.",
        "pt": "A dublagem muitas vezes diz algo diferente do original; a tradução precisa ser refeita.",
        "es": "El doblaje a menudo dice algo distinto del original; hay que rehacer la traducción.",
    },
    "r.g.meaning": {
        "en": "Rated 1–5 by {model} from both transcripts: Good from {good}, Needs review at {check}, otherwise Poor.",
        "ko": "두 받아쓰기를 비교해 1–5점으로 평가(평가 모델: {model}): {good}점 이상 좋음, {check}점 검토 필요, 그보다 낮으면 미흡.",
        "pt": "Nota de 1 a 5 dada por {model} com base nas duas transcrições: Bom a partir de {good}, Precisa de revisão em {check}, "
              "abaixo disso Ruim.",
        "es": "Nota de 1 a 5 de {model} a partir de las dos transcripciones: Bien desde {good}, Necesita revisión en {check}, si no "
              "Deficiente.",
    },
    "r.issues.none_completeness": {
        "en": "Nothing important from the original is missing, and nothing was added.",
        "ko": "원본의 중요한 내용이 빠지지 않았고 추가된 내용도 없습니다.",
        "pt": "Nada importante do original está faltando, e nada foi acrescentado.",
        "es": "No falta nada importante del original y no se añadió nada.",
    },
    "r.issues.none_names_numbers": {
        "en": "Names and numbers are kept correctly.", "ko": "이름과 숫자가 올바르게 유지되었습니다.",
        "pt": "Nomes e números foram mantidos corretamente.", "es": "Los nombres y números se mantienen correctamente.",
    },
    "r.issues.none_mistranslations": {
        "en": "No passage changes the meaning.", "ko": "의미가 바뀐 부분이 없습니다.",
        "pt": "Nenhum trecho muda o sentido.", "es": "Ningún pasaje cambia el sentido.",
    },
    "r.issues.found_one": {
        "en": "{n} problem found ({major} serious). It is listed under Things to check with the original and dubbed words.",
        "ko": "문제 {n}건을 찾았습니다(심각 {major}건). 원본과 더빙 문장과 함께 확인할 사항에 나와 있습니다.",
        "pt": "{n} problema encontrado ({major} grave). Ele aparece em Pontos a verificar com as palavras originais e "
              "dubladas.",
        "es": "{n} problema encontrado ({major} grave). Aparece en Cosas que revisar con las palabras originales y dobladas.",
    },
    "r.issues.found_many": {
        "en": "{n} problems found ({major} serious). They are listed under Things to check with the original and dubbed "
              "words.",
        "ko": "문제 {n}건을 찾았습니다(심각 {major}건). 원본과 더빙 문장과 함께 확인할 사항에 나와 있습니다.",
        "pt": "{n} problemas encontrados ({major} graves). Eles aparecem em Pontos a verificar com as palavras originais e "
              "dubladas.",
        "es": "{n} problemas encontrados ({major} graves). Aparecen en Cosas que revisar con las palabras originales y "
              "dobladas.",
    },
    "r.issues.maybe_only_one": {
        "en": "{n} possible mistake, but it is probably a speech-recognition error, not a dubbing error, so it doesn't "
              "lower the grade. Listen to it under Things to check.",
        "ko": "문제로 보이는 곳이 {n}곳 있지만 더빙 오류가 아니라 음성 인식 오류일 가능성이 높아 등급을 낮추지 않습니다. "
              "확인할 사항에서 직접 들어 보세요.",
        "pt": "{n} possível erro, mas provavelmente é um erro do reconhecimento de fala, não da dublagem, então não baixa "
              "a nota. Ouça em Pontos a verificar.",
        "es": "{n} posible error, pero probablemente es del reconocimiento de voz, no del doblaje, así que no baja la nota. "
              "Escúchalo en Cosas que revisar.",
    },
    "r.issues.maybe_only_many": {
        "en": "{n} possible mistakes, but they are probably speech-recognition errors, not dubbing errors, so they don't "
              "lower the grade. Listen to them under Things to check.",
        "ko": "문제로 보이는 곳이 {n}곳 있지만 더빙 오류가 아니라 음성 인식 오류일 가능성이 높아 등급을 낮추지 않습니다. "
              "확인할 사항에서 직접 들어 보세요.",
        "pt": "{n} possíveis erros, mas provavelmente são do reconhecimento de fala, não da dublagem, então não baixam a "
              "nota. Ouça em Pontos a verificar.",
        "es": "{n} posibles errores, pero probablemente son del reconocimiento de voz, no del doblaje, así que no bajan la "
              "nota. Escúchalos en Cosas que revisar.",
    },
    "r.issues.plus_maybe_one": {
        "en": "{n} more is probably a speech-recognition error and doesn't count.",
        "ko": "그 밖의 {n}건은 음성 인식 오류로 보여 계산하지 않습니다.",
        "pt": "Mais {n} provavelmente é erro do reconhecimento de fala e não conta.",
        "es": "{n} más probablemente es un error del reconocimiento de voz y no cuenta.",
    },
    "r.issues.plus_maybe_many": {
        "en": "{n} more are probably speech-recognition errors and don't count.",
        "ko": "그 밖의 {n}건은 음성 인식 오류로 보여 계산하지 않습니다.",
        "pt": "Mais {n} provavelmente são erros do reconhecimento de fala e não contam.",
        "es": "{n} más probablemente son errores del reconocimiento de voz y no cuentan.",
    },
    "r.issues.count_one": {"en": "{n} problem", "ko": "문제 {n}건", "pt": "{n} problema", "es": "{n} problema"},
    "r.issues.count_many": {"en": "{n} problems", "ko": "문제 {n}건", "pt": "{n} problemas", "es": "{n} problemas"},
    "r.issues.maybe_count_one": {"en": "{n} possible mishearing", "ko": "인식 오류 추정 {n}건",
                                 "pt": "{n} possível erro de escuta", "es": "{n} posible error de escucha"},
    "r.issues.maybe_count_many": {"en": "{n} possible mishearings", "ko": "인식 오류 추정 {n}건",
                                  "pt": "{n} possíveis erros de escuta", "es": "{n} posibles errores de escucha"},
    "r.g.issues": {
        "en": "Good with no problems, Needs review with minor ones only, Poor with any serious one. Probable speech-recognition "
              "errors don't count.",
        "ko": "문제가 없으면 좋음, 사소한 문제만 있으면 검토 필요, 심각한 문제가 하나라도 있으면 미흡입니다. 음성 인식 "
              "오류로 보이는 것은 계산하지 않습니다.",
        "pt": "Bom sem problemas, Precisa de revisão só com problemas leves, Ruim com qualquer problema grave. Prováveis erros do "
              "reconhecimento de fala não contam.",
        "es": "Bien sin problemas, Necesita revisión solo con problemas leves, Deficiente con cualquier problema grave. Los "
              "probables errores del reconocimiento de voz no cuentan.",
    },
    "r.judge.nothing": {"en": "no speech", "ko": "말 없음", "pt": "sem fala", "es": "sin habla"},
    "r.judge.has_nothing": {"en": "has no speech", "ko": "말 없음", "pt": "não tem fala", "es": "no tiene habla"},
    "r.judge.added_line": {
        "en": "The original has no speech here, but the dub adds a line.",
        "ko": "원본에는 이 부분에 말이 없는데, 더빙에 문장이 추가되었습니다.",
        "pt": "O original não tem fala aqui, mas a dublagem acrescenta uma fala.",
        "es": "El original no tiene habla aquí, pero el doblaje añade una frase.",
    },
    "r.judge.left_out_line": {
        "en": "The original says something here, but the dub has no speech.",
        "ko": "원본에는 말이 있는데, 더빙에는 이 부분에 말이 없습니다.",
        "pt": "O original diz algo aqui, mas a dublagem não tem fala.",
        "es": "El original dice algo aquí, pero el doblaje no tiene habla.",
    },
    "r.judge.off": {
        "en": "The translation check was turned off for this run.",
        "ko": "이번 실행에서는 번역 검토를 끄고 진행했습니다.",
        "pt": "A verificação da tradução foi desligada nesta execução.",
        "es": "La revisión de la traducción se desactivó en esta ejecución.",
    },
    "r.judge.unrecognized": {"en": "Not checked: speech recognition couldn't make out the dub's language, so its words can't be compared with the original. Add the dub's subtitle file, or try the large speech model.", "ko": "검사 안 함: 음성 인식이 더빙 언어를 알아듣지 못해 더빙의 말을 원본과 비교할 수 없습니다. 더빙 자막 파일을 추가하거나 큰 음성 인식 모델을 사용해 보세요.", "pt": "Não verificado: o reconhecimento de fala não entendeu o idioma da dublagem, então suas palavras não podem ser comparadas com o original. Adicione o arquivo de legendas da dublagem ou experimente o modelo de fala grande.", "es": "No comprobado: el reconocimiento de voz no entendió el idioma del doblaje, así que sus palabras no se pueden comparar con el original. Añade el archivo de subtítulos del doblaje o prueba el modelo de habla grande."},
    "r.m.naturalness": {"en": "Natural wording", "ko": "자연스러운 표현", "pt": "Naturalidade", "es": "Naturalidad"},
    "r.m.context_fit": {"en": "Fits the context", "ko": "문맥 일관성", "pt": "Coerência com o contexto", "es": "Coherencia con el contexto"},
    "r.m.terminology": {"en": "Consistent terms", "ko": "용어·표현 일관성", "pt": "Termos consistentes", "es": "Términos coherentes"},
    "r.m.localization": {"en": "Localization", "ko": "현지화", "pt": "Localização", "es": "Localización"},
    # The translation check's one row: what it says, its value and how it is graded.
    "r.tr.low": {
        "en": "Lines that lose or change the original's meaning: {n} of {total} (average {avg} / 10).",   # n: counted lines
        "ko": "원본의 의미가 빠지거나 달라진 줄: {total}줄 중 {n}줄(평균 {avg}/10).",
        "pt": "Falas que perdem ou mudam o sentido do original: {n} de {total} (média {avg} / 10).",
        "es": "Frases que pierden o cambian el sentido del original: {n} de {total} (promedio {avg} / 10).",
    },
    "r.tr.all_keep": {
        "en": "Every line keeps the original's meaning (average {avg} / 10 over {total} lines).",
        "ko": "모든 줄이 원본의 의미를 유지합니다({total}줄 평균 {avg}/10).",
        "pt": "Todas as falas mantêm o sentido do original (média {avg} / 10 em {total} falas).",
        "es": "Todas las frases mantienen el sentido del original (promedio {avg} / 10 en {total} frases).",
    },
    "r.tr.none_clear": {
        "en": "No line clearly loses the original's meaning (average {avg} / 10 over {total} lines).",
        "ko": "의미가 분명히 달라진 줄은 없습니다({total}줄 평균 {avg}/10).",
        "pt": "Nenhuma fala perde claramente o sentido do original (média {avg} / 10 em {total} falas).",
        "es": "Ninguna frase pierde claramente el sentido del original (promedio {avg} / 10 en {total} frases).",
    },
    "r.tr.of": {"en": "{n} of {total}", "ko": "{total}줄 중 {n}줄", "pt": "{n} de {total}", "es": "{n} de {total}"},
    "r.tr.wording_only": {
        "en": "The meaning is kept; the wording of the lines listed needs a look.",
        "ko": "의미는 유지됩니다. 표시된 줄의 표현을 확인하세요.",
        "pt": "O sentido é mantido; a redação das falas listadas merece uma olhada.",
        "es": "El sentido se mantiene; conviene mirar la redacción de las frases indicadas.",
    },
    "r.tr.display_low": {
        "en": "{low} of {total} lines flagged · meaning {avg} / 10", "ko": "{total}줄 중 {low}줄 표시 · 의미 {avg}/10",
        "pt": "{low} de {total} falas marcadas · sentido {avg} / 10",
        "es": "{low} de {total} frases marcadas · sentido {avg} / 10",
    },
    "r.tr.display_ok": {"en": "meaning {avg} / 10", "ko": "의미 {avg}/10", "pt": "sentido {avg} / 10",
                        "es": "sentido {avg} / 10"},
    "r.g.translation": {
        "en": "{model} scores every line from 1 to 10 for meaning, natural wording, context, consistent terms and "
              "localization, against written descriptions of each score. Poor when {count} or more lines (or most lines) "
              "score {poor} or lower for meaning; Needs review when any line scores {flag} or lower on any of the five; "
              "otherwise Good. Lines that speech recognition may have misheard are listed but don't count.",
        "ko": "{model} 모델이 각 점수의 설명에 따라 모든 줄을 의미, 자연스러운 표현, 문맥, 용어 일관성, 현지화 기준으로 1~10점으로 "
              "평가합니다. 의미가 {poor}점 이하인 줄이 {count}개 이상이거나 대부분이면 미흡, 다섯 기준 중 하나라도 {flag}점 이하인 줄이 "
              "있으면 검토 필요, 그 외에는 좋음입니다. 음성 인식이 잘못 들었을 수 있는 줄은 목록에만 표시하고 평가에 넣지 않습니다.",
        "pt": "{model} dá a cada fala uma nota de 1 a 10 em sentido, naturalidade, contexto, termos consistentes e "
              "localização, seguindo descrições escritas de cada nota. Ruim quando {count} ou mais falas (ou a maioria) "
              "têm {poor} ou menos em sentido; Precisa de revisão quando alguma fala tem {flag} ou menos em qualquer das "
              "cinco; senão, Bom. Falas que o reconhecimento de fala pode ter ouvido errado são listadas, mas não contam.",
        "es": "{model} puntúa cada frase del 1 al 10 en sentido, naturalidad, contexto, términos coherentes y "
              "localización, según descripciones escritas de cada nota. Deficiente cuando {count} o más frases (o la "
              "mayoría) obtienen {poor} o menos en sentido; Necesita revisión cuando alguna frase obtiene {flag} o menos "
              "en cualquiera de las cinco; si no, Bien. Las frases que el reconocimiento de voz pudo oír mal se listan, "
              "pero no cuentan.",
    },
    "r.g.second_listen": {
        "en": "A marked-down line is heard a second time on its own, and counts only if it reads as a problem both times.",
        "ko": "문제로 표시된 줄은 그 줄만 한 번 더 인식해, 두 번 모두 문제로 읽힐 때만 평가에 넣습니다.",
        "pt": "Uma fala marcada é ouvida uma segunda vez sozinha e só conta se parecer um problema nas duas vezes.",
        "es": "Una frase marcada se oye una segunda vez por separado y solo cuenta si parece un problema las dos veces.",
    },
    "r.tr.heard_again_one": {
        "en": "{n} line was marked down at first but reads fine when heard again, and doesn't count.",
        "ko": "{n}줄은 처음에는 문제로 표시됐지만 다시 들으니 문제가 없어 계산하지 않습니다.",
        "pt": "{n} fala foi marcada no início, mas está boa quando ouvida de novo, e não conta.",
        "es": "{n} frase se marcó al principio, pero está bien al oírla de nuevo, y no cuenta.",
    },
    "r.tr.heard_again_many": {
        "en": "{n} lines were marked down at first but read fine when heard again, and don't count.",
        "ko": "{n}줄은 처음에는 문제로 표시됐지만 다시 들으니 문제가 없어 계산하지 않습니다.",
        "pt": "{n} falas foram marcadas no início, mas estão boas quando ouvidas de novo, e não contam.",
        "es": "{n} frases se marcaron al principio, pero están bien al oírlas de nuevo, y no cuentan.",
    },
    "r.int.heard_again_dub": {
        "en": "The dub was first heard as “{first}” and marked down. Heard again on its own, it says “{second}”, which "
              "is a fine translation.",
        "ko": "처음 인식한 더빙: “{first}”. 이 줄만 다시 인식한 결과: “{second}”. 다시 들은 내용으로는 번역에 문제가 없습니다.",
        "pt": "A dublagem foi ouvida primeiro como “{first}” e marcada como problema. Ouvida de novo sozinha, diz "
              "“{second}”, que é uma boa tradução.",
        "es": "El doblaje se oyó primero como “{first}” y se marcó como problema. Al oírlo de nuevo por separado, dice "
              "“{second}”, que es una buena traducción.",
    },
    "r.int.heard_again_original": {
        "en": "The original was first heard as “{first}”, which made the dub look wrong. Heard again on its own, it says "
              "“{second}”, and the dub matches that.",
        "ko": "처음 인식한 원본: “{first}”. 이 줄만 다시 인식한 결과: “{second}”. 다시 들은 내용과는 더빙이 맞습니다.",
        "pt": "O original foi ouvido primeiro como “{first}”, o que fazia a dublagem parecer errada. Ouvido de novo "
              "sozinho, diz “{second}”, e a dublagem corresponde.",
        "es": "El original se oyó primero como “{first}”, lo que hacía parecer incorrecto el doblaje. Al oírlo de nuevo "
              "por separado, dice “{second}”, y el doblaje coincide.",
    },
    "r.int.heard_nothing_dub": {
        "en": "No dub speech was heard here at first, so the line looked left out. Heard again on its own, the dub says "
              "“{second}”.",
        "ko": "처음에는 이 구간에서 더빙 음성을 듣지 못해 빠진 줄로 보였습니다. 이 줄만 다시 인식한 결과: “{second}”.",
        "pt": "No início nenhuma fala da dublagem foi ouvida aqui, e a fala parecia omitida. Ouvida de novo sozinha, a "
              "dublagem diz “{second}”.",
        "es": "Al principio no se oyó voz del doblaje aquí, y la frase parecía omitida. Al oírlo de nuevo por separado, "
              "el doblaje dice “{second}”.",
    },
    "r.int.heard_nothing_original": {
        "en": "No original speech was heard here at first, so the dub's line looked added. Heard again on its own, the "
              "original says “{second}”.",
        "ko": "처음에는 이 구간에서 원본 음성을 듣지 못해 더빙에 추가된 줄로 보였습니다. 이 줄만 다시 인식한 결과: “{second}”.",
        "pt": "No início nenhuma fala do original foi ouvida aqui, e a fala da dublagem parecia acrescentada. Ouvido de "
              "novo sozinho, o original diz “{second}”.",
        "es": "Al principio no se oyó voz del original aquí, y la frase del doblaje parecía añadida. Al oírlo de nuevo "
              "por separado, el original dice “{second}”.",
    },
    "r.todo.suggested": {"en": "Suggested translation: “{text}”", "ko": "추천 번역: “{text}”", "pt": "Tradução sugerida: “{text}”", "es": "Traducción sugerida: “{text}”"},
    "r.cat.wording": {"en": "translation wording", "ko": "번역 표현", "pt": "redação da tradução", "es": "redacción de la traducción"},
    "r.tcat.omission": {"en": "Omission", "ko": "누락", "pt": "Omissão", "es": "Omisión"},
    "r.tcat.distortion": {"en": "Meaning distorted", "ko": "의미 왜곡", "pt": "Sentido distorcido", "es": "Sentido distorsionado"},
    "r.tcat.context_misread": {"en": "Context misread", "ko": "문맥 파악 실패로 인한 의미 왜곡", "pt": "Contexto mal entendido", "es": "Contexto mal entendido"},
    "r.tcat.invented": {"en": "Content not in the original", "ko": "원문에 없는 내용 추가", "pt": "Conteúdo que não está no original", "es": "Contenido que no está en el original"},
    "r.tcat.repetitive_style": {"en": "Repetitive structure", "ko": "문체·구조 반복", "pt": "Estrutura repetitiva", "es": "Estructura repetitiva"},
    "r.tcat.wordiness": {"en": "Wordiness", "ko": "장황함", "pt": "Prolixidade", "es": "Verbosidad"},
    "r.tcat.literal_order": {"en": "Word order copied from the original", "ko": "어순·문체 직번역", "pt": "Ordem das palavras copiada do original", "es": "Orden de palabras copiado del original"},
    "r.tcat.word_for_word": {"en": "Word-for-word translation", "ko": "단어 단위 직역", "pt": "Tradução palavra por palavra", "es": "Traducción palabra por palabra"},
    "r.tcat.idiom": {"en": "Idiom or figure of speech misread", "ko": "비유·표현 해석 실패", "pt": "Expressão idiomática mal interpretada", "es": "Expresión idiomática mal interpretada"},
    "r.tcat.formality": {"en": "Wrong level of formality", "ko": "격식 수준 오류", "pt": "Nível de formalidade errado", "es": "Nivel de formalidad incorrecto"},
    "r.tcat.tone_consistency": {"en": "Inconsistent tone", "ko": "톤·격식 일관성 오류", "pt": "Tom inconsistente", "es": "Tono incoherente"},
    "r.tcat.pronoun": {"en": "Pronoun misread", "ko": "대명사 해석 오류", "pt": "Pronome mal interpretado", "es": "Pronombre mal interpretado"},
    "r.tcat.possessive": {"en": "Possessive or relation misread", "ko": "소유격·관계 해석 오류", "pt": "Possessivo ou relação mal interpretada", "es": "Posesivo o relación mal interpretada"},
    "r.tcat.gender_number": {"en": "Gender or number mismatch", "ko": "성·수 불일치", "pt": "Gênero ou número não concordam", "es": "Género o número no concuerdan"},
    "r.tcat.term_consistency": {"en": "Inconsistent terms", "ko": "용어 일관성 오류", "pt": "Termos inconsistentes", "es": "Términos incoherentes"},
    "r.tcat.technical_term": {"en": "Technical term wrong", "ko": "전문 용어 오류", "pt": "Termo técnico errado", "es": "Término técnico incorrecto"},
    "r.tcat.abbreviation": {"en": "Abbreviation problem", "ko": "줄임말·약어 오류", "pt": "Problema de abreviação", "es": "Problema de abreviatura"},
    "r.tcat.culture": {"en": "Doesn't fit the local culture", "ko": "현지 문화에 맞지 않는 표현", "pt": "Não combina com a cultura local", "es": "No encaja con la cultura local"},
    "r.tcat.dnt": {"en": "Translated what should stay as it is", "ko": "번역하지 말아야 할 항목 번역", "pt": "Traduziu o que devia ficar como está", "es": "Tradujo lo que debía quedar igual"},
    "r.tcat.segmentation": {"en": "Sentence split or joined wrongly", "ko": "문장 분리·결합 문제", "pt": "Frase dividida ou unida errado", "es": "Frase dividida o unida mal"},
    "r.tcat.clause_structure": {"en": "Clause structure wrong", "ko": "구문·절 구조 오류", "pt": "Estrutura da oração errada", "es": "Estructura de la oración incorrecta"},
    "r.tcat.lexical_choice": {"en": "Word choice", "ko": "어휘 선택 부적절", "pt": "Escolha de palavra", "es": "Elección de palabra"},
    "r.tcat.other": {"en": "Other (check it yourself)", "ko": "기타 (직접 확인 필요)", "pt": "Outro (confira você mesmo)", "es": "Otro (revísalo tú)"},
    "r.tcat.no_error": {"en": "No clear error", "ko": "명확한 에러 없음", "pt": "Nenhum erro claro", "es": "Ningún error claro"},
    "r.judge.no_speech": {
        "en": "One of the videos has no recognised speech, so there was nothing to compare.",
        "ko": "한쪽 영상에서 말소리가 인식되지 않아 비교할 내용이 없습니다.",
        "pt": "Um dos vídeos não tem fala reconhecida, então não havia o que comparar.",
        "es": "Uno de los videos no tiene habla reconocida, así que no había nada que comparar.",
    },
    "r.judge.no_key": {
        "en": "The translation check needs a judge: add a Claude, Gemini or ChatGPT key in Settings → API keys (or the "
              ".env file), or download the local checker in Settings → Models, then run again.",
        "ko": "번역 검토에는 판정 모델이 필요합니다. 설정 → API 키(또는 .env 파일)에 Claude, Gemini, ChatGPT 키 중 하나를 "
              "추가하거나, 설정 → 모델에서 로컬 검사 모델을 내려받은 뒤 다시 실행하세요.",
        "pt": "A verificação da tradução precisa de um avaliador: adicione uma chave do Claude, do Gemini ou do ChatGPT em "
              "Configurações → Chaves de API (ou no arquivo .env), ou baixe o verificador local em Configurações → Modelos, "
              "e execute de novo.",
        "es": "La revisión de la traducción necesita un evaluador: añade una clave de Claude, Gemini o ChatGPT en Ajustes "
              "→ Claves de API (o en el archivo .env), o descarga el comprobador local en Ajustes → Modelos, y "
              "vuelve a ejecutarlo.",
    },
    "r.judge.bad_key": {
        "en": "{model} rejected the API key. Check the key in Settings → API keys (or the .env file) and run again.",
        "ko": "{model} 서비스가 API 키를 거부했습니다. 설정 → API 키(또는 .env 파일)에서 키를 확인하고 다시 실행하세요.",
        "pt": "O {model} recusou a chave de API. Confira a chave em Configurações → Chaves de API (ou no arquivo .env) e "
              "execute de novo.",
        "es": "{model} rechazó la clave de API. Revisa la clave en Ajustes → Claves de API (o en el archivo .env) y "
              "vuelve a ejecutar.",
    },
    "r.judge.daily_quota": {"en": "{model} didn't check the translation: this API key has used up today's requests (a free key can allow as few as 20 a day for each model). Run the evaluation again after the daily reset (midnight US Pacific time), turn on billing for the key, or choose another checker. The other results are not affected.", "ko": "{model} 번역 검사를 하지 못했습니다. 이 API 키의 오늘 요청 횟수를 모두 썼습니다(무료 키는 모델마다 하루 20번 정도만 가능할 수 있음). 매일 초기화된 뒤(미국 태평양 시간 자정) 다시 평가하거나, 키에 결제를 켜거나, 다른 검사기를 고르세요. 다른 결과에는 영향이 없습니다.", "pt": "O {model} não verificou a tradução: esta chave de API usou todos os pedidos de hoje (uma chave gratuita pode permitir apenas 20 por dia para cada modelo). Rode a avaliação de novo depois da renovação diária (meia-noite no horário do Pacífico dos EUA), ative o faturamento da chave ou escolha outro verificador. Os outros resultados não são afetados.", "es": "{model} no revisó la traducción: esta clave de API agotó las solicitudes de hoy (una clave gratuita puede permitir solo 20 al día por modelo). Vuelve a evaluar tras el reinicio diario (medianoche, hora del Pacífico de EE. UU.), activa la facturación de la clave o elige otro revisor. Los demás resultados no se ven afectados."},
    "r.judge.incomplete": {
        "en": "{model} evaluated only {done} of {total} lines, even when asked again, so the translation isn't graded: a "
              "partial review would look complete. Run the evaluation again; the other results are not affected.",
        "ko": "{model} 모델이 {total}개 줄 중 {done}개 줄만 평가했습니다(다시 요청해도 마찬가지). 일부만 본 결과가 전체처럼 "
              "보이지 않도록 번역은 평가하지 않습니다. 다시 평가해 보세요. 다른 결과에는 영향이 없습니다.",
        "pt": "{model} avaliou só {done} de {total} falas, mesmo pedindo de novo, então a tradução não é avaliada: uma "
              "revisão parcial pareceria completa. Rode a avaliação de novo; os outros resultados não são afetados.",
        "es": "{model} evaluó solo {done} de {total} frases, incluso al pedírselo de nuevo, así que la traducción no se "
              "evalúa: una revisión parcial parecería completa. Vuelve a evaluar; los demás resultados no se ven afectados.",
    },
    "r.judge.busy": {
        "en": "{model} is busy right now (it was tried several times). Run the evaluation again in a minute; the other "
              "results are not affected.",
        "ko": "{model} 서비스가 지금 혼잡합니다(여러 번 시도함). 1분 뒤 다시 평가해 보세요. 다른 결과에는 영향이 없습니다.",
        "pt": "O {model} está ocupado agora (foram feitas várias tentativas). Rode a avaliação de novo em um minuto; os "
              "outros resultados não são afetados.",
        "es": "{model} está ocupado ahora (se intentó varias veces). Vuelve a evaluar en un minuto; los demás resultados "
              "no se ven afectados.",
    },
    "r.judge.unreachable": {
        "en": "{model} couldn't be reached. Check the internet connection and run again; the other results are not "
              "affected.",
        "ko": "{model} 서비스에 연결할 수 없습니다. 인터넷 연결을 확인하고 다시 실행하세요. 다른 결과에는 영향이 없습니다.",
        "pt": "Não foi possível acessar o {model}. Confira a conexão com a internet e execute de novo; os outros "
              "resultados não são afetados.",
        "es": "No se pudo contactar con {model}. Revisa la conexión a internet y vuelve a ejecutar; los demás resultados "
              "no se ven afectados.",
    },
    "r.judge.error": {
        "en": "{model} returned an error, so the translation wasn't checked. The other results are not affected.",
        "ko": "{model} 서비스에서 오류가 발생해 번역을 검토하지 못했습니다. 다른 결과에는 영향이 없습니다.",
        "pt": "O {model} retornou um erro, então a tradução não foi verificada. Os outros resultados não são afetados.",
        "es": "{model} devolvió un error, así que no se revisó la traducción. Los demás resultados no se ven afectados.",
    },
    "r.judge.declined": {
        "en": "{model} declined to review this content, so the translation wasn't checked.",
        "ko": "{model} 서비스가 이 내용의 검토를 거절해 번역을 확인하지 못했습니다.",
        "pt": "O {model} se recusou a revisar este conteúdo, então a tradução não foi verificada.",
        "es": "{model} se negó a revisar este contenido, así que no se revisó la traducción.",
    },
    "r.judge.cut_off": {
        "en": "{model}'s review was cut off before it finished, so the translation wasn't checked.",
        "ko": "{model}의 검토가 끝나기 전에 끊겨 번역을 확인하지 못했습니다.",
        "pt": "A revisão do {model} foi interrompida antes de terminar, então a tradução não foi verificada.",
        "es": "La revisión de {model} se cortó antes de terminar, así que no se revisó la traducción.",
    },
    "r.judge.unreadable": {
        "en": "{model}'s review couldn't be read, so the translation wasn't checked.",
        "ko": "{model}의 검토 결과를 읽을 수 없어 번역을 확인하지 못했습니다.",
        "pt": "Não foi possível ler a revisão do {model}, então a tradução não foi verificada.",
        "es": "No se pudo leer la revisión de {model}, así que no se revisó la traducción.",
    },

    # ----- video file -----
    "r.file.ok": {
        "en": "The dub keeps the original picture ({res}, {fps} fps) and has an audio track, so only the voice was changed.",
        "ko": "더빙 영상이 원본 화면({res}, {fps} fps)을 그대로 유지하고 오디오 트랙도 있습니다. 목소리만 바뀌었습니다.",
        "pt": "A dublagem mantém a imagem original ({res}, {fps} fps) e tem faixa de áudio, então só a voz mudou.",
        "es": "El doblaje mantiene la imagen original ({res}, {fps} fps) y tiene pista de audio, así que solo cambió la voz.",
    },
    "r.file.unreadable": {
        "en": "The dubbed file can't be read; it may be damaged.", "ko": "더빙 파일을 읽을 수 없습니다. 손상되었을 수 있습니다.",
        "pt": "O arquivo dublado não pode ser lido; ele pode estar danificado.",
        "es": "El archivo doblado no se puede leer; puede estar dañado.",
    },
    "r.file.no_audio": {
        "en": "The dubbed file has no audio track, so viewers would hear nothing.",
        "ko": "더빙 파일에 오디오 트랙이 없어 시청자에게 아무 소리도 들리지 않습니다.",
        "pt": "O arquivo dublado não tem faixa de áudio, então o público não ouviria nada.",
        "es": "El archivo doblado no tiene pista de audio, así que no se oiría nada.",
    },
    "r.file.resolution": {
        "en": "The picture size changed from {orig} to {dub}.", "ko": "화면 크기가 {orig}에서 {dub}로 바뀌었습니다.",
        "pt": "O tamanho da imagem mudou de {orig} para {dub}.", "es": "El tamaño de la imagen cambió de {orig} a {dub}.",
    },
    "r.file.fps": {
        "en": "The frame rate changed from {orig} to {dub} fps, which can make motion look different.",
        "ko": "프레임 속도가 {orig}에서 {dub} fps로 바뀌어 움직임이 달라 보일 수 있습니다.",
        "pt": "A taxa de quadros mudou de {orig} para {dub} fps, o que pode deixar o movimento diferente.",
        "es": "La velocidad de fotogramas cambió de {orig} a {dub} fps, lo que puede hacer que el movimiento se vea distinto.",
    },
    "r.file.na": {
        "en": "The video files weren't inspected in this run.", "ko": "이번 실행에서는 영상 파일을 점검하지 않았습니다.",
        "pt": "Os arquivos de vídeo não foram inspecionados nesta execução.",
        "es": "Los archivos de video no se revisaron en esta ejecución.",
    },
    "r.file.audio_yes": {"en": "audio ✓", "ko": "오디오 ✓", "pt": "áudio ✓", "es": "audio ✓"},
    "r.file.audio_no": {"en": "no audio", "ko": "오디오 없음", "pt": "sem áudio", "es": "sin audio"},
    "r.g.lip_sync": {
        "en": "Good when the lips line up in {good}% or more of the moments checked, Poor at {poor}% or less, Needs review in "
              "between. Up to {n} moments with a face and speech in both videos are checked; a moment lines up when the "
              "lips match the sound within {sec} s of where they do in the original.",
        "ko": "확인한 순간 중 입 모양이 맞는 비율이 {good}% 이상이면 좋음, {poor}% 이하면 미흡, 그 사이면 검토 필요입니다. 두 "
              "영상 모두 얼굴과 음성이 있는 순간을 최대 {n}개 확인하며, 입 모양이 원본에서와 같은 위치의 {sec}초 안에서 소리와 "
              "맞으면 맞는 순간으로 봅니다.",
        "pt": "Bom quando os lábios combinam em {good}% ou mais dos momentos verificados, Ruim com {poor}% ou menos, "
              "Precisa de revisão entre os dois. São verificados até {n} momentos com rosto e fala nos dois vídeos; um momento "
              "combina quando os lábios acompanham o som a até {sec} s de onde acompanham no original.",
        "es": "Bien cuando los labios coinciden en el {good}% o más de los momentos revisados, Deficiente con el {poor}% o "
              "menos, Necesita revisión entre medias. Se revisan hasta {n} momentos con cara y voz en los dos videos; un momento "
              "coincide cuando los labios siguen el sonido a menos de {sec} s de donde lo hacen en el original.",
    },
    "r.g.file": {
        "en": "Good when the picture size and frame rate match the original and there is an audio track.",
        "ko": "화면 크기와 프레임 속도가 원본과 같고 오디오 트랙이 있으면 좋음입니다.",
        "pt": "Bom se o tamanho da imagem e a taxa de quadros são iguais aos do original e há faixa de áudio.",
        "es": "Bien si el tamaño de la imagen y la velocidad de fotogramas coinciden con el original y hay pista de audio.",
    },

    # ----- pairing: same video, time shift, coverage (dubeval/pairing.py) -----
    "r.m.same_video": {"en": "Same video", "ko": "같은 영상", "pt": "Mesmo vídeo", "es": "Mismo video"},
    "r.m.time_shift": {"en": "Time shift", "ko": "시간 어긋남", "pt": "Deslocamento de tempo", "es": "Desfase de tiempo"},
    "r.m.coverage": {"en": "Coverage", "ko": "포함 범위", "pt": "Cobertura", "es": "Cobertura"},
    "r.pair.disp_match": {"en": "{pct}% of frames match", "ko": "프레임 {pct}% 일치", "pt": "{pct}% dos quadros coincidem",
                          "es": "{pct}% de los fotogramas coinciden"},
    "r.pair.disp_sound": {"en": "background sound matches", "ko": "배경음 일치", "pt": "o som de fundo coincide",
                          "es": "el sonido de fondo coincide"},
    "r.pair.disp_none": {"en": "none", "ko": "없음", "pt": "nenhum", "es": "ninguno"},
    "r.pair.disp_corrected": {"en": "{sec} s (corrected)", "ko": "{sec}초 (보정됨)", "pt": "{sec} s (corrigido)",
                              "es": "{sec} s (corregido)"},
    "r.pair.disp_coverage": {"en": "{pct}% of the original", "ko": "원본의 {pct}%", "pt": "{pct}% do original",
                             "es": "{pct}% del original"},
    "r.pair.same": {
        "en": "The dub shows the same picture as the original ({pct}% of the sampled frames match), so the two can be "
              "compared.",
        "ko": "더빙 영상의 화면이 원본과 같습니다(샘플 프레임의 {pct}% 일치). 두 영상을 비교할 수 있습니다.",
        "pt": "A dublagem mostra a mesma imagem do original ({pct}% dos quadros amostrados coincidem), então os dois "
              "podem ser comparados.",
        "es": "El doblaje muestra la misma imagen que el original (coincide el {pct}% de los fotogramas muestreados), así "
              "que se pueden comparar.",
    },
    "r.pair.same_sound": {
        "en": "One file has no picture, but the background sound matches the original's, so they're treated as the same "
              "video.",
        "ko": "한쪽 파일에 화면이 없지만 배경음이 원본과 일치해 같은 영상으로 봅니다.",
        "pt": "Um dos arquivos não tem imagem, mas o som de fundo coincide com o do original, então são tratados como o "
              "mesmo vídeo.",
        "es": "Uno de los archivos no tiene imagen, pero el sonido de fondo coincide con el del original, así que se "
              "tratan como el mismo video.",
    },
    "r.pair.unsure": {
        "en": "Only {pct}% of the sampled frames match the original's, so it isn't clear these are the same video. Check "
              "that you chose the right files; if you did, the dub may be cropped, re-edited or covered with graphics.",
        "ko": "샘플 프레임의 {pct}%만 원본과 일치해 같은 영상인지 확실하지 않습니다. 파일을 올바르게 골랐는지 확인하세요. "
              "맞다면 더빙 영상이 잘렸거나 다시 편집되었거나 그래픽으로 가려졌을 수 있습니다.",
        "pt": "Só {pct}% dos quadros amostrados coincidem com os do original, então não está claro se é o mesmo vídeo. "
              "Confira se escolheu os arquivos certos; se sim, a dublagem pode ter sido recortada, reeditada ou coberta "
              "por gráficos.",
        "es": "Solo el {pct}% de los fotogramas muestreados coincide con el original, así que no está claro que sea el "
              "mismo video. Comprueba que elegiste los archivos correctos; si es así, el doblaje puede estar recortado, "
              "reeditado o cubierto con gráficos.",
    },
    "r.pair.unsure_sound": {
        "en": "One file has no picture and the background sounds don't clearly match, so DubEval can't confirm these "
              "are the same video.",
        "ko": "한쪽 파일에 화면이 없고 배경음도 뚜렷하게 일치하지 않아 같은 영상인지 확인할 수 없습니다.",
        "pt": "Um dos arquivos não tem imagem e os sons de fundo não coincidem claramente, então o DubEval não consegue "
              "confirmar que é o mesmo vídeo.",
        "es": "Uno de los archivos no tiene imagen y los sonidos de fondo no coinciden con claridad, así que DubEval no "
              "puede confirmar que sea el mismo video.",
    },
    "r.pair.different": {
        "en": "The pictures don't match ({pct}% of the sampled frames), so these look like different videos. The results "
              "below compare unrelated videos and mean little.",
        "ko": "화면이 일치하지 않아(샘플 프레임의 {pct}%) 서로 다른 영상으로 보입니다. 아래 결과는 관련 없는 영상을 비교한 "
              "것이라 의미가 거의 없습니다.",
        "pt": "As imagens não coincidem ({pct}% dos quadros amostrados), então parecem vídeos diferentes. Os resultados "
              "abaixo comparam vídeos sem relação e dizem pouco.",
        "es": "Las imágenes no coinciden ({pct}% de los fotogramas muestreados), así que parecen videos distintos. Los "
              "resultados de abajo comparan videos sin relación y significan poco.",
    },
    "r.pair.shift_none": {
        "en": "The dub's content starts at the same moment as the original's, so no shift was needed.",
        "ko": "더빙 영상의 내용이 원본과 같은 순간에 시작해 보정이 필요 없었습니다.",
        "pt": "O conteúdo da dublagem começa no mesmo momento que o do original, então nenhum ajuste foi necessário.",
        "es": "El contenido del doblaje empieza en el mismo momento que el del original, así que no hizo falta ajustar nada.",
    },
    "r.pair.shift_small": {
        "en": "The dub is offset by {sec} s, too little to matter, so nothing was corrected.",
        "ko": "더빙 영상이 {sec}초 어긋나 있지만 무시할 만큼 작아 보정하지 않았습니다.",
        "pt": "A dublagem está deslocada {sec} s, pouco demais para importar, então nada foi corrigido.",
        "es": "El doblaje está desfasado {sec} s, demasiado poco para importar, así que no se corrigió nada.",
    },
    "r.pair.shift_later": {
        "en": "The same moment comes {sec} s later in the dub than in the original. DubEval corrected for it, so every "
              "time in this report is the original's.",
        "ko": "같은 장면이 원본보다 더빙 영상에서 {sec}초 늦게 나옵니다. DubEval이 이를 보정했으므로 이 보고서의 모든 시간은 "
              "원본 기준입니다.",
        "pt": "O mesmo momento aparece {sec} s mais tarde na dublagem do que no original. O DubEval corrigiu isso, então "
              "todos os tempos deste relatório são os do original.",
        "es": "El mismo momento aparece {sec} s más tarde en el doblaje que en el original. DubEval lo corrigió, así que "
              "todos los tiempos de este informe son los del original.",
    },
    "r.pair.shift_earlier": {
        "en": "The same moment comes {sec} s earlier in the dub than in the original. DubEval corrected for it, so every "
              "time in this report is the original's.",
        "ko": "같은 장면이 원본보다 더빙 영상에서 {sec}초 일찍 나옵니다. DubEval이 이를 보정했으므로 이 보고서의 모든 시간은 "
              "원본 기준입니다.",
        "pt": "O mesmo momento aparece {sec} s mais cedo na dublagem do que no original. O DubEval corrigiu isso, então "
              "todos os tempos deste relatório são os do original.",
        "es": "El mismo momento aparece {sec} s antes en el doblaje que en el original. DubEval lo corrigió, así que "
              "todos los tiempos de este informe son los del original.",
    },
    "r.pair.shift_parts": {
        "en": "The dub's parts sit at different time shifts ({shifts} s): it was cut differently. DubEval lined up each "
              "part with the original, so every time in this report is the original's.",
        "ko": "더빙 영상의 부분마다 시간 어긋남이 다릅니다({shifts}초). 편집이 다르게 되었습니다. DubEval이 부분별로 원본에 "
              "맞췄으므로 이 보고서의 모든 시간은 원본 기준입니다.",
        "pt": "As partes da dublagem estão em deslocamentos diferentes ({shifts} s): ela foi editada de outro jeito. O "
              "DubEval alinhou cada parte com o original, então todos os tempos deste relatório são os do original.",
        "es": "Las partes del doblaje están en desfases distintos ({shifts} s): se editó de otra forma. DubEval alineó "
              "cada parte con el original, así que todos los tiempos de este informe son los del original.",
    },
    "r.pair.shift_drift": {
        "en": "The dub's picture drifts against the original, between {low} and {high} s: it was slowed down or sped up in "
              "places. DubEval followed the drift, so every time in this report is the original's.",
        "ko": "더빙 영상의 화면이 원본과 {low}초에서 {high}초 사이로 조금씩 어긋납니다. 군데군데 느리거나 빠르게 바뀌었습니다. "
              "DubEval이 이 어긋남을 따라갔으므로 이 보고서의 모든 시간은 원본 기준입니다.",
        "pt": "A imagem da dublagem se desloca em relação ao original, entre {low} e {high} s: ela foi desacelerada ou acelerada "
              "em alguns trechos. O DubEval acompanhou esse deslocamento, então todos os tempos deste relatório são os do original.",
        "es": "La imagen del doblaje se desplaza respecto al original, entre {low} y {high} s: se ralentizó o aceleró en algunos "
              "tramos. DubEval siguió ese desplazamiento, así que todos los tiempos de este informe son los del original.",
    },
    "r.pair.disp_drift": {"en": "{low} to {high} s, followed", "ko": "{low}초~{high}초, 따라감",
                          "pt": "{low} a {high} s, acompanhado", "es": "{low} a {high} s, seguido"},
    "r.pair.disp_parts": {"en": "{n} parts, each corrected", "ko": "{n}개 부분, 각각 보정됨",
                          "pt": "{n} partes, cada uma corrigida", "es": "{n} partes, cada una corregida"},
    "r.pair.cov_full": {
        "en": "Every part of the original is in the dub.",
        "ko": "원본의 모든 부분이 더빙 영상에 들어 있습니다.",
        "pt": "Todas as partes do original estão na dublagem.",
        "es": "Todas las partes del original están en el doblaje.",
    },
    "r.pair.cov_missing_one": {
        "en": "1 part of the original ({sec} s) isn't in the dub; it's listed under Things to check.",
        "ko": "원본 중 1곳({sec}초)이 더빙 영상에 없습니다. 확인할 사항에 표시했습니다.",
        "pt": "1 parte do original ({sec} s) não está na dublagem; ela aparece em Pontos a verificar.",
        "es": "1 parte del original ({sec} s) no está en el doblaje; aparece en Cosas que revisar.",
    },
    "r.pair.cov_missing_many": {
        "en": "{n} parts of the original ({sec} s in all) aren't in the dub; they're listed under Things to "
              "check.",
        "ko": "원본 중 {n}곳(합계 {sec}초)이 더빙 영상에 없습니다. 확인할 사항에 표시했습니다.",
        "pt": "{n} partes do original ({sec} s no total) não estão na dublagem; elas aparecem em Pontos a "
              "verificar.",
        "es": "{n} partes del original ({sec} s en total) no están en el doblaje; aparecen en Cosas que "
              "revisar.",
    },
    "r.pair.cut": {
        "en": "The dub is also cut differently: its parts sit at different time shifts, so DubEval lined up each part "
              "with the original separately.",
        "ko": "더빙 영상의 편집도 다릅니다. 부분마다 시간 어긋남이 달라 DubEval이 부분별로 원본에 맞춰 정렬했습니다.",
        "pt": "A dublagem também foi editada de outro jeito: as partes estão em deslocamentos diferentes, então o "
              "DubEval alinhou cada parte com o original separadamente.",
        "es": "El doblaje también está editado de otra forma: sus partes están en desfases distintos, así que DubEval "
              "alineó cada parte con el original por separado.",
    },
    "r.pair.na": {
        "en": "The two files' pictures and sound couldn't be compared, so the same-video check wasn't done.",
        "ko": "두 파일의 화면과 소리를 비교할 수 없어 같은 영상인지 확인하지 못했습니다.",
        "pt": "Não foi possível comparar as imagens e o som dos dois arquivos, então a verificação de mesmo vídeo não foi feita.",
        "es": "No se pudieron comparar las imágenes y el sonido de los dos archivos, así que no se comprobó si son el mismo video.",
    },
    "r.pair.cov_na": {
        "en": "Coverage needs a picture in both files.",
        "ko": "포함 범위는 두 파일 모두에 화면이 있어야 확인할 수 있습니다.",
        "pt": "A cobertura precisa de imagem nos dois arquivos.",
        "es": "La cobertura necesita imagen en ambos archivos.",
    },
    "r.g.same_video": {
        "en": "Good when at least {good}% of the sampled frames match the original's at the best time shift (or, when a "
              "file has no picture, the background sound matches), Needs review from {check}%, otherwise Poor.",
        "ko": "가장 잘 맞는 시간 어긋남에서 샘플 프레임의 {good}% 이상이 원본과 일치하면(화면이 없는 파일이면 배경음이 "
              "일치하면) 좋음, {check}% 이상이면 검토 필요, 그 미만이면 미흡입니다.",
        "pt": "Bom quando pelo menos {good}% dos quadros amostrados coincidem com os do original no melhor deslocamento "
              "(ou, se um arquivo não tem imagem, o som de fundo coincide), Precisa de revisão a partir de {check}%, senão Ruim.",
        "es": "Bien cuando al menos el {good}% de los fotogramas muestreados coincide con el original en el mejor desfase "
              "(o, si un archivo no tiene imagen, el sonido de fondo coincide), Necesita revisión desde el {check}%, si no Deficiente.",
    },
    "r.g.time_shift": {
        "en": "For information: found by matching the pictures, then the background sound to about 0.01 s; shifts under "
              "{min} s are left alone.",
        "ko": "참고용입니다. 화면을 맞춘 뒤 배경음으로 약 0.01초 단위까지 찾습니다. {min}초 미만의 어긋남은 보정하지 않습니다.",
        "pt": "Informativo: encontrado comparando as imagens e depois o som de fundo, com precisão de cerca de 0,01 s; "
              "deslocamentos abaixo de {min} s não são corrigidos.",
        "es": "Informativo: se encuentra comparando las imágenes y luego el sonido de fondo, con una precisión de unos "
              "0,01 s; los desfases de menos de {min} s no se corrigen.",
    },
    "r.g.coverage": {
        "en": "Good when at least {good}% of the original is found in the dub, Needs review from {check}%, otherwise Poor.",
        "ko": "원본의 {good}% 이상이 더빙 영상에 있으면 좋음, {check}% 이상이면 검토 필요, 그 미만이면 미흡입니다.",
        "pt": "Bom quando pelo menos {good}% do original está na dublagem, Precisa de revisão a partir de {check}%, senão Ruim.",
        "es": "Bien cuando al menos el {good}% del original está en el doblaje, Necesita revisión desde el {check}%, si no Deficiente.",
    },
    "r.m.sound_sync": {"en": "Sound in sync with the picture", "ko": "소리와 화면 싱크", "pt": "Som em sincronia com a imagem",
                       "es": "Sonido sincronizado con la imagen"},
    "r.sync.good": {"en": "The dub's sound is in step with its picture.",
                    "ko": "더빙 소리가 화면과 맞습니다.",
                    "pt": "O som da dublagem está em sincronia com a imagem.",
                    "es": "El sonido del doblaje va al ritmo de la imagen."},
    "r.sync.late": {"en": "The dub's sound is {sec} s behind its picture: viewers hear everything after they see it. "
                           "Shift the dub's audio earlier and export again.",
                    "ko": "더빙 소리가 화면보다 {sec}초 늦습니다. 시청자는 장면을 본 뒤에 소리를 듣게 됩니다. 더빙 오디오를 앞으로 당겨 다시 내보내세요.",
                    "pt": "O som da dublagem está {sec} s atrás da imagem: o público ouve tudo depois de ver. Adiante o "
                          "áudio da dublagem e exporte de novo.",
                    "es": "El sonido del doblaje va {sec} s por detrás de la imagen: el público oye todo después de verlo. "
                          "Adelanta el audio del doblaje y vuelve a exportar."},
    "r.sync.early": {"en": "The dub's sound is {sec} s ahead of its picture: viewers hear everything before they see it. "
                            "Shift the dub's audio later and export again.",
                     "ko": "더빙 소리가 화면보다 {sec}초 빠릅니다. 시청자는 장면을 보기 전에 소리를 듣게 됩니다. 더빙 오디오를 뒤로 밀어 다시 내보내세요.",
                     "pt": "O som da dublagem está {sec} s à frente da imagem: o público ouve tudo antes de ver. Atrase o "
                           "áudio da dublagem e exporte de novo.",
                     "es": "El sonido del doblaje va {sec} s por delante de la imagen: el público oye todo antes de verlo. "
                           "Retrasa el audio del doblaje y vuelve a exportar."},
    "r.sync.na_short": {"en": "Not measured: the video is shorter than {sec} s, too short to compare the soundtracks reliably.",
                        "ko": "측정하지 않음: 영상 길이가 {sec}초 미만이라 두 소리를 믿을 만하게 비교할 수 없습니다.",
                        "pt": "Não medido: o vídeo tem menos de {sec} s, curto demais para comparar as trilhas com segurança.",
                        "es": "No medido: el video dura menos de {sec} s, demasiado poco para comparar las pistas con fiabilidad."},
    "r.sync.na_shared": {"en": "Not measured: the dub doesn't keep enough of the original's background sound to line the two "
                                "up (for example, the music was replaced).",
                         "ko": "측정하지 않음: 더빙에 원본의 배경음이 충분히 남아 있지 않아 두 소리를 맞춰 볼 수 없습니다 (예: 음악이 바뀜).",
                         "pt": "Não medido: a dublagem não mantém som de fundo suficiente do original para alinhar os dois "
                               "(por exemplo, a música foi trocada).",
                         "es": "No medido: el doblaje no conserva suficiente sonido de fondo del original para alinearlos "
                               "(por ejemplo, se cambió la música)."},
    "r.g.sound_sync": {"en": "The background sound the dub keeps from the original (music, effects) is lined up with the "
                              "original's, and compared with where the picture lines up. Good under {check} s apart, Needs review "
                              "from {check} s, Poor from {poor} s.",
                       "ko": "더빙에 남아 있는 원본 배경음(음악, 효과음)을 원본과 맞춰 보고, 화면이 맞는 위치와 비교합니다. 차이가 {check}초 미만이면 좋음, "
                             "{check}초부터 검토 필요, {poor}초부터 미흡입니다.",
                       "pt": "O som de fundo que a dublagem mantém do original (música, efeitos) é alinhado com o do original "
                             "e comparado com o alinhamento da imagem. Bom com menos de {check} s de diferença, Verificar a "
                             "partir de {check} s, Ruim a partir de {poor} s.",
                       "es": "El sonido de fondo que el doblaje conserva del original (música, efectos) se alinea con el del "
                             "original y se compara con el alineamiento de la imagen. Bien con menos de {check} s de "
                             "diferencia, Necesita revisión desde {check} s, Deficiente desde {poor} s."},
    "r.cat.sound_sync": {"en": "sound out of sync", "ko": "소리와 화면 어긋남", "pt": "som fora de sincronia",
                         "es": "sonido desincronizado"},
    "r.int.sound_late": {"en": "The whole dub: its sound is {sec} s behind the picture.",
                         "ko": "더빙 전체: 소리가 화면보다 {sec}초 늦습니다.",
                         "pt": "A dublagem inteira: o som está {sec} s atrás da imagem.",
                         "es": "Todo el doblaje: el sonido va {sec} s por detrás de la imagen."},
    "r.int.sound_early": {"en": "The whole dub: its sound is {sec} s ahead of the picture.",
                          "ko": "더빙 전체: 소리가 화면보다 {sec}초 빠릅니다.",
                          "pt": "A dublagem inteira: o som está {sec} s à frente da imagem.",
                          "es": "Todo el doblaje: el sonido va {sec} s por delante de la imagen."},
    "r.cat.missing_in_dub": {"en": "missing from the dub", "ko": "더빙에서 빠짐", "pt": "ausente na dublagem",
                             "es": "falta en el doblaje"},
    "r.int.missing_in_dub": {
        "en": "This part of the original ({sec} s) isn't in the dub: it was cut or replaced.",
        "ko": "원본의 이 부분({sec}초)이 더빙 영상에 없습니다. 잘렸거나 다른 장면으로 바뀌었습니다.",
        "pt": "Esta parte do original ({sec} s) não está na dublagem: foi cortada ou substituída.",
        "es": "Esta parte del original ({sec} s) no está en el doblaje: se cortó o se reemplazó.",
    },

    # ----- line by line: length and overruns (evaluate.line_timing) -----
    "r.m.line_length": {"en": "Line length", "ko": "대사 길이", "pt": "Duração das falas", "es": "Duración de las frases"},
    "r.m.line_overrun": {"en": "Lines running over", "ko": "다음 대사 침범", "pt": "Falas que invadem a próxima",
                         "es": "Frases que invaden la siguiente"},
    "r.line.display": {"en": "{ok} of {n} lines fit", "ko": "{n}개 중 {ok}개 대사 맞음", "pt": "{ok} de {n} falas cabem",
                       "es": "{ok} de {n} frases encajan"},
    "r.line.good": {
        "en": "{ok} of {n} lines are within ±{band}% of the original's length, so the dub fits the original's timing line "
              "by line.",
        "ko": "대사 {n}개 중 {ok}개가 원본 길이의 ±{band}% 안에 있어 더빙이 대사마다 원본 타이밍에 맞습니다.",
        "pt": "{ok} de {n} falas estão dentro de ±{band}% da duração original, então a dublagem acompanha o tempo do "
              "original fala por fala.",
        "es": "{ok} de {n} frases están dentro de ±{band}% de la duración original, así que el doblaje sigue el tiempo "
              "del original frase por frase.",
    },
    "r.line.bad": {
        "en": "{bad} of {n} lines differ from the original's length by more than {band}% ({long} longer, "
              "{short} shorter). A line that's too long gets rushed or cut; one that's too short leaves the "
              "speaker's mouth moving in silence. They're listed under Things to check.",
        "ko": "대사 {n}개 중 {bad}개가 원본 길이와 {band}% 넘게 다릅니다(길어짐 {long}개, 짧아짐 {short}개). 너무 긴 대사는 빨라지거나 잘리고, 너무 짧은 "
              "대사는 입은 움직이는데 소리가 없습니다. 확인할 사항에 표시했습니다.",
        "pt": "{bad} de {n} falas diferem da duração original em mais de {band}% ({long} mais longas, {short} "
              "mais curtas). Uma fala longa demais fica corrida ou cortada; uma curta demais deixa a boca se "
              "mexendo em silêncio. Elas aparecem em Pontos a verificar.",
        "es": "{bad} de {n} frases difieren de la duración original en más de un {band}% ({long} más largas, "
              "{short} más cortas). Una frase demasiado larga se acelera o se corta; una demasiado corta deja "
              "al hablante moviendo la boca en silencio. Aparecen en Cosas que revisar.",
    },
    "r.line.music": {
        "en": "Not graded: this video is mostly music or effects (speech in {pct}% of it), so recognized words can't time its lines reliably.",
        "ko": "평가하지 않음: 이 영상은 대부분 음악이나 효과음이라(말소리 {pct}%) 인식된 단어로 대사 길이를 믿을 만하게 잴 수 없습니다.",
        "pt": "Não avaliado: este vídeo é quase todo música ou efeitos (fala em {pct}% dele), então as palavras reconhecidas não medem as falas com segurança.",
        "es": "No evaluado: este vídeo es casi todo música o efectos (habla en {pct}% de él), así que las palabras reconocidas no miden las frases con fiabilidad.",
    },
    "r.line.na": {
        "en": "No original line of at least {min} s could be matched with a dub line, so line lengths weren't compared.",
        "ko": "{min}초 이상인 원본 대사를 더빙 대사와 짝지을 수 없어 대사 길이를 비교하지 못했습니다.",
        "pt": "Nenhuma fala original de pelo menos {min} s pôde ser ligada a uma fala da dublagem, então as durações não "
              "foram comparadas.",
        "es": "Ninguna frase original de al menos {min} s se pudo emparejar con una frase del doblaje, así que no se "
              "compararon las duraciones.",
    },
    "r.overrun.none": {
        "en": "No dub line runs into the original's next line.",
        "ko": "다음 원본 대사를 침범하는 더빙 대사가 없습니다.",
        "pt": "Nenhuma fala da dublagem invade a próxima fala do original.",
        "es": "Ninguna frase del doblaje invade la siguiente frase del original.",
    },
    "r.overrun.some_one": {
        "en": "1 dub line keeps going after the original's next line has started, so two lines overlap or the "
              "next one starts late. It's listed under Things to check.",
        "ko": "더빙 대사 1개가 다음 원본 대사가 시작된 뒤에도 이어져 두 대사가 겹치거나 다음 대사가 늦게 시작됩니다. 확인할 사항에 표시했습니다.",
        "pt": "1 fala da dublagem continua depois que a próxima fala do original começou, então as duas se "
              "sobrepõem ou a próxima começa atrasada. Ela aparece em Pontos a verificar.",
        "es": "1 frase del doblaje sigue después de que empieza la siguiente frase del original, así que se "
              "solapan o la siguiente empieza tarde. Aparece en Cosas que revisar.",
    },
    "r.overrun.some_many": {
        "en": "{n} dub lines keep going after the original's next line has started, so lines overlap or start late. "
              "They're listed under Things to check.",
        "ko": "더빙 대사 {n}개가 다음 원본 대사가 시작된 뒤에도 이어져 대사가 겹치거나 늦게 시작됩니다. 확인할 사항에 "
              "표시했습니다.",
        "pt": "{n} falas da dublagem continuam depois que a próxima fala do original começou, então as falas se "
              "sobrepõem ou começam atrasadas. Elas aparecem em Pontos a verificar.",
        "es": "{n} frases del doblaje siguen después de que empieza la siguiente frase del original, así que se solapan "
              "o empiezan tarde. Aparecen en Cosas que revisar.",
    },
    "r.overrun.display_one": {"en": "1 line", "ko": "대사 1개", "pt": "1 fala", "es": "1 frase"},
    "r.overrun.display_many": {"en": "{n} lines", "ko": "대사 {n}개", "pt": "{n} falas", "es": "{n} frases"},
    "r.g.line_length": {
        "en": "Each original line of at least {min} s is compared with the dub speech matched to it, from first to "
              "last word. A line is off when it differs by more than ±{band}% and by at least {diff} s. Good when at least "
              "{good}% of the lines are not off, Needs review from {check}%, otherwise Poor. Poor needs at least {count} lines off.",
        "ko": "{min}초 이상인 원본 대사마다 짝지은 더빙 음성과 첫 단어부터 마지막 단어까지 비교합니다. 길이 차이가 "
              "±{band}% 초과이면서 {diff}초 이상 차이 나면 맞지 않는 대사입니다. 대사의 {good}% 이상이 맞으면 좋음, {check}% 이상이면 검토 필요, 그 미만이면 미흡입니다. 미흡은 맞지 않는 대사가 {count}개 이상일 때만입니다.",
        "pt": "Cada fala original de pelo menos {min} s é comparada com a fala da dublagem ligada a ela, da primeira à "
              "última palavra. Uma fala está fora quando difere mais de ±{band}% e pelo menos {diff} s. Bom quando pelo "
              "menos {good}% das falas não estão fora, Precisa de revisão a partir de {check}%, senão Ruim. Ruim exige pelo menos {count} falas fora.",
        "es": "Cada frase original de al menos {min} s se compara con la voz del doblaje emparejada, de la primera a la "
              "última palabra. Una frase está fuera cuando difiere más de ±{band}% y al menos {diff} s. Bien cuando al "
              "menos el {good}% de las frases no está fuera, Necesita revisión desde el {check}%, si no Deficiente. Deficiente requiere al menos {count} frases fuera.",
    },
    "r.g.line_overrun": {
        "en": "A dub line runs over when it ends more than {sec} s after the original's next line starts. Good when "
              "none does, Needs review up to {share}% of the lines, otherwise Poor. Poor needs at least {count} such lines.",
        "ko": "더빙 대사가 다음 원본 대사 시작 후 {sec}초 넘게 이어지면 침범으로 봅니다. 하나도 없으면 좋음, 대사의 {share}%까지 "
              "검토 필요, 그보다 많으면 미흡입니다. 미흡은 그런 대사가 {count}개 이상일 때만입니다.",
        "pt": "Uma fala da dublagem invade quando termina mais de {sec} s depois do início da próxima fala do original. "
              "Bom quando nenhuma invade, Precisa de revisão até {share}% das falas, senão Ruim. Ruim exige pelo menos {count} falas assim.",
        "es": "Una frase del doblaje invade cuando termina más de {sec} s después de que empiece la siguiente frase del "
              "original. Bien cuando ninguna invade, Necesita revisión hasta el {share}% de las frases, si no Deficiente. Deficiente requiere al menos {count} frases así.",
    },
    "r.cat.line_length": {"en": "line length", "ko": "대사 길이", "pt": "duração da fala", "es": "duración de la frase"},
    "r.cat.line_overrun": {"en": "line runs over", "ko": "대사 침범", "pt": "fala invade a próxima",
                           "es": "frase invade la siguiente"},
    "r.int.line_long": {
        "en": "Line {n}: the dub speaks {d} s against the original's {o} s ({pct}% longer).",
        "ko": "{n}번 대사: 더빙은 {d}초, 원본은 {o}초입니다({pct}% 길어짐).",
        "pt": "Fala {n}: a dublagem dura {d} s contra {o} s do original ({pct}% mais longa).",
        "es": "Frase {n}: el doblaje dura {d} s frente a {o} s del original ({pct}% más larga).",
    },
    "r.int.line_short": {
        "en": "Line {n}: the dub speaks {d} s against the original's {o} s ({pct}% shorter).",
        "ko": "{n}번 대사: 더빙은 {d}초, 원본은 {o}초입니다({pct}% 짧아짐).",
        "pt": "Fala {n}: a dublagem dura {d} s contra {o} s do original ({pct}% mais curta).",
        "es": "Frase {n}: el doblaje dura {d} s frente a {o} s del original ({pct}% más corta).",
    },
    "r.int.line_overrun": {
        "en": "Line {n}: the dub is still speaking {sec} s after the original's next line has started.",
        "ko": "{n}번 대사: 다음 원본 대사가 시작된 뒤에도 더빙이 {sec}초 더 이어집니다.",
        "pt": "Fala {n}: a dublagem ainda fala {sec} s depois do início da próxima fala do original.",
        "es": "Frase {n}: el doblaje sigue hablando {sec} s después de que empiece la siguiente frase del original.",
    },

    # ----- the removed meaning screen: its label stays, old votes are summed under it (qa.py feedback); dub types -----
    "r.m.meaning_screen": {"en": "Meaning similarity (offline)", "ko": "의미 유사도 (오프라인)",
                           "pt": "Semelhança de sentido (offline)", "es": "Similitud de sentido (sin conexión)"},
    "r.cat.meaning_drift": {"en": "meaning may differ", "ko": "의미 다를 수 있음", "pt": "sentido pode diferir",
                            "es": "el sentido puede diferir"},
    "r.m.numbers": {"en": "Numbers", "ko": "숫자", "pt": "Números", "es": "Números"},
    "r.num.good_one": {
        "en": "The line with numbers on both sides says the same numbers as the original.",
        "ko": "양쪽에 숫자가 있는 대사 1개의 숫자가 원본과 같습니다.",
        "pt": "A fala com números dos dois lados diz os mesmos números do original.",
        "es": "La frase con números en ambos lados dice los mismos números que el original.",
    },
    "r.num.good_many": {
        "en": "All {n} lines with numbers on both sides say the same numbers as the original.",
        "ko": "양쪽에 숫자가 있는 대사 {n}개 모두 숫자가 원본과 같습니다.",
        "pt": "As {n} falas com números dos dois lados dizem os mesmos números do original.",
        "es": "Las {n} frases con números en ambos lados dicen los mismos números que el original.",
    },
    "r.num.check_one": {
        "en": "{n} of {total} lines with numbers says a number the original doesn't. Speech recognition can "
              "mishear a number, so listen before you fix it. It's listed under Things to check.",
        "ko": "숫자가 있는 대사 {total}개 중 {n}개에서 원본에 없는 숫자가 들립니다. 음성 인식이 숫자를 잘못 들을 수 있으니 고치기 전에 직접 들어 보세요. 확인할 사항에 "
              "표시했습니다.",
        "pt": "{n} de {total} falas com números diz um número que o original não diz. O reconhecimento de fala "
              "pode ouvir mal um número; ouça antes de corrigir. Ela aparece em Pontos a verificar.",
        "es": "{n} de {total} frases con números dice un número que el original no dice. El reconocimiento de "
              "voz puede oír mal un número; escúchalo antes de corregirlo. Aparece en Cosas que revisar.",
    },
    "r.num.check_many": {
        "en": "{n} of {total} lines with numbers say numbers the original doesn't. Speech recognition can "
              "mishear numbers, so listen before you fix them. They're listed under Things to check.",
        "ko": "숫자가 있는 대사 {total}개 중 {n}개에서 원본에 없는 숫자가 들립니다. 음성 인식이 숫자를 잘못 들을 수 있으니 고치기 전에 직접 들어 보세요. 확인할 사항에 "
              "표시했습니다.",
        "pt": "{n} de {total} falas com números dizem números que o original não diz. O reconhecimento de fala "
              "pode ouvir mal os números; ouça antes de corrigir. Elas aparecem em Pontos a verificar.",
        "es": "{n} de {total} frases con números dicen números que el original no dice. El reconocimiento de "
              "voz puede oír mal los números; escúchalos antes de corregirlos. Aparecen en Cosas que revisar.",
    },
    "r.num.display": {"en": "{changed} of {n} lines differ", "ko": "{n}개 중 {changed}개 다름",
                      "pt": "{changed} de {n} falas diferem", "es": "{changed} de {n} frases difieren"},
    "r.num.words": {
        "en": "Numbers are said as words on one side, so they couldn't be compared.",
        "ko": "한쪽에서 숫자를 글자로 말해 비교할 수 없었습니다.",
        "pt": "Os números aparecem por extenso de um lado, então não puderam ser comparados.",
        "es": "Los números aparecen en palabras en un lado, así que no se pudieron comparar.",
    },
    "r.vq.display": {
        "en": "{dub} vs {orig} original, out of {scale}",
        "ko": "원본 {orig} 대비 {dub} ({scale}점 만점)",
        "pt": "{dub} vs. {orig} do original, numa escala até {scale}",
        "es": "{dub} frente a {orig} del original, sobre {scale}",
    },
    "r.num.words_display": {
        "en": "Not compared (said in words)",
        "ko": "비교 못 함 (숫자를 말로 풀어 씀)",
        "pt": "Não comparados (por extenso)",
        "es": "No comparados (en palabras)",
    },
    "r.num.none": {"en": "Neither side says a number.", "ko": "양쪽 모두 숫자가 없습니다.",
                   "pt": "Nenhum dos lados diz um número.", "es": "Ningún lado dice un número."},
    "r.num.unrecognized": {
        "en": "The dub's language wasn't recognized, so its numbers weren't compared.",
        "ko": "더빙 언어를 인식하지 못해 숫자를 비교하지 않았습니다.",
        "pt": "O idioma da dublagem não foi reconhecido, então os números não foram comparados.",
        "es": "No se reconoció el idioma del doblaje, así que no se compararon los números.",
    },
    "r.g.numbers": {
        "en": "Compares the digits each dub line says (amounts, dates, prices, times) with the original line said at "
              "the same time, without an AI. Only lines with digits on both sides count, so a number said as a word "
              "isn't compared. Needs review when a number the original says has become another in the dub, otherwise Good. Never Poor: "
              "speech recognition can mishear a number.",
        "ko": "더빙 대사가 말하는 숫자(금액, 날짜, 가격, 시간)를 같은 시간의 원본 대사와 AI 없이 비교합니다. 양쪽에 숫자가 "
              "있는 대사만 세므로 글자로 말한 숫자는 비교하지 않습니다. 원본의 숫자가 더빙에서 다른 숫자로 바뀌면 검토 필요, 아니면 "
              "좋음입니다. 음성 인식이 숫자를 잘못 들을 수 있어 미흡은 없습니다.",
        "pt": "Compara os algarismos de cada fala da dublagem (valores, datas, preços, horários) com a fala original no "
              "mesmo momento, sem IA. Só contam as falas com algarismos dos dois lados, então um número por extenso "
              "não é comparado. Precisa de revisão quando uma fala da dublagem diz um número que o original não diz, senão Bom. "
              "Nunca Ruim: o reconhecimento de fala pode ouvir mal um número.",
        "es": "Compara las cifras de cada frase del doblaje (cantidades, fechas, precios, horas) con la frase original "
              "dicha al mismo tiempo, sin IA. Solo cuentan las frases con cifras en ambos lados, así que un número "
              "dicho en palabras no se compara. Necesita revisión cuando una frase del doblaje dice un número que el original no "
              "dice, si no Bien. Nunca Deficiente: el reconocimiento de voz puede oír mal un número.",
    },
    "r.int.number": {
        "en": "Line {n}: the original says {orig}, the dub says {dub}.",
        "ko": "{n}번 대사: 원본 숫자 {orig}, 더빙 숫자 {dub}.",
        "pt": "Fala {n}: o original diz {orig}, a dublagem diz {dub}.",
        "es": "Frase {n}: el original dice {orig}, el doblaje dice {dub}.",
    },
    "r.vs.not_compared_human": {
        "en": "Not compared: this dub was recorded by human voice actors, so a different voice is expected.",
        "ko": "비교하지 않음: 사람 성우가 녹음한 더빙이라 목소리가 다른 것이 정상입니다.",
        "pt": "Não comparada: esta dublagem foi gravada por dubladores humanos, então uma voz diferente é esperada.",
        "es": "No comparada: este doblaje lo grabaron actores de voz, así que se espera una voz distinta.",
    },
    "r.vs.not_compared_stock": {
        "en": "Not compared: this dub uses an AI stock voice, so a different voice is expected.",
        "ko": "비교하지 않음: AI 기본 음성을 쓴 더빙이라 목소리가 다른 것이 정상입니다.",
        "pt": "Não comparada: esta dublagem usa uma voz padrão de IA, então uma voz diferente é esperada.",
        "es": "No comparada: este doblaje usa una voz de IA de catálogo, así que se espera una voz distinta.",
    },
    "r.judge.no_credit": {
        "en": "{model} refused the request because the account has no credit left. Add credit on the provider's "
              "billing page, or use another judge (for example the local one: --judge ollama).",
        "ko": "계정에 크레딧이 남아 있지 않아 {model} 요청이 거절되었습니다. 제공업체의 결제 페이지에서 크레딧을 추가하거나 "
              "다른 판정 모델(예: 로컬 모델 --judge ollama)을 사용하세요.",
        "pt": "O {model} recusou o pedido porque a conta está sem crédito. Adicione crédito na página de cobrança do "
              "provedor ou use outro avaliador (por exemplo, o local: --judge ollama).",
        "es": "{model} rechazó la solicitud porque la cuenta no tiene crédito. Añade crédito en la página de "
              "facturación del proveedor o usa otro evaluador (por ejemplo, el local: --judge ollama).",
    },
    "r.judge.local_slow": {
        "en": "The local judge ({model}) didn't answer within {sec} s. Local models are slow on some computers: close "
              "other programs that use the graphics card, raise DUBEVAL_OLLAMA_TIMEOUT, or use Claude, Gemini or ChatGPT "
              "for this check.",
        "ko": "로컬 판정 모델({model})이 {sec}초 안에 응답하지 않았습니다. 컴퓨터에 따라 로컬 모델은 느릴 수 있습니다. 그래픽 "
              "카드를 쓰는 다른 프로그램을 닫거나, DUBEVAL_OLLAMA_TIMEOUT을 늘리거나, 이 검사에 Claude, Gemini, ChatGPT 중 "
              "하나를 써 보세요.",
        "pt": "O avaliador local ({model}) não respondeu em {sec} s. Modelos locais são lentos em alguns computadores: "
              "feche outros programas que usam a placa de vídeo, aumente DUBEVAL_OLLAMA_TIMEOUT ou use o Claude, o Gemini "
              "ou o ChatGPT nesta verificação.",
        "es": "El evaluador local ({model}) no respondió en {sec} s. Los modelos locales son lentos en algunos equipos: "
              "cierra otros programas que usen la tarjeta gráfica, aumenta DUBEVAL_OLLAMA_TIMEOUT o usa Claude, Gemini o "
              "ChatGPT para esta comprobación.",
    },
    "r.judge.local_down": {
        "en": "The local judge ({model}) couldn't be reached at {url}. Start Ollama (ollama serve), or set "
              "DUBEVAL_OLLAMA_URL to where it runs.",
        "ko": "{url}에서 로컬 판정 모델({model})에 연결할 수 없습니다. Ollama를 실행하거나(ollama serve) "
              "DUBEVAL_OLLAMA_URL을 실행 중인 주소로 설정하세요.",
        "pt": "Não foi possível acessar o avaliador local ({model}) em {url}. Inicie o Ollama (ollama serve) ou defina "
              "DUBEVAL_OLLAMA_URL para onde ele está rodando.",
        "es": "No se pudo contactar con el evaluador local ({model}) en {url}. Inicia Ollama (ollama serve) o define "
              "DUBEVAL_OLLAMA_URL con la dirección donde se ejecuta.",
    },
    "r.judge.no_local_model": {
        "en": "The local judge model ({model}) isn't installed in Ollama. Install it with: ollama pull {model}",
        "ko": "로컬 판정 모델({model})이 Ollama에 설치되어 있지 않습니다. 설치: ollama pull {model}",
        "pt": "O modelo de avaliação local ({model}) não está instalado no Ollama. Instale com: ollama pull {model}",
        "es": "El modelo de evaluación local ({model}) no está instalado en Ollama. Instálalo con: ollama pull {model}",
    },

    # ----- speech that can't be graded (report.speech_problem) -----
    "r.m.speech_found": {"en": "Speech found", "ko": "음성 감지", "pt": "Fala encontrada", "es": "Habla detectada"},
    "r.speech.none_display": {"en": "no speech recognized", "ko": "인식된 음성 없음", "pt": "nenhuma fala reconhecida",
                              "es": "no se reconoció habla"},
    "r.speech.none_dub": {"en": "No speech was recognized in the dub (music, singing or noise?) while the original has speech: a dub without a voice is graded Poor, and the speech, timing and meaning checks couldn't run. Listen to confirm.", "ko": "원본에는 음성이 있는데 더빙에서 인식된 음성이 없습니다(음악, 노래, 잡음?). 목소리가 없는 더빙은 미흡으로 평가하며, 음성·타이밍·의미 검사를 할 수 없었습니다. 직접 들어 확인하세요.", "pt": "Nenhuma fala foi reconhecida na dublagem (música, canto ou ruído?), embora o original tenha fala: uma dublagem sem voz é avaliada como Ruim, e as verificações de fala, tempo e sentido não puderam rodar. Ouça para confirmar.", "es": "No se reconoció habla en el doblaje (¿música, canto o ruido?), aunque el original sí la tiene: un doblaje sin voz se califica como Deficiente, y no se pudieron hacer las comprobaciones de habla, tiempo y sentido. Escúchalo para confirmar."},
    "r.speech.none_original": {
        "en": "No speech was recognized in the original (music, singing or noise?), so the dub couldn't be compared "
              "with it. A person should watch it.",
        "ko": "원본에서 인식된 음성이 없어(음악, 노래, 잡음?) 더빙과 비교할 수 없었습니다. 직접 보고 확인하세요.",
        "pt": "Nenhuma fala foi reconhecida no original (música, canto ou ruído?), então a dublagem não pôde ser "
              "comparada com ele. Uma pessoa deve assistir.",
        "es": "No se reconoció habla en el original (¿música, canto o ruido?), así que el doblaje no se pudo comparar "
              "con él. Una persona debería verlo.",
    },
    "r.g.speech_found": {"en": "Poor when the dub has no recognized speech while the original has (nothing was dubbed); Needs review when the original has none: the checks that need speech can't run.", "ko": "원본에는 음성이 있는데 더빙에 인식된 음성이 전혀 없으면 미흡(더빙되지 않음), 원본에 음성이 없으면 검토 필요입니다. 음성이 필요한 검사를 할 수 없습니다.", "pt": "Ruim quando a dublagem não tem fala reconhecida e o original tem (nada foi dublado); Precisa de revisão quando o original não tem: as verificações que precisam de fala não podem rodar.", "es": "Deficiente cuando el doblaje no tiene habla reconocida y el original sí (no se dobló nada); Necesita revisión cuando el original no la tiene: las comprobaciones que necesitan habla no pueden hacerse."},
    "r.lang.unrecognized": {
        "en": "Speech recognition heard {detected} in the dub instead of {lang}. For less common languages this usually "
              "means recognition failed rather than the dub being in the wrong language, so listen to confirm. The "
              "checks that depend on recognized speech aren't graded.",
        "ko": "음성 인식이 더빙에서 {lang} 대신 {detected}로 들었습니다. 덜 흔한 언어에서는 보통 더빙 언어가 틀린 것이 아니라 "
              "인식이 실패한 것이니 직접 들어 확인하세요. 인식된 음성에 의존하는 검사는 평가하지 않았습니다.",
        "pt": "O reconhecimento de fala ouviu {detected} na dublagem em vez de {lang}. Em idiomas menos comuns isso "
              "geralmente significa que o reconhecimento falhou, não que a dublagem esteja no idioma errado; ouça para "
              "confirmar. As verificações que dependem da fala reconhecida não foram avaliadas.",
        "es": "El reconocimiento de voz oyó {detected} en el doblaje en lugar de {lang}. En idiomas menos comunes esto "
              "suele significar que el reconocimiento falló, no que el doblaje esté en el idioma equivocado; escúchalo "
              "para confirmar. Las comprobaciones que dependen del habla reconocida no se evaluaron.",
    },
    "r.speech.unreliable_timing": {
        "en": "Not graded: speech recognition heard {detected} instead of {lang}, so the recognized speech can't be "
              "trusted. Long silences in the dub are still found, by a voice detector that doesn't need the words.",
        "ko": "평가하지 않음: 음성 인식이 {lang} 대신 {detected}로 들어 인식 결과를 믿을 수 없습니다. 더빙의 긴 무음은 "
              "단어가 필요 없는 음성 감지기로 계속 찾습니다.",
        "pt": "Não avaliado: o reconhecimento de fala ouviu {detected} em vez de {lang}, então a fala reconhecida não é "
              "confiável. Silêncios longos na dublagem ainda são encontrados por um detector de voz, que não precisa "
              "das palavras.",
        "es": "No evaluado: el reconocimiento de voz oyó {detected} en lugar de {lang}, así que el habla reconocida no "
              "es fiable. Los silencios largos del doblaje se siguen encontrando con un detector de voz, que no "
              "necesita las palabras.",
    },
    "r.speech.unreliable": {
        "en": "Not graded: speech recognition heard {detected} instead of {lang}, so the recognized speech can't be "
              "trusted.",
        "ko": "평가하지 않음: 음성 인식이 {lang} 대신 {detected}로 들어 인식 결과를 믿을 수 없습니다.",
        "pt": "Não avaliado: o reconhecimento de fala ouviu {detected} em vez de {lang}, então a fala reconhecida não é "
              "confiável.",
        "es": "No evaluado: el reconocimiento de voz oyó {detected} en lugar de {lang}, así que el habla reconocida no "
              "es fiable.",
    },

    # ----- lip movement -----

    # ----- lip sync (the lip_sync pack) -----
    "r.sync_lips.info": {
        "en": "The lips line up with the dubbed speech in {dub} of {n} moments checked; in the original, {orig} of {n}. "
              "Close to the original means viewers see the mouth say what they hear. A dub without lip sync lines up "
              "about 1 time in 6 by chance.",
        "ko": "확인한 {n}개 순간 중 {dub}개에서 입 모양이 더빙 음성과 맞습니다. 원본은 {n}개 중 {orig}개입니다. 원본에 "
              "가까울수록 시청자가 듣는 말과 입 모양이 일치합니다. 립싱크가 없는 더빙도 우연히 6번에 1번쯤은 맞습니다.",
        "pt": "Os lábios acompanham a fala dublada em {dub} de {n} momentos verificados; no original, em {orig} de {n}. "
              "Perto do original significa que o espectador vê a boca dizer o que ouve. Uma dublagem sem sincronia "
              "labial acerta cerca de 1 vez em 6 por acaso.",
        "es": "Los labios coinciden con la voz doblada en {dub} de {n} momentos revisados; en el original, en {orig} de "
              "{n}. Cerca del original significa que el espectador ve la boca decir lo que oye. Un doblaje sin "
              "sincronía labial coincide por azar alrededor de 1 vez de cada 6.",
    },
    "r.sync_lips.check_hint": {
        "en": "Some moments don't line up: watch the dub's close-ups before delivering it.",
        "ko": "맞지 않는 순간이 있습니다. 전달하기 전에 더빙의 클로즈업 장면을 확인하세요.",
        "pt": "Alguns momentos não combinam: confira os closes da dublagem antes de entregá-la.",
        "es": "Algunos momentos no coinciden: revisa los primeros planos del doblaje antes de entregarlo.",
    },
    "r.sync_lips.poor_hint": {
        "en": "Most moments don't line up, so viewers will see the mouth out of step with the voice: redo the lip sync "
              "before delivering it.",
        "ko": "대부분의 순간이 맞지 않아 시청자에게 입 모양과 목소리가 어긋나 보입니다. 전달하기 전에 립싱크를 다시 하세요.",
        "pt": "A maioria dos momentos não combina, então quem assiste verá a boca fora do tempo da voz: refaça a "
              "sincronia labial antes de entregar.",
        "es": "La mayoría de los momentos no coinciden, así que el público verá la boca desfasada de la voz: rehaz la "
              "sincronía labial antes de entregarlo.",
    },
    "r.sync_lips.late": {
        "en": "The lips do follow the speech, but the sound comes {sec} s after them: check that the sound is in step "
              "with the picture.",
        "ko": "입 모양은 음성을 따라가지만 소리가 입보다 {sec}초 늦습니다. 소리와 화면이 맞는지 확인하세요.",
        "pt": "Os lábios acompanham a fala, mas o som vem {sec} s depois deles: confira se o som está alinhado com a imagem.",
        "es": "Los labios siguen la voz, pero el sonido llega {sec} s después: comprueba que el sonido vaya a la par de la "
              "imagen.",
    },
    "r.sync_lips.early": {
        "en": "The lips do follow the speech, but the sound comes {sec} s before them: check that the sound is in step "
              "with the picture.",
        "ko": "입 모양은 음성을 따라가지만 소리가 입보다 {sec}초 빠릅니다. 소리와 화면이 맞는지 확인하세요.",
        "pt": "Os lábios acompanham a fala, mas o som vem {sec} s antes deles: confira se o som está alinhado com a imagem.",
        "es": "Los labios siguen la voz, pero el sonido llega {sec} s antes: comprueba que el sonido vaya a la par de la "
              "imagen.",
    },
    "r.sync_lips.display": {"en": "{dub} of {n} (original {orig})", "ko": "{n}개 중 {dub}개 (원본 {orig}개)",
                            "pt": "{dub} de {n} (original {orig})", "es": "{dub} de {n} (original {orig})"},
    "r.sync_lips.few_moments": {
        "en": "Not measured: only {n} moments show a face while both videos have speech (at least 8 are needed).",
        "ko": "측정 안 함: 두 영상 모두 음성이 있는 동안 얼굴이 보이는 순간이 {n}개뿐입니다(최소 8개 필요).",
        "pt": "Não medido: só {n} momentos mostram um rosto enquanto os dois vídeos têm fala (são precisos pelo menos 8).",
        "es": "No medido: solo {n} momentos muestran una cara mientras los dos videos tienen voz (se necesitan al menos 8).",
    },
    "r.sync_lips.original_off": {
        "en": "Not measured: even in the original the lips line up with the speech in only {pct} of moments, so the voice "
              "is probably not the person on screen (a narrator or a voice off camera).",
        "ko": "측정 안 함: 원본에서도 입 모양이 음성과 맞는 순간이 {pct}뿐이라, 목소리가 화면 속 인물의 것이 아닐 가능성이 "
              "큽니다(내레이터나 화면 밖 목소리).",
        "pt": "Não medido: mesmo no original os lábios acompanham a fala em só {pct} dos momentos, então a voz provavelmente "
              "não é da pessoa na tela (um narrador ou uma voz fora de cena).",
        "es": "No medido: incluso en el original los labios coinciden con la voz solo en el {pct} de los momentos, así que "
              "la voz probablemente no es de la persona en pantalla (un narrador o una voz fuera de cámara).",
    },
    "r.sync_lips.recut": {
        "en": "Not measured: the dub is cut differently from the original, so its moments can't be matched one to one.",
        "ko": "측정 안 함: 더빙이 원본과 다르게 편집되어 같은 순간끼리 짝지을 수 없습니다.",
        "pt": "Não medido: a dublagem foi editada de outro jeito que o original, então os momentos não se correspondem um a um.",
        "es": "No medido: el doblaje está montado de otra forma que el original, así que sus momentos no se corresponden uno a uno.",
    },
    "r.sync_lips.error": {
        "en": "Not measured: the lip-sync check couldn't read the videos.",
        "ko": "측정 안 함: 립싱크 검사가 영상을 읽지 못했습니다.",
        "pt": "Não medido: a verificação de sincronia labial não conseguiu ler os vídeos.",
        "es": "No medido: la comprobación de sincronía labial no pudo leer los videos.",
    },
    "r.lips.not_lipsynced": {
        "en": "This dub isn't lip-synced, so there are no re-drawn lips to check.",
        "ko": "립싱크 영상이 아니라 다시 그려진 입 모양이 없어 확인할 것이 없습니다.",
        "pt": "Esta dublagem não tem sincronização labial, então não há lábios refeitos para verificar.",
        "es": "Este doblaje no tiene sincronización labial, así que no hay labios regenerados que revisar.",
    },
    "r.lips.no_download": {
        "en": "Lips weren't checked: the lip-sync check needs its download (1.6 GB). Get it under Settings → Models, "
              "then run the evaluation again.",
        "ko": "입 모양은 확인하지 않았습니다. 립싱크 검사를 쓰려면 다운로드(1.6 GB)가 필요합니다. 설정 → 모델에서 받은 뒤 "
              "평가를 다시 실행하세요.",
        "pt": "Os lábios não foram verificados: a verificação da sincronia labial precisa do seu download (1,6 GB). "
              "Baixe-o em Configurações → Modelos e rode a avaliação de novo.",
        "es": "No se comprobaron los labios: la comprobación de la sincronía labial necesita su descarga (1,6 GB). "
              "Descárgala en Ajustes → Modelos y vuelve a ejecutar la evaluación.",
    },
    "r.lips.estimate_removed": {
        "en": "This evaluation used an older, rough lip estimate that DubEval no longer shows because it wasn't "
              "reliable. Run it again with the lip-sync check to grade the lips.",
        "ko": "이 평가는 예전의 대략적인 입 모양 추정을 사용했습니다. 신뢰하기 어려워 DubEval에서 더 이상 표시하지 않습니다. "
              "입 모양을 평가하려면 립싱크 검사를 켜고 다시 실행하세요.",
        "pt": "Esta avaliação usou uma estimativa antiga e aproximada dos lábios, que o DubEval não mostra mais por não "
              "ser confiável. Rode de novo com a verificação da sincronia labial para avaliar os lábios.",
        "es": "Esta evaluación usó una estimación antigua y aproximada de los labios, que DubEval ya no muestra por no "
              "ser fiable. Vuelve a ejecutarla con la comprobación de la sincronía labial para evaluar los labios.",
    },
    "r.lips.short.skipped": {"en": "Off for this run", "ko": "이번 실행에서 꺼짐", "pt": "Desligada nesta execução",
                             "es": "Desactivada en esta ejecución"},
    "r.lips.short.no_download": {"en": "Needs its download", "ko": "다운로드 필요", "pt": "Precisa do download",
                                 "es": "Necesita su descarga"},
    "r.lips.short.not_lipsynced": {"en": "Not a lip-synced dub", "ko": "립싱크 더빙 아님",
                                   "pt": "Dublagem sem sincronização labial", "es": "Doblaje sin sincronización labial"},
    "r.lips.short.estimate_removed": {"en": "Old estimate, not shown", "ko": "예전 추정, 표시 안 함",
                                      "pt": "Estimativa antiga, não exibida", "es": "Estimación antigua, no se muestra"},
    "r.lips.skipped": {
        "en": "Lips weren't checked: the lip check was off for this run. To check them, turn it on under More options "
              "when you start an evaluation (--lipsync on the command line).",
        "ko": "입 모양은 확인하지 않았습니다. 이번 실행에서는 립싱크 검사를 켜지 않았습니다. 확인하려면 평가를 시작할 때 추가 옵션에서 "
              "켜세요(명령줄에서는 --lipsync).",
        "pt": "Os lábios não foram verificados: a verificação estava desligada nesta execução. Para verificá-los, ligue-a "
              "em Mais opções ao iniciar uma avaliação (--lipsync na linha de comando).",
        "es": "No se comprobaron los labios: la comprobación estaba desactivada en esta ejecución. Para comprobarlos, "
              "actívala en Más opciones al iniciar una evaluación (--lipsync en la línea de comandos).",
    },

    # ----- things to check -----
    "r.cat.timing": {"en": "timing", "ko": "타이밍", "pt": "tempo", "es": "momento"},
    "r.cat.clarity": {"en": "clarity", "ko": "명료도", "pt": "clareza", "es": "claridad"},
    "r.cat.missing": {"en": "left out of the translation", "ko": "번역에서 빠짐", "pt": "omitido na tradução",
                      "es": "omitido en la traducción"},
    "r.cat.added": {"en": "added speech", "ko": "추가된 말", "pt": "fala acrescentada", "es": "habla añadida"},
    "r.cat.noise": {"en": "noise", "ko": "잡음", "pt": "ruído", "es": "ruido"},
    "r.cat.long_silence": {"en": "long silence", "ko": "긴 무음", "pt": "silêncio longo", "es": "silencio largo"},
    "r.cat.distortion": {"en": "distortion", "ko": "소리 찌그러짐", "pt": "distorção", "es": "distorsión"},
    "r.cat.loudness_jump": {"en": "loudness jump", "ko": "음량 급변", "pt": "salto de volume", "es": "salto de volumen"},
    "r.cat.wrong_language": {"en": "wrong language", "ko": "다른 언어", "pt": "idioma errado", "es": "idioma incorrecto"},
    "r.cat.mistranslation": {"en": "mistranslation", "ko": "오역", "pt": "erro de tradução", "es": "error de traducción"},
    "r.cat.name_or_number": {"en": "name or number", "ko": "이름·숫자", "pt": "nome ou número", "es": "nombre o número"},
    "r.cat.general": {"en": "Whole video", "ko": "영상 전체", "pt": "Vídeo inteiro", "es": "Todo el video"},
    "r.todo.dub_only": {
        "en": "The dub speaks here, but the original is silent. The voice may not match the picture.",
        "ko": "원본은 조용한데 더빙이 말하고 있습니다. 목소리가 화면과 맞지 않을 수 있습니다.",
        "pt": "A dublagem fala aqui, mas o original está em silêncio. A voz pode não combinar com a imagem.",
        "es": "El doblaje habla aquí, pero el original calla. La voz puede no encajar con la imagen.",
    },
    "r.todo.original_only": {
        "en": "The original speaks here, but the dub is silent. A line may be missing from the dub.",
        "ko": "원본은 말하는데 더빙이 조용합니다. 더빙에서 문장이 빠졌을 수 있습니다.",
        "pt": "O original fala aqui, mas a dublagem está em silêncio. Pode faltar uma fala na dublagem.",
        "es": "El original habla aquí, pero el doblaje calla. Puede faltar una frase en el doblaje.",
    },
    "r.todo.unclear": {
        "en": "This part of the dub is hard to understand: “{text}”. Listen to check the voice is clear.",
        "ko": "더빙의 이 부분을 알아듣기 어렵습니다: “{text}”. 목소리가 또렷한지 들어 보세요.",
        "pt": "Este trecho da dublagem é difícil de entender: “{text}”. Ouça para ver se a voz está clara.",
        "es": "Esta parte del doblaje se entiende mal: “{text}”. Escucha para comprobar que la voz es clara.",
    },
    "r.cat.voice_quality": {"en": "voice quality", "ko": "목소리 품질", "pt": "qualidade da voz", "es": "calidad de la voz"},
    "r.int.voice_quality": {
        "en": "Around here the dub's voice sounds clearly worse than the original's (score {dub} against {orig}): "
              "listen for a robotic, distorted or muffled voice.",
        "ko": "이 부근에서 더빙 목소리가 원본보다 확실히 나쁘게 들립니다(점수 {dub}, 원본 {orig}). 기계음, 찌그러짐, "
              "먹먹한 소리가 나는지 들어 보세요.",
        "pt": "Por aqui a voz da dublagem soa claramente pior que a do original (nota {dub} contra {orig}): ouça se a voz "
              "está robótica, distorcida ou abafada.",
        "es": "Por aquí la voz del doblaje suena claramente peor que la del original (nota {dub} frente a {orig}): "
              "escucha si suena robótica, distorsionada o apagada.",
    },
    "r.vq.good": {
        "en": "The dub's voice sounds as clean as the original's where both speak (score {dub} against {orig} on a "
              "1-{scale} scale). No robotic, distorted or muffled sound stands out.",
        "ko": "두 트랙이 함께 말하는 구간에서 더빙 목소리가 원본만큼 깨끗하게 들립니다(1~{scale}점 중 더빙 {dub}, 원본 "
              "{orig}). 기계음, 찌그러짐, 먹먹한 소리가 눈에 띄지 않습니다.",
        "pt": "A voz da dublagem soa tão limpa quanto a do original onde os dois falam (nota {dub} contra {orig}, de 1 a "
              "{scale}). Nenhum som robótico, distorcido ou abafado se destaca.",
        "es": "La voz del doblaje suena tan limpia como la del original donde hablan los dos (nota {dub} frente a "
              "{orig}, de 1 a {scale}). No destaca ningún sonido robótico, distorsionado ni apagado.",
    },
    "r.vq.check_one": {
        "en": "In {n} of {total} stretches the dub's voice sounds a little worse than the original's at the same moment. "
              "Listen there for a slightly robotic or distorted voice.",
        "ko": "{total}개 구간 중 {n}개에서 더빙 목소리가 같은 순간의 원본보다 조금 나쁘게 들립니다. 그 부분이 약간 "
              "기계적이거나 찌그러지게 들리는지 확인하세요.",
        "pt": "Em {n} de {total} trechos a voz da dublagem soa um pouco pior que a do original no mesmo momento. Ouça "
              "ali se a voz está um pouco robótica ou distorcida.",
        "es": "En {n} de {total} tramos la voz del doblaje suena algo peor que la del original en el mismo momento. "
              "Escucha ahí si suena algo robótica o distorsionada.",
    },
    "r.vq.check_many": {
        "en": "In {n} of {total} stretches the dub's voice sounds a little worse than the original's at the same "
              "moment. Listen there for a slightly robotic or distorted voice.",
        "ko": "{total}개 구간 중 {n}개에서 더빙 목소리가 같은 순간의 원본보다 조금 나쁘게 들립니다. 그 부분들이 약간 "
              "기계적이거나 찌그러지게 들리는지 확인하세요.",
        "pt": "Em {n} de {total} trechos a voz da dublagem soa um pouco pior que a do original no mesmo momento. Ouça "
              "ali se a voz está um pouco robótica ou distorcida.",
        "es": "En {n} de {total} tramos la voz del doblaje suena algo peor que la del original en el mismo momento. "
              "Escucha ahí si suena algo robótica o distorsionada.",
    },
    "r.vq.poor_one": {
        "en": "In {n} of {total} stretches the dub's voice sounds clearly worse than the original's: viewers will likely "
              "hear a robotic or distorted voice there. Check the voice settings or regenerate that part.",
        "ko": "{total}개 구간 중 {n}개에서 더빙 목소리가 원본보다 확실히 나쁘게 들려 시청자가 기계음이나 찌그러진 소리를 "
              "들을 가능성이 높습니다. 음성 설정을 확인하거나 그 부분을 다시 생성하세요.",
        "pt": "Em {n} de {total} trechos a voz da dublagem soa claramente pior que a do original: o público "
              "provavelmente ouvirá uma voz robótica ou distorcida ali. Revise a voz ou gere essa parte de novo.",
        "es": "En {n} de {total} tramos la voz del doblaje suena claramente peor que la del original: es probable que "
              "el público oiga ahí una voz robótica o distorsionada. Revisa la voz o vuelve a generar esa parte.",
    },
    "r.vq.poor_many": {
        "en": "In {n} of {total} stretches the dub's voice sounds clearly worse than the original's: viewers will likely "
              "hear a robotic or distorted voice there. Check the voice settings or regenerate those parts.",
        "ko": "{total}개 구간 중 {n}개에서 더빙 목소리가 원본보다 확실히 나쁘게 들려 시청자가 기계음이나 찌그러진 소리를 "
              "들을 가능성이 높습니다. 음성 설정을 확인하거나 그 부분들을 다시 생성하세요.",
        "pt": "Em {n} de {total} trechos a voz da dublagem soa claramente pior que a do original: o público "
              "provavelmente ouvirá uma voz robótica ou distorcida ali. Revise a voz ou gere essas partes de novo.",
        "es": "En {n} de {total} tramos la voz del doblaje suena claramente peor que la del original: es probable que "
              "el público oiga ahí una voz robótica o distorsionada. Revisa la voz o vuelve a generar esas partes.",
    },
    "r.g.vq": {
        "en": "A voice-quality model trained on listener scores rates both tracks at the same moments (about 9 s each) "
              "and the same volume, where both speak, on a 1-5 scale for the voice and for the whole sound. A stretch "
              "is Needs review when the dub's voice scores {sig} or more below the original's or the whole sound {ovr} or more "
              "below, Poor from {sig_poor} / {ovr_poor}. A stretch where the original itself scores under {floor} doesn't "
              "count. The worst stretch sets the level. A muffled voice is not detected.",
        "ko": "청취자 평가로 학습한 목소리 품질 모델이 두 트랙이 함께 말하는 같은 순간(약 9초씩)을 같은 음량으로 맞춰 "
              "목소리와 전체 소리에 대해 1~5점으로 평가합니다. 더빙 목소리 점수가 원본보다 {sig}점 이상 또는 전체 소리 "
              "점수가 {ovr}점 이상 낮으면 검토 필요, {sig_poor} / {ovr_poor}점 이상이면 미흡입니다. 원본 자체의 점수가 "
              "{floor}점 미만인 구간은 세지 않습니다. 가장 나쁜 구간이 등급을 정합니다. 먹먹한 목소리는 감지하지 못합니다.",
        "pt": "Um modelo de qualidade de voz treinado com notas de ouvintes avalia as duas faixas nos mesmos momentos "
              "(cerca de 9 s cada) e no mesmo volume, onde as duas falam, de 1 a 5 para a voz e para o som todo. Um "
              "trecho é Precisa de revisão quando a voz da dublagem fica {sig} ou mais abaixo da original ou o som todo {ovr} ou "
              "mais abaixo, Ruim a partir de {sig_poor} / {ovr_poor}. Um trecho em que a própria original fica abaixo de "
              "{floor} não conta. O pior trecho define o nível. Uma voz abafada não é detectada.",
        "es": "Un modelo de calidad de voz entrenado con notas de oyentes califica las dos pistas en los mismos momentos "
              "(unos 9 s cada uno) y al mismo volumen, donde hablan las dos, de 1 a 5 para la voz y para todo el sonido. "
              "Un tramo es Necesita revisión cuando la voz del doblaje queda {sig} o más por debajo de la original o todo el sonido "
              "{ovr} o más, Deficiente desde {sig_poor} / {ovr_poor}. Un tramo donde la propia original queda por debajo "
              "de {floor} no cuenta. El peor tramo fija el nivel. Una voz apagada no se detecta.",
    },
    "r.cat.voice_change": {"en": "different voice", "ko": "다른 목소리", "pt": "voz diferente", "es": "voz distinta"},
    "r.int.voice_change": {
        "en": "This line's dub voice doesn't sound like the original speaker ({sim} alike) while the rest of the dub "
              "does ({median}). The line may have been given another character's voice.",
        "ko": "이 문장의 더빙 목소리는 원래 화자와 닮지 않았습니다(유사도 {sim}, 나머지 더빙은 {median}). 다른 인물의 "
              "목소리가 배정됐을 수 있습니다.",
        "pt": "A voz da dublagem nesta fala não se parece com a do falante original ({sim}), embora o resto pareça "
              "({median}). A fala pode ter recebido a voz de outro personagem.",
        "es": "La voz del doblaje en esta frase no se parece al hablante original ({sim}), aunque el resto sí "
              "({median}). Puede que la frase recibiera la voz de otro personaje.",
    },
    "r.vs.display": {"en": "{sim} alike · {n} lines", "ko": "유사도 {sim} · {n}문장", "pt": "{sim} parecida · {n} falas",
                     "es": "{sim} de parecido · {n} frases"},
    "r.vs.good": {
        "en": "The dub speaks with the original speaker's voice: {sim} alike over {n} lines compared at the same "
              "moments. The same voice scores {same} or more; two different people score under {strangers}.",
        "ko": "더빙 목소리가 원래 화자의 목소리와 같습니다. 같은 순간에 비교한 {n}문장의 유사도: {sim}. 같은 목소리는 "
              "{same} 이상, 서로 다른 두 사람은 {strangers} 미만입니다.",
        "pt": "A dublagem fala com a voz do falante original: {sim} de semelhança em {n} falas comparadas nos mesmos "
              "momentos. A mesma voz dá {same} ou mais; duas pessoas diferentes dão menos de {strangers}.",
        "es": "El doblaje habla con la voz del hablante original: {sim} de parecido en {n} frases comparadas en los "
              "mismos momentos. La misma voz da {same} o más; dos personas distintas dan menos de {strangers}.",
    },
    "r.vs.different": {
        "en": "The dub speaks with a different voice from the original speaker: {sim} alike over {n} lines, where two "
              "different people score under {strangers}. That's fine if another voice was chosen on purpose; if the "
              "voice should be cloned, check the voice settings.",
        "ko": "더빙 목소리가 원래 화자와 다른 목소리입니다. {n}문장의 유사도: {sim} (서로 다른 두 사람은 {strangers} "
              "미만). 일부러 다른 목소리를 골랐다면 정상이지만, 목소리를 복제해야 한다면 음성 설정을 확인하세요.",
        "pt": "A dublagem fala com uma voz diferente da do falante original: {sim} de semelhança em {n} falas, e duas "
              "pessoas diferentes dão menos de {strangers}. É esperado se outra voz foi escolhida de propósito; se a "
              "voz deveria ser clonada, revise a configuração de voz.",
        "es": "El doblaje habla con una voz distinta de la del hablante original: {sim} de parecido en {n} frases, y "
              "dos personas distintas dan menos de {strangers}. Es normal si se eligió otra voz a propósito; si la voz "
              "debía clonarse, revisa la configuración de voz.",
    },
    "r.vs.partly": {
        "en": "The dub's voice is only partly like the original speaker's: {sim} alike over {n} lines. The same voice "
              "scores {same} or more; two different people score under {strangers}. Listen to a few lines to decide.",
        "ko": "더빙 목소리가 원래 화자와 일부만 닮았습니다. {n}문장의 유사도: {sim}. 같은 목소리는 {same} 이상, 서로 다른 "
              "두 사람은 {strangers} 미만입니다. 몇 문장을 들어 보고 판단하세요.",
        "pt": "A voz da dublagem só se parece em parte com a do falante original: {sim} de semelhança em {n} falas. A "
              "mesma voz dá {same} ou mais; duas pessoas diferentes dão menos de {strangers}. Ouça algumas falas para "
              "decidir.",
        "es": "La voz del doblaje solo se parece en parte a la del hablante original: {sim} de parecido en {n} frases. "
              "La misma voz da {same} o más; dos personas distintas dan menos de {strangers}. Escucha algunas frases "
              "para decidir.",
    },
    "r.vs.known": {
        "en": "The measure can be trusted on this video: the original speaker's own lines are {own} alike.",
        "ko": "이 영상에서는 측정을 믿을 수 있습니다. 원래 화자 자신의 문장끼리 유사도: {own}.",
        "pt": "A medida é confiável neste vídeo: as falas do próprio falante original têm {own} de semelhança entre si.",
        "es": "La medida es fiable en este video: las frases del propio hablante original tienen {own} de parecido "
              "entre sí.",
    },
    "r.vs.unsure": {
        "en": "Can't tell on this video: the dub is {sim} like the original over {n} lines, but the model can't "
              "recognise the original's own speakers either (their lines are {own} alike; it takes {known}). Several "
              "people talking, music over the voices or short lines cause that, so the number says nothing about the "
              "dub's voice.",
        "ko": "이 영상에서는 판단할 수 없습니다. 더빙과 원본의 유사도: {sim} ({n}문장). 그런데 모델이 원본 화자 자신도 잘 "
              "알아보지 못합니다(원본 문장끼리 유사도 {own}, 필요한 값 {known}). 여러 사람이 함께 말하거나, 목소리 위에 "
              "음악이 깔리거나, 문장이 짧을 때 생기는 일이라 이 숫자로는 더빙 목소리를 평가할 수 없습니다.",
        "pt": "Não dá para dizer neste vídeo: a dublagem tem {sim} de semelhança com o original em {n} falas, mas o "
              "modelo também não reconhece os próprios falantes do original (as falas deles têm {own} de semelhança "
              "entre si; são precisos {known}). Isso acontece com várias pessoas falando, música sobre as vozes ou "
              "falas curtas, então o número não diz nada sobre a voz da dublagem.",
        "es": "No se puede saber en este video: el doblaje tiene {sim} de parecido con el original en {n} frases, pero "
              "el modelo tampoco reconoce a los propios hablantes del original (sus frases tienen {own} de parecido "
              "entre sí; hacen falta {known}). Pasa con varias personas hablando, música sobre las voces o frases "
              "cortas, así que el número no dice nada sobre la voz del doblaje.",
    },
    "r.g.vs": {
        "en": "A speaker-recognition model compares the voice of each original line (2 s or longer) with the dub at "
              "the same moment. {same} or more: the same voice (Good). Under {different}: another voice; between: "
              "partly alike (both Needs review, never Poor: a new voice can be a deliberate choice). Two different "
              "people score under {strangers}. A result under {same} isn't graded when the original's own lines are "
              "less than {known} alike with each other: the model doesn't know that video's speakers.",
        "ko": "화자 인식 모델이 원본의 각 문장(2초 이상)의 목소리를 같은 순간의 더빙과 비교합니다. {same} 이상: 같은 "
              "목소리(좋음). {different} 미만: 다른 목소리, 그 사이: 일부만 닮음(둘 다 검토 필요. 일부러 다른 목소리를 고를 "
              "수 있어 미흡은 없음). 서로 다른 두 사람은 {strangers} 미만입니다. 결과가 {same} 미만인데 원본 문장끼리의 "
              "유사도가 {known} 미만이면 등급을 매기지 않습니다. 모델이 그 영상의 화자를 알아보지 못하기 때문입니다.",
        "pt": "Um modelo de reconhecimento de falante compara a voz de cada fala original (2 s ou mais) com a dublagem "
              "no mesmo momento. {same} ou mais: a mesma voz (Bom). Menos de {different}: outra voz; entre os dois: "
              "parecida em parte (ambos Precisa de revisão, nunca Ruim: outra voz pode ser uma escolha). Duas pessoas "
              "diferentes dão menos de {strangers}. Um resultado abaixo de {same} não recebe nota quando as falas do "
              "próprio original têm menos de {known} de semelhança entre si: o modelo não conhece os falantes desse "
              "vídeo.",
        "es": "Un modelo de reconocimiento de hablante compara la voz de cada frase original (2 s o más) con el "
              "doblaje en el mismo momento. {same} o más: la misma voz (Bien). Menos de {different}: otra voz; entre "
              "ambos: parecida en parte (ambos Necesita revisión, nunca Deficiente: otra voz puede ser una elección). "
              "Dos personas distintas dan menos de {strangers}. Un resultado por debajo de {same} no se califica "
              "cuando las frases del propio original tienen menos de {known} de parecido entre sí: el modelo no "
              "conoce a los hablantes de ese video.",
    },
    "r.vs.noisy": {
        "en": "The original's background (music, effects or noise) is too loud under the dialogue to compare voices "
              "reliably, so voice similarity wasn't measured.",
        "ko": "원본의 대사 아래 배경(음악, 효과음, 소음)이 너무 커서 목소리를 믿을 만하게 비교할 수 없어 목소리 유사도를 "
              "측정하지 않았습니다.",
        "pt": "O fundo do original (música, efeitos ou ruído) está alto demais sob os diálogos para comparar vozes com "
              "confiança, então a semelhança da voz não foi medida.",
        "es": "El fondo del original (música, efectos o ruido) suena demasiado fuerte bajo los diálogos para comparar "
              "voces con fiabilidad, así que no se midió el parecido de la voz.",
    },
    "r.vs.few_lines": {
        "en": "There are fewer than two original lines of 2 seconds or more to compare, so voice similarity wasn't "
              "measured.",
        "ko": "비교할 2초 이상의 원본 문장이 두 개 미만이라 목소리 유사도를 측정하지 않았습니다.",
        "pt": "Há menos de duas falas originais de 2 segundos ou mais para comparar, então a semelhança da voz não foi "
              "medida.",
        "es": "Hay menos de dos frases originales de 2 segundos o más para comparar, así que no se midió el parecido "
              "de la voz.",
    },
    "r.vs.no_model": {
        "en": "The speaker-recognition model (26 MB, downloaded once) couldn't be downloaded, so voice similarity "
              "wasn't measured. Check the internet connection and run again.",
        "ko": "화자 인식 모델(26 MB, 한 번만 다운로드)을 받지 못해 목소리 유사도를 측정하지 않았습니다. 인터넷 연결을 "
              "확인하고 다시 실행하세요.",
        "pt": "O modelo de reconhecimento de falante (26 MB, baixado uma vez) não pôde ser baixado, então a semelhança "
              "da voz não foi medida. Verifique a internet e rode de novo.",
        "es": "No se pudo descargar el modelo de reconocimiento de hablante (26 MB, se descarga una vez), así que no "
              "se midió el parecido de la voz. Revisa la conexión y vuelve a ejecutar.",
    },
    "r.vs.error": {
        "en": "The speaker-recognition model couldn't run on this machine, so voice similarity wasn't measured.",
        "ko": "이 컴퓨터에서 화자 인식 모델을 실행하지 못해 목소리 유사도를 측정하지 않았습니다.",
        "pt": "O modelo de reconhecimento de falante não pôde rodar nesta máquina, então a semelhança da voz não foi "
              "medida.",
        "es": "El modelo de reconocimiento de hablante no pudo ejecutarse en este equipo, así que no se midió el "
              "parecido de la voz.",
    },
    "r.g.vq_pq": {
        "en": "A model trained on listeners' ratings of speech, music and sound rates both tracks at the same moments "
              "(about 9 s each) and the same volume, where both speak, on a 1-10 scale for how well the sound is "
              "produced. A stretch is Needs review when the dub scores {drop} or more below the original there, or "
              "{drop} or more below how this dub usually compares with the original ({second} on the model's second "
              "score); Poor from {poor}. The worst stretch sets the level.",
        "ko": "말소리, 음악, 효과음에 대한 청취자 평가로 학습한 모델이 두 트랙이 함께 말하는 같은 순간(약 9초씩)을 같은 "
              "음량으로 맞춰, 소리가 얼마나 잘 만들어졌는지 1~10점으로 평가합니다. 어떤 구간에서 더빙 점수가 원본보다 "
              "{drop}점 이상 낮거나, 이 더빙이 평소 원본과 비교되는 수준보다 {drop}점 이상 낮으면(모델의 두 번째 점수는 "
              "{second}점) 검토 필요, {poor}점 이상이면 미흡입니다. 가장 나쁜 구간이 등급을 정합니다.",
        "pt": "Um modelo treinado com notas de ouvintes para fala, música e som avalia as duas faixas nos mesmos "
              "momentos (cerca de 9 s cada) e no mesmo volume, onde as duas falam, de 1 a 10 para a qualidade da "
              "produção do som. Um trecho é Precisa de revisão quando a dublagem fica {drop} ou mais abaixo do original "
              "ali, ou {drop} ou mais abaixo de como esta dublagem costuma se comparar com o original ({second} na "
              "segunda nota do modelo); Ruim a partir de {poor}. O pior trecho define o nível.",
        "es": "Un modelo entrenado con valoraciones de oyentes sobre habla, música y sonido puntúa las dos pistas en los "
              "mismos momentos (unos 9 s cada uno) y al mismo volumen, donde hablan las dos, de 1 a 10 según lo bien "
              "producido que está el sonido. Un tramo es Necesita revisión cuando el doblaje queda {drop} o más por "
              "debajo del original ahí, o {drop} o más por debajo de como suele compararse este doblaje con el "
              "original ({second} en la segunda nota del modelo); Deficiente desde {poor}. El peor tramo fija el nivel.",
    },
    "r.vq.no_common_speech": {
        "en": "The original and the dub don't speak at the same time long enough to compare their voices.",
        "ko": "원본과 더빙이 동시에 말하는 시간이 짧아 목소리를 비교할 수 없습니다.",
        "pt": "O original e a dublagem não falam ao mesmo tempo por tempo suficiente para comparar as vozes.",
        "es": "El original y el doblaje no hablan a la vez el tiempo suficiente para comparar sus voces.",
    },
    "r.vq.too_noisy": {
        "en": "The original's voice itself scores low ({orig} of 5, usually because of loud music or noise), so it "
              "can't serve as a reference for the dub's voice quality.",
        "ko": "원본 목소리 점수 자체가 낮아(5점 중 {orig}, 보통 큰 음악이나 소음 때문) 더빙 목소리 품질의 기준으로 쓸 수 "
              "없습니다.",
        "pt": "A própria voz do original tem nota baixa ({orig} de 5, em geral por música alta ou ruído), então não serve "
              "de referência para a qualidade da voz da dublagem.",
        "es": "La propia voz del original tiene nota baja ({orig} de 5, normalmente por música fuerte o ruido), así que "
              "no sirve de referencia para la calidad de la voz del doblaje.",
    },
    "r.vq.error": {
        "en": "The voice-quality model couldn't run on this machine, so voice quality wasn't measured.",
        "ko": "이 컴퓨터에서 목소리 품질 모델을 실행하지 못해 목소리 품질을 측정하지 않았습니다.",
        "pt": "O modelo de qualidade de voz não pôde rodar nesta máquina, então a qualidade da voz não foi medida.",
        "es": "El modelo de calidad de voz no pudo ejecutarse en este equipo, así que no se midió la calidad de la voz.",
    },
    "r.vq.old": {
        "en": "This result was made before voice quality was measured. Run the evaluation again to get it.",
        "ko": "목소리 품질 측정이 추가되기 전에 만든 결과입니다. 다시 평가하면 볼 수 있습니다.",
        "pt": "Este resultado foi gerado antes da medição da qualidade da voz. Avalie de novo para obtê-la.",
        "es": "Este resultado se hizo antes de que se midiera la calidad de la voz. Vuelve a evaluar para obtenerla.",
    },
    "r.int.noise": {
        "en": "The dub fills with noise here for {sec} s (a hiss or static the original doesn't have). Listen to check.",
        "ko": "더빙의 이 부분에 {sec}초 동안 원본에 없는 잡음(쉿 소리, 지직거림)이 있습니다. 들어 보고 확인하세요.",
        "pt": "A dublagem se enche de ruído aqui por {sec} s (um chiado ou estática que o original não tem). Ouça para confirmar.",
        "es": "El doblaje se llena de ruido aquí durante {sec} s (un siseo o estática que el original no tiene). Escucha para comprobarlo.",
    },
    "r.int.long_silence": {
        "en": "The original speaks for {sec} s here, but the dub is silent. A line is probably missing from the dub.",
        "ko": "원본은 여기서 {sec}초 동안 말하는데 더빙은 조용합니다. 더빙에서 문장이 빠졌을 가능성이 높습니다.",
        "pt": "O original fala por {sec} s aqui, mas a dublagem fica em silêncio. Provavelmente falta uma fala.",
        "es": "El original habla {sec} s aquí, pero el doblaje calla. Probablemente falta una frase en el doblaje.",
    },
    "r.int.clipping": {
        "en": "The dub's audio hits the maximum level here and distorts. Listen for crackling.",
        "ko": "여기서 더빙 소리가 최대 음량을 넘어 찌그러집니다. 지직거리는 소리가 나는지 들어 보세요.",
        "pt": "O áudio da dublagem atinge o nível máximo aqui e distorce. Ouça se há chiado.",
        "es": "El audio del doblaje llega al nivel máximo aquí y se distorsiona. Escucha si hay chasquidos.",
    },
    "r.int.louder": {
        "en": "The dub is about {db} dB louder than the original here. Listen for a sudden jump in volume.",
        "ko": "여기서 더빙이 원본보다 약 {db} dB 더 큽니다. 음량이 갑자기 커지는지 들어 보세요.",
        "pt": "A dublagem está cerca de {db} dB mais alta que o original aqui. Ouça se o volume salta de repente.",
        "es": "El doblaje suena unos {db} dB más fuerte que el original aquí. Escucha si el volumen salta de golpe.",
    },
    "r.int.quieter": {
        "en": "The dub is about {db} dB quieter than the original here. Viewers may struggle to hear this part.",
        "ko": "여기서 더빙이 원본보다 약 {db} dB 더 작습니다. 시청자가 이 부분을 잘 듣지 못할 수 있습니다.",
        "pt": "A dublagem está cerca de {db} dB mais baixa que o original aqui. Pode ser difícil ouvir este trecho.",
        "es": "El doblaje suena unos {db} dB más bajo que el original aquí. Puede costar oír esta parte.",
    },
    "r.int.original_language": {
        "en": "This part sounds like {lang}, the original language. The original voice may have been left in, or "
              "the line wasn't dubbed.",
        "ko": "이 부분은 원본 언어({lang})처럼 들립니다. 원래 목소리가 남아 있거나 이 문장이 더빙되지 않았을 수 있습니다.",
        "pt": "Este trecho soa como {lang}, o idioma original. A voz original pode ter ficado, ou a fala não foi dublada.",
        "es": "Esta parte suena a {lang}, el idioma original. Puede que quedara la voz original o que la frase no se "
              "doblara.",
    },
    "r.int.other_language": {
        "en": "This part sounds like {detected}, not {expected}. Check that it was dubbed into the right language.",
        "ko": "이 부분은 기대한 언어({expected})가 아니라 다른 언어({detected})처럼 들립니다. 올바른 언어로 더빙됐는지 "
              "확인하세요.",
        "pt": "Este trecho soa como {detected}, não {expected}. Confira se foi dublado no idioma certo.",
        "es": "Esta parte suena a {detected}, no a {expected}. Comprueba que se dobló al idioma correcto.",
    },
    "r.todo.maybe_asr_or_real": {
        "en": "(This may be a speech-recognition error or a real translation error: listen to the line to tell.)",
        "ko": "(음성 인식 오류일 수도, 실제 번역 오류일 수도 있습니다. 해당 대사를 들어 보고 판단하세요.)",
        "pt": "(Pode ser um erro do reconhecimento de fala ou um erro real de tradução: ouça a fala para saber.)",
        "es": "(Puede ser un error del reconocimiento de voz o un error real de traducción: escucha la frase para "
              "saberlo.)",
    },
    "r.rubric.doubtful_one": {
        "en": "{n} line scored very low but may be misheard: listen to it to tell (Needs review, not Poor).",
        "ko": "{n}개 대사의 점수가 매우 낮지만 잘못 들었을 수 있습니다. 들어 보고 판단하세요(미흡이 아니라 검토 필요).",
        "pt": "{n} fala teve nota muito baixa, mas pode ter sido ouvida errado: ouça para saber (Precisa de revisão, não Ruim).",
        "es": "{n} frase obtuvo una nota muy baja, pero pudo oírse mal: escúchala para saberlo (Necesita revisión, no Deficiente).",
    },
    "r.rubric.doubtful_many": {
        "en": "{n} lines scored very low but may be misheard: listen to them to tell (Needs review, not Poor).",
        "ko": "{n}개 대사의 점수가 매우 낮지만 잘못 들었을 수 있습니다. 들어 보고 판단하세요(미흡이 아니라 검토 필요).",
        "pt": "{n} falas tiveram nota muito baixa, mas podem ter sido ouvidas errado: ouça para saber (Precisa de revisão, não "
              "Ruim).",
        "es": "{n} frases obtuvieron una nota muy baja, pero pudieron oírse mal: escúchalas para saberlo (Necesita revisión, no "
              "Deficiente).",
    },
    "r.todo.maybe_asr": {
        "en": "(Probably a speech-recognition error, not a dubbing error.)",
        "ko": "(더빙 오류가 아니라 음성 인식 오류일 가능성이 높습니다.)",
        "pt": "(Provavelmente um erro do reconhecimento de fala, não da dublagem.)",
        "es": "(Probablemente un error del reconocimiento de voz, no del doblaje.)",
    },
    "r.warn.length": {
        "en": "The dub ({dub} s) and the original ({orig} s) differ in length by more than 20%; they may not be the same "
              "video.",
        "ko": "더빙({dub}초)과 원본({orig}초)의 길이가 20% 넘게 다릅니다. 같은 영상이 아닐 수 있습니다.",
        "pt": "A dublagem ({dub} s) e o original ({orig} s) diferem em mais de 20% na duração; talvez não sejam o mesmo "
              "vídeo.",
        "es": "El doblaje ({dub} s) y el original ({orig} s) difieren en más de un 20% de duración; puede que no sean el "
              "mismo video.",
    },
    "r.warn.no_speech": {
        "en": "Speech recognition found no speech in the dub. Check that the dub has a voice.",
        "ko": "음성 인식이 더빙에서 말소리를 찾지 못했습니다. 더빙에 목소리가 있는지 확인하세요.",
        "pt": "O reconhecimento de fala não encontrou fala na dublagem. Confira se a dublagem tem voz.",
        "es": "El reconocimiento de voz no encontró habla en el doblaje. Comprueba que el doblaje tiene voz.",
    },
    "r.warn.script": {
        "en": "Very little of the script was heard. Check that the script belongs to this video and is in the dub's "
              "language.",
        "ko": "스크립트 내용이 거의 들리지 않습니다. 스크립트가 이 영상의 것이고 더빙 언어로 되어 있는지 확인하세요.",
        "pt": "Quase nada do roteiro foi ouvido. Confira se o roteiro é deste vídeo e está no idioma da dublagem.",
        "es": "Apenas se oyó el guion. Comprueba que el guion es de este video y está en el idioma del doblaje.",
    },
    "r.warn.lang_guess": {
        "en": "The dub's language wasn't given, and speech recognition guessed {lang} but is only {pct}% sure. If the "
              "dub is in another language, run again with that language set (--target-lang); the language checks "
              "depend on it.",
        "ko": "더빙 언어가 지정되지 않아 음성 인식이 언어를 추측했습니다({lang}, 확신도 {pct}%). 실제 언어가 다르면 "
              "언어를 지정해(--target-lang) 다시 실행하세요. 언어 관련 검사는 이 값에 따라 달라집니다.",
        "pt": "O idioma da dublagem não foi informado, e o reconhecimento de fala supôs {lang}, com só {pct}% de "
              "certeza. Se a dublagem estiver em outro idioma, execute de novo informando-o (--target-lang); as "
              "verificações de idioma dependem disso.",
        "es": "No se indicó el idioma del doblaje y el reconocimiento de voz supuso {lang}, con solo un {pct}% de "
              "seguridad. Si el doblaje está en otro idioma, vuelve a ejecutarlo indicándolo (--target-lang); las "
              "comprobaciones de idioma dependen de ello.",
    },
    "r.warn.no_whisper": {
        "en": "Speech recognition doesn't know this language ({lang}), so it guessed; treat the speech results as rough.",
        "ko": "음성 인식이 이 언어({lang})를 지원하지 않아 추측했습니다. 음성 관련 결과는 대략적인 값으로 보세요.",
        "pt": "O reconhecimento de fala não conhece este idioma ({lang}), então fez uma estimativa; considere os "
              "resultados de fala aproximados.",
        "es": "El reconocimiento de voz no conoce este idioma ({lang}), así que estimó; toma los resultados de habla como "
              "aproximados.",
    },

    # ----- verdict -----
    "r.headline.good": {
        "en": "The dub passed every automatic check. A quick watch-through is still a good idea before publishing.",
        "ko": "더빙이 모든 자동 검사를 통과했습니다. 게시 전에 한 번 훑어보는 것을 권합니다.",
        "pt": "A dublagem passou em todas as verificações automáticas. Ainda vale assistir rapidamente antes de publicar.",
        "es": "El doblaje pasó todas las comprobaciones automáticas. Aun así, conviene verlo rápido antes de publicar.",
    },
    "r.headline.check_one": {
        "en": "{n} item needs review: {names}.",
        "ko": "검토가 필요한 항목 {n}개: {names}.",
        "pt": "{n} item precisa de revisão: {names}.",
        "es": "{n} elemento necesita revisión: {names}.",
    },
    "r.headline.check_many": {
        "en": "{n} items need review: {names}.",
        "ko": "검토가 필요한 항목 {n}개: {names}.",
        "pt": "{n} itens precisam de revisão: {names}.",
        "es": "{n} elementos necesitan revisión: {names}.",
    },
    "r.headline.unsure_one": {
        "en": "DubEval found {n} serious problem but isn't sure of it: {names}. Watch the dub before deciding.",
        "ko": "DubEval이 심각한 문제를 {n}개 찾았지만 확실하지 않습니다: {names}. 판단하기 전에 더빙을 직접 보세요.",
        "pt": "O DubEval encontrou {n} problema grave, mas não tem certeza dele: {names}. Assista à dublagem antes de "
              "decidir.",
        "es": "DubEval encontró {n} problema grave, pero no está seguro de él: {names}. Mira el doblaje antes de decidir.",
    },
    "r.headline.unsure_many": {
        "en": "DubEval found {n} serious problems but isn't sure of them: {names}. Watch the dub before deciding.",
        "ko": "DubEval이 심각한 문제를 {n}개 찾았지만 확실하지 않습니다: {names}. 판단하기 전에 더빙을 직접 보세요.",
        "pt": "O DubEval encontrou {n} problemas graves, mas não tem certeza deles: {names}. Assista à dublagem antes "
              "de decidir.",
        "es": "DubEval encontró {n} problemas graves, pero no está seguro de ellos: {names}. Mira el doblaje antes de "
              "decidir.",
    },
    # A measure the headline names with the time of its first moment, and the rest of the list in a count.
    "r.headline.from": {"en": "{label} (from {time})", "ko": "{label}({time}부터)",
                        "pt": "{label} (a partir de {time})", "es": "{label} (desde {time})"},
    "r.headline.more": {"en": "and {n} more", "ko": "외 {n}개", "pt": "e mais {n}", "es": "y {n} más"},
    "r.headline.unchecked": {
        "en": "Nothing looked wrong in what DubEval could check, but it couldn't check everything.",
        "ko": "DubEval이 확인할 수 있는 부분에서는 문제가 없었지만, 모든 것을 확인하지는 못했습니다.",
        "pt": "Nada pareceu errado no que o DubEval conseguiu verificar, mas ele não conseguiu verificar tudo.",
        "es": "Nada pareció mal en lo que DubEval pudo comprobar, pero no pudo comprobarlo todo.",
    },
    "r.sure.little_speech": {
        "en": "Not sure: people speak only {pct}% of the video; the rest is music or effects, where speech recognition "
              "mishears and invents words.",
        "ko": "확실하지 않음: 영상에서 말소리는 {pct}%뿐이고 나머지는 음악이나 효과음입니다. 이런 부분에서는 음성 인식이 잘못 듣거나 없는 말을 만들어 냅니다.",
        "pt": "Sem certeza: há fala em só {pct}% do vídeo; o resto é música ou efeitos, onde o reconhecimento de fala "
              "ouve errado e inventa palavras.",
        "es": "Sin certeza: se habla solo en el {pct}% del video; el resto es música o efectos, donde el reconocimiento "
              "de voz oye mal e inventa palabras.",
    },
    "r.sure.short_speech": {
        "en": "Not sure: the original has only {sec} s of speech, too little to grade timing and meaning reliably. "
              "Listen to the dub yourself.",
        "ko": "확실하지 않음: 원본의 말소리가 {sec}초뿐이라 타이밍과 의미를 믿을 만하게 평가하기에 너무 짧습니다.",
        "pt": "Sem certeza: o original tem só {sec} s de fala, pouco demais para avaliar tempo e sentido com segurança. "
              "Ouça a dublagem você mesmo.",
        "es": "Sin certeza: el original tiene solo {sec} s de voz, muy poco para evaluar el ritmo y el sentido con "
              "fiabilidad.",
    },
    "r.sure.unclear_speech": {
        "en": "Not sure: speech recognition was confident on only {pct}% of the dub's speech, so the transcript-based "
              "checks may be wrong.",
        "ko": "확실하지 않음: 음성 인식이 더빙 말소리의 {pct}%만 확실하게 알아들어서, 대본에 기반한 검사가 틀릴 수 있습니다.",
        "pt": "Sem certeza: o reconhecimento de fala teve segurança em só {pct}% da fala da dublagem, então as "
              "verificações baseadas na transcrição podem errar.",
        "es": "Sin certeza: el reconocimiento de voz tuvo seguridad solo en el {pct}% de la voz del doblaje, así que las "
              "comprobaciones basadas en la transcripción pueden fallar.",
    },
    "r.sure.listen": {"en": "Listen to the dub yourself.", "ko": "더빙을 직접 들어 보세요.",
                      "pt": "Ouça a dublagem você mesmo.", "es": "Escucha el doblaje tú mismo."},
    "r.sure.background_replaced": {
        "en": "The dub's background sound is much cleaner than the original's (the music or effects were removed or "
              "replaced), so silence and loudness compare different soundtracks: they're shown as Needs review at most.",
        "ko": "더빙의 배경음이 원본보다 훨씬 깨끗합니다(음악이나 효과음이 제거되었거나 바뀜). 그래서 무음과 음량 비교는 서로 다른 소리를 비교하게 되므로 최대 검토 필요로만 표시합니다.",
        "pt": "O som de fundo da dublagem é muito mais limpo que o do original (a música ou os efeitos foram removidos "
              "ou trocados), então silêncio e volume comparam trilhas diferentes: aparecem no máximo como Precisa de revisão.",
        "es": "El sonido de fondo del doblaje es mucho más limpio que el del original (se quitó o cambió la música o "
              "los efectos), así que el silencio y el volumen comparan pistas distintas: se muestran como Necesita revisión "
              "como mucho.",
    },
    "r.sure.capped_background": {
        "en": "(Needs review at most: the dub's background was replaced.)",
        "ko": "(최대 검토 필요: 더빙의 배경음이 바뀌었습니다.)",
        "pt": "(No máximo Precisa de revisão: o fundo da dublagem foi trocado.)",
        "es": "(Como mucho Necesita revisión: se cambió el fondo del doblaje.)",
    },
    "r.sure.words_unchecked": {
        "en": "The dub's words couldn't be checked (speech recognition didn't make out its language), so DubEval "
              "can't call it Good. Watch it, or add the dub's subtitle file.",
        "ko": "음성 인식이 더빙 언어를 알아듣지 못해 더빙의 말을 확인할 수 없었습니다. 그래서 DubEval은 좋음으로 판정할 수 없습니다. 직접 보거나 더빙 자막 파일을 추가하세요.",
        "pt": "As palavras da dublagem não puderam ser verificadas (o reconhecimento de fala não identificou o idioma), "
              "então o DubEval não pode dizer que está Bom. Assista ou adicione o arquivo de legendas da dublagem.",
        "es": "No se pudieron comprobar las palabras del doblaje (el reconocimiento de voz no distinguió su idioma), "
              "así que DubEval no puede decir que está Bien. Míralo o añade el archivo de subtítulos del doblaje.",
    },
    "r.sure.translation_unchecked": {
        "en": "The translation wasn't checked (see Translation for why), so DubEval can't call the dub Good: check the "
              "meaning yourself, or add an AI key in Settings → API keys and run it again.",
        "ko": "번역을 확인하지 않았습니다(이유는 번역 항목 참고). 그래서 DubEval은 좋음으로 판정할 수 없습니다. 의미를 직접 확인하거나, 설정 → API 키에 AI 키를 추가한 뒤 다시 실행하세요.",
        "pt": "A tradução não foi verificada (veja o motivo em Tradução), então o DubEval não pode dizer que a "
              "dublagem está Boa: confira o sentido você mesmo ou adicione uma chave de IA em Configurações → Chaves "
              "de API e rode de novo.",
        "es": "No se comprobó la traducción (el motivo está en Traducción), así que DubEval no puede decir que el "
              "doblaje está Bien: revisa el sentido tú mismo o añade una clave de IA en Ajustes → Claves de API y "
              "vuelve a ejecutarlo.",
    },
    "r.sure.translation_off": {
        "en": "The translation check was turned off for this run, so DubEval can't call the dub Good: check the meaning "
              "yourself, or turn the check on and run it again.",
        "ko": "이번 실행에서는 번역 검사를 껐습니다. 그래서 DubEval은 좋음으로 판정할 수 없습니다. 의미를 직접 확인하거나, 번역 "
              "검사를 켠 뒤 다시 실행하세요.",
        "pt": "A verificação da tradução foi desligada nesta execução, então o DubEval não pode dizer que a dublagem está "
              "Boa: confira o sentido você mesmo ou ligue a verificação e rode de novo.",
        "es": "La comprobación de la traducción estaba desactivada en esta ejecución, así que DubEval no puede decir que "
              "el doblaje está Bien: revisa el sentido tú mismo o activa la comprobación y vuelve a ejecutarlo.",
    },
    "r.sure.translation_failed": {
        "en": "The translation wasn't checked (the reason is under Translation), so DubEval can't call the dub Good: "
              "check the meaning yourself, or fix what's described there and run it again.",
        "ko": "번역을 확인하지 못했습니다(이유는 번역 항목 참고). 그래서 DubEval은 좋음으로 판정할 수 없습니다. 의미를 직접 "
              "확인하거나, 번역 항목에 적힌 문제를 해결한 뒤 다시 실행하세요.",
        "pt": "A tradução não foi verificada (o motivo está em Tradução), então o DubEval não pode dizer que a dublagem "
              "está Boa: confira o sentido você mesmo ou resolva o que está descrito lá e rode de novo.",
        "es": "No se comprobó la traducción (el motivo está en Traducción), así que DubEval no puede decir que el "
              "doblaje está Bien: revisa el sentido tú mismo o resuelve lo que se indica allí y vuelve a ejecutarlo.",
    },
    "r.sure.judge_handover_credit": {
        "en": "Note: {first} couldn't check the translation because its account has no credit left, so {model} checked "
              "it instead. Add credit on the provider's billing page, or remove that key in Settings → API keys.",
        "ko": "참고: {first} 계정에 크레딧이 남아 있지 않아 대신 {model} 모델로 번역을 확인했습니다. 제공업체의 결제 페이지에서 "
              "크레딧을 추가하거나, 설정 → API 키에서 그 키를 삭제하세요.",
        "pt": "Nota: o {first} não pôde verificar a tradução porque a conta está sem crédito, então o {model} verificou "
              "no lugar dele. Adicione crédito na página de cobrança do provedor ou remova essa chave em Configurações → "
              "Chaves de API.",
        "es": "Nota: {first} no pudo revisar la traducción porque la cuenta no tiene crédito, así que la revisó {model}. "
              "Añade crédito en la página de facturación del proveedor o quita esa clave en Ajustes → Claves de API.",
    },
    "r.sure.judge_handover_key": {
        "en": "Note: {first} rejected the API key, so {model} checked the translation instead. Check that key in "
              "Settings → API keys.",
        "ko": "참고: {first} 서비스가 API 키를 거부해 대신 {model} 모델로 번역을 확인했습니다. 설정 → API 키에서 그 키를 "
              "확인하세요.",
        "pt": "Nota: o {first} recusou a chave de API, então o {model} verificou a tradução no lugar dele. Confira essa "
              "chave em Configurações → Chaves de API.",
        "es": "Nota: {first} rechazó la clave de API, así que {model} revisó la traducción. Revisa esa clave en Ajustes "
              "→ Claves de API.",
    },
    "r.sure.judge_fallback": {
        "en": "Note: the translation was judged by {model}, a backup model, because the first choice was busy; its "
              "scores can differ from run to run.",
        "ko": "참고: 첫 번째 모델이 바빠서 예비 모델({model})이 번역을 평가했습니다. 점수가 실행마다 달라질 수 있습니다.",
        "pt": "Nota: a tradução foi avaliada por {model}, um modelo reserva, porque o primeiro estava ocupado; as notas "
              "podem variar de uma execução para outra.",
        "es": "Nota: la traducción la evaluó {model}, un modelo de reserva, porque el primero estaba ocupado; las notas "
              "pueden variar de una ejecución a otra.",
    },
    "r.sure.weak_dub": {
        "en": "Note: the dub is in {lang}, which the speech model used here ({model}) reads poorly: about {pct}% of "
              "characters wrong on clear test sentences. Treat the checks that read the dub's words (clarity, timing, "
              "pace, translation) as rough.",
        "ko": "참고: 더빙 언어({lang})는 이번에 사용한 음성 인식 모델({model})이 잘 읽지 못합니다. 또렷한 시험 문장에서도 글자의 "
              "약 {pct}%를 틀립니다. 더빙의 말을 읽는 검사(명료도, 타이밍, 속도, 번역)는 대략적인 참고로만 보세요.",
        "pt": "Nota: a dublagem está em {lang}, idioma que o modelo de fala usado aqui ({model}) lê mal: cerca de {pct}% "
              "dos caracteres errados em frases de teste claras. Considere aproximadas as verificações que leem as "
              "palavras da dublagem (clareza, tempo, ritmo, tradução).",
        "es": "Nota: el doblaje está en {lang}, un idioma que el modelo de voz usado aquí ({model}) lee mal: cerca del "
              "{pct}% de los caracteres mal en frases de prueba claras. Toma como aproximadas las comprobaciones que "
              "leen las palabras del doblaje (claridad, tiempos, ritmo, traducción).",
    },
    "r.sure.weak_original": {
        "en": "Note: the original is in {lang}, which the speech model used here ({model}) reads poorly: about {pct}% of "
              "characters wrong on clear test sentences. Treat the checks that compare the dub with the original's words "
              "(timing, translation) as rough.",
        "ko": "참고: 원본 언어({lang})는 이번에 사용한 음성 인식 모델({model})이 잘 읽지 못합니다. 또렷한 시험 문장에서도 글자의 "
              "약 {pct}%를 틀립니다. 더빙을 원본의 말과 비교하는 검사(타이밍, 번역)는 대략적인 참고로만 보세요.",
        "pt": "Nota: o original está em {lang}, idioma que o modelo de fala usado aqui ({model}) lê mal: cerca de {pct}% "
              "dos caracteres errados em frases de teste claras. Considere aproximadas as verificações que comparam a "
              "dublagem com as palavras do original (tempo, tradução).",
        "es": "Nota: el original está en {lang}, un idioma que el modelo de voz usado aquí ({model}) lee mal: cerca del "
              "{pct}% de los caracteres mal en frases de prueba claras. Toma como aproximadas las comprobaciones que "
              "comparan el doblaje con las palabras del original (tiempos, traducción).",
    },
    "r.sure.weak_tip": {
        "en": "The large speech model reads {lang} much better (about {better}% wrong): download it in Settings → Models, "
              "or choose it under More options when you start an evaluation.",
        "ko": "큰 음성 인식 모델은 이 언어({lang})를 훨씬 잘 읽습니다(약 {better}% 오류). 설정 → 모델에서 내려받거나, 평가를 "
              "시작할 때 추가 옵션에서 선택하세요.",
        "pt": "O modelo de fala grande lê {lang} muito melhor (cerca de {better}% de erro): baixe-o em Configurações → "
              "Modelos ou escolha-o em Mais opções ao iniciar uma avaliação.",
        "es": "El modelo de voz grande lee {lang} mucho mejor (cerca del {better}% de error): descárgalo en Ajustes → "
              "Modelos o elígelo en Más opciones al iniciar una evaluación.",
    },
    "r.headline.poor_one": {
        "en": "{n} serious problem to fix before publishing: {names}.",
        "ko": "게시 전에 고쳐야 할 심각한 문제 {n}개: {names}.",
        "pt": "{n} problema grave para corrigir antes de publicar: {names}.",
        "es": "{n} problema grave que corregir antes de publicar: {names}.",
    },
    "r.headline.poor_many": {
        "en": "{n} serious problems to fix before publishing: {names}.",
        "ko": "게시 전에 고쳐야 할 심각한 문제 {n}개: {names}.",
        "pt": "{n} problemas graves para corrigir antes de publicar: {names}.",
        "es": "{n} problemas graves que corregir antes de publicar: {names}.",
    },
    "r.headline.plus_check_one": {
        "en": "{n} more item needs review.", "ko": "그 밖에 {n}개 항목은 검토가 필요합니다.",
        "pt": "Mais {n} item precisa de revisão.", "es": "{n} elemento más necesita revisión.",
    },
    "r.headline.plus_check_many": {
        "en": "{n} more items need review.", "ko": "그 밖에 {n}개 항목은 검토가 필요합니다.",
        "pt": "Mais {n} itens precisam de revisão.", "es": "{n} elementos más necesitan revisión.",
    },
    "r.note.translation": {
        "en": "The translation is judged from the speech-recognition transcripts of both videos, so a misheard word can "
              "look like a translation mistake. Such cases are marked as probable recognition errors.",
        "ko": "번역은 두 영상의 음성 인식 받아쓰기를 바탕으로 평가하므로, 잘못 들린 단어가 번역 오류처럼 보일 수 있습니다. "
              "그런 경우는 음성 인식 오류로 표시합니다.",
        "pt": "A tradução é avaliada a partir das transcrições dos dois vídeos, então uma palavra mal ouvida pode parecer "
              "erro de tradução. Esses casos são marcados como prováveis erros de reconhecimento.",
        "es": "La traducción se evalúa con las transcripciones de ambos videos, así que una palabra mal oída puede parecer "
              "un error de traducción. Esos casos se marcan como probables errores de reconocimiento.",
    },
    "r.note.lip_sync": {
        "en": "Counts in the overall verdict. The original's own score shows what this video can reach: some faces and "
              "angles line up less often even when they're in sync.",
        "ko": "전체 판정에 반영됩니다. 원본의 점수는 이 영상이 도달할 수 있는 수준을 보여 줍니다. 얼굴이나 각도에 따라서는 "
              "싱크가 맞아도 덜 맞는 것으로 나올 수 있습니다.",
        "pt": "Conta no resultado geral. A pontuação do próprio original mostra até onde este vídeo pode chegar: alguns "
              "rostos e ângulos combinam menos vezes mesmo quando estão sincronizados.",
        "es": "Cuenta en el resultado general. La puntuación del propio original muestra hasta dónde puede llegar este "
              "video: algunas caras y ángulos coinciden menos veces aunque estén sincronizados.",
    },
    "r.evaluated.lipsync": {"en": "lip-synced video", "ko": "립싱크 영상", "pt": "vídeo com sincronização labial",
                            "es": "video con sincronización labial"},
    "r.evaluated.dub": {"en": "dubbed video", "ko": "더빙 영상", "pt": "vídeo dublado", "es": "video doblado"},

    # ----- report labels (text and HTML versions) -----
    "r.label.title": {"en": "Dub Quality Report", "ko": "더빙 품질 보고서", "pt": "Relatório de qualidade da dublagem",
                      "es": "Informe de calidad del doblaje"},
    "r.label.overall": {"en": "Overall", "ko": "종합 판정", "pt": "Resultado", "es": "Resultado"},
    "r.label.things": {"en": "Things to check", "ko": "확인할 사항", "pt": "Pontos a verificar", "es": "Cosas que revisar"},
    "r.label.nothing": {"en": "Nothing specific to check.", "ko": "특별히 확인할 곳이 없습니다.",
                        "pt": "Nada específico para verificar.", "es": "Nada específico que revisar."},
    "r.label.not_measured": {"en": "Not measured", "ko": "측정하지 않은 항목", "pt": "Não medido", "es": "No medido"},
    "r.label.method": {"en": "Method", "ko": "방법", "pt": "Método", "es": "Método"},
    "r.label.judged_by": {"en": "translation judged by", "ko": "번역 평가:", "pt": "tradução avaliada por",
                          "es": "traducción evaluada por"},
    "r.label.project": {"en": "Project", "ko": "프로젝트", "pt": "Projeto", "es": "Proyecto"},
    "r.label.languages": {"en": "Languages", "ko": "언어", "pt": "Idiomas", "es": "Idiomas"},
    "r.label.length": {"en": "Length", "ko": "길이", "pt": "Duração", "es": "Duración"},
    "r.label.evaluated": {"en": "Evaluated", "ko": "평가 대상", "pt": "Avaliado", "es": "Evaluado"},
    "r.label.source": {"en": "Source", "ko": "출처", "pt": "Origem", "es": "Origen"},
    "r.label.original": {"en": "Original", "ko": "원본", "pt": "Original", "es": "Original"},
    "r.label.dub": {"en": "Dub", "ko": "더빙", "pt": "Dublagem", "es": "Doblaje"},
    "r.label.evidence": {"en": "Transcripts of both videos", "ko": "두 영상의 받아쓰기", "pt": "Transcrições dos dois vídeos",
                         "es": "Transcripciones de ambos videos"},
    "r.label.note": {"en": "Note", "ko": "참고", "pt": "Nota", "es": "Nota"},
    "r.label.score": {"en": "Score", "ko": "점수 항목", "pt": "Nota", "es": "Nota"},
    "r.label.average": {"en": "Average of all lines", "ko": "전체 줄 평균", "pt": "Média de todas as falas",
                        "es": "Promedio de todas las frases"},
    "r.label.part_line": {"en": "{label}: {avg} on average · {low} lines at {flag} or lower",
                          "ko": "{label}: 평균 {avg} · {flag}점 이하: {low}",
                          "pt": "{label}: média {avg} · {low} falas com {flag} ou menos",
                          "es": "{label}: promedio {avg} · {low} frases con {flag} o menos"},
    "r.label.low_lines": {"en": "Lines scoring {flag} or lower", "ko": "{flag}점 이하인 줄", "pt": "Falas com {flag} ou menos",
                          "es": "Frases con {flag} o menos"},
    "r.label.attention": {"en": "Measures that need attention", "ko": "확인이 필요한 측정 항목",
                          "pt": "Medidas que pedem atenção", "es": "Medidas que piden atención"},
    "r.label.passed": {"en": "Passed", "ko": "통과한 항목", "pt": "Aprovadas", "es": "Aprobadas"},
    "r.label.info": {
        "en": "For information",
        "ko": "참고",
        "pt": "Apenas informativo",
        "es": "Para información",
    },
    "r.label.tl_original": {"en": "Original speaking", "ko": "원본 말소리", "pt": "Original falando",
                            "es": "Original hablando"},
    "r.label.tl_dub": {"en": "Dub speaking", "ko": "더빙 말소리", "pt": "Dublagem falando", "es": "Doblaje hablando"},
    "r.label.tl_moment": {"en": "Moment to check", "ko": "확인할 순간", "pt": "Momento a verificar",
                          "es": "Momento que revisar"},
    "r.label.passed_note": {
        "en": "The HTML report and the app explain each one and how it is graded.",
        "ko": "각 항목의 설명과 평가 기준은 HTML 보고서와 앱에서 볼 수 있습니다.",
        "pt": "O relatório em HTML e o app explicam cada uma e como ela é avaliada.",
        "es": "El informe HTML y la app explican cada una y cómo se califica.",
    },
    # Checks that didn't run, put together by reason.
    "r.skip.count_one": {"en": "{n} check didn't run", "ko": "실행하지 못한 검사 {n}개",
                         "pt": "{n} verificação não foi feita", "es": "{n} comprobación no se hizo"},
    "r.skip.count_many": {"en": "{n} checks didn't run", "ko": "실행하지 못한 검사 {n}개",
                          "pt": "{n} verificações não foram feitas", "es": "{n} comprobaciones no se hicieron"},
    "r.skip.unrecognized_do": {
        "en": "What to do: add the dub's subtitle file (SRT or WebVTT) when you start the evaluation, so DubEval can read "
              "its words, or watch the dub yourself.",
        "ko": "해결 방법: 평가를 시작할 때 더빙의 자막 파일(SRT 또는 WebVTT)을 추가하면 DubEval이 더빙의 말을 읽을 수 있습니다. "
              "아니면 더빙을 직접 확인하세요.",
        "pt": "O que fazer: adicione o arquivo de legendas da dublagem (SRT ou WebVTT) ao iniciar a avaliação, para o "
              "DubEval ler as palavras, ou assista à dublagem você mesmo.",
        "es": "Qué hacer: añade el archivo de subtítulos del doblaje (SRT o WebVTT) al iniciar la evaluación, para que "
              "DubEval lea sus palabras, o mira el doblaje tú mismo.",
    },
    "r.label.suggested": {"en": "Suggested translation", "ko": "추천 번역", "pt": "Tradução sugerida",
                          "es": "Traducción sugerida"},
    "r.label.also": {"en": "Also at this moment", "ko": "같은 순간의 다른 문제", "pt": "Também neste momento",
                     "es": "También en este momento"},
    "r.label.misheard": {"en": "Possibly misheard (not counted)", "ko": "잘못 들었을 수 있음(계산하지 않음)",
                         "pt": "Possivelmente ouvido errado (não conta)", "es": "Posiblemente mal oído (no cuenta)"},
    "r.label.generated": {"en": "Generated by DubEval.", "ko": "DubEval에서 생성했습니다.",
                          "pt": "Gerado pelo DubEval.", "es": "Generado por DubEval."},

    # ----- compare mode (dubeval/compare.py) -----
    "c.title": {"en": "Dub comparison", "ko": "더빙 비교", "pt": "Comparação de dublagens", "es": "Comparación de doblajes"},
    "c.sec.recommended": {"en": "Recommended version", "ko": "추천 버전", "pt": "Versão recomendada",
                          "es": "Versión recomendada"},
    "c.sec.provisional": {"en": "Provisional first place (not a delivery recommendation)", "ko": "잠정 1위 (납품 추천 아님)",
                          "pt": "Primeiro lugar provisório (não é uma recomendação de entrega)",
                          "es": "Primer puesto provisional (no es una recomendación de entrega)"},
    "c.sec.not_ready": {"en": "Best starting point (not ready to deliver)", "ko": "가장 나은 출발점 (납품 준비 안 됨)",
                        "pt": "Melhor ponto de partida (não está pronta para entrega)",
                        "es": "Mejor punto de partida (no está listo para entregar)"},
    "c.sec.intervals": {
        "en": "Problems on the timeline",
        "ko": "문제 구간",
        "pt": "Problemas na linha do tempo",
        "es": "Problemas en la línea de tiempo",
    },
    "c.sec.reasoning": {"en": "Reasoning", "ko": "판단 근거", "pt": "Justificativa", "es": "Razonamiento"},
    "c.sec.table": {"en": "Every check, side by side", "ko": "전체 항목 나란히 보기", "pt": "Todas as verificações lado a lado",
                    "es": "Todas las comprobaciones, lado a lado"},
    "c.sec.links": {"en": "The dubs", "ko": "더빙 정보", "pt": "As dublagens", "es": "Los doblajes"},
    "c.sec.notes": {"en": "Measurement notes", "ko": "측정 참고 사항", "pt": "Notas sobre a medição",
                    "es": "Notas de medición"},
    "c.dub": {"en": "Dub {d}", "ko": "더빙 {d}", "pt": "Dublagem {d}", "es": "Doblaje {d}"},
    "c.held": {
        "en": "No confident recommendation yet: Dub {d} ranks first, but {why} Listen to the dubs before choosing.",
        "ko": "아직 확실하게 추천할 수 없습니다. 더빙 {d} 버전이 1위지만, {why} 고르기 전에 더빙을 직접 들어 보세요.",
        "pt": "Ainda não há recomendação segura: a Dublagem {d} fica em primeiro, mas {why} Ouça as dublagens antes de "
              "escolher.",
        "es": "Aún no hay una recomendación segura: el Doblaje {d} queda primero, pero {why} Escucha los doblajes antes "
              "de elegir.",
    },
    "c.held.speech": {
        "en": "its speech checks rest on little or unclear speech (see its report).",
        "ko": "말소리가 적거나 불분명해서 말소리 검사를 믿기 어렵습니다(해당 보고서 참고).",
        "pt": "as verificações de fala dela se baseiam em pouca fala ou fala pouco clara (veja o relatório).",
        "es": "sus comprobaciones de voz se basan en poca voz o voz poco clara (mira su informe).",
    },
    "c.held.translation": {
        "en": "its translation wasn't checked.",
        "ko": "번역을 확인하지 않았습니다.",
        "pt": "a tradução dela não foi verificada.",
        "es": "su traducción no se comprobó.",
    },
    "c.recommend": {"en": "Deliver Dub {d}.", "ko": "더빙 {d} 버전을 납품하세요.", "pt": "Entregue a Dublagem {d}.",
                    "es": "Entrega el Doblaje {d}."},
    "c.recommend_review": {"en": "Deliver Dub {d} after review.", "ko": "검토 후 더빙 {d} 버전을 납품하세요.",
                           "pt": "Entregue a Dublagem {d} depois de revisá-la.",
                           "es": "Entrega el Doblaje {d} después de revisarlo."},
    "c.recommend_tie_review": {
        "en": "Deliver Dub {d} after review. It is tied with Dub {other} on every rule, and comes first.",
        "ko": "검토 후 더빙 {d} 버전을 납품하세요. 더빙 {other} 버전과 모든 규칙에서 동점이며 순서상 먼저입니다.",
        "pt": "Entregue a Dublagem {d} depois de revisá-la. Ela empata com a Dublagem {other} em todas as regras e vem "
              "primeiro.",
        "es": "Entrega el Doblaje {d} después de revisarlo. Empata con el Doblaje {other} en todas las reglas y va primero.",
    },
    "c.why.more_moments": {
        "en": "Dub {win} has more problems on the timeline ({win_n}; Dub {lose}: {lose_n}), but the rules above come "
              "first: they count the checks that need attention, not the moments.",
        "ko": "문제 구간은 더빙 {win} 쪽이 더 많지만({win_n}개, 더빙 {lose}: {lose_n}개) 위 규칙이 먼저입니다. 위 규칙은 "
              "구간 수가 아니라 주의가 필요한 검사 항목 수를 셉니다.",
        "pt": "A Dublagem {win} tem mais trechos com problemas ({win_n}; Dublagem {lose}: {lose_n}), mas as regras acima "
              "vêm antes: elas contam as verificações que precisam de atenção, não os trechos.",
        "es": "El Doblaje {win} tiene más tramos con problemas ({win_n}; Doblaje {lose}: {lose_n}), pero las reglas de "
              "arriba van antes: cuentan las comprobaciones que necesitan atención, no los tramos.",
    },
    "c.recommend_tie": {
        "en": "Deliver Dub {d}. It is tied with Dub {other} on every rule, and comes first.",
        "ko": "더빙 {d} 버전을 납품하세요. 더빙 {other} 버전과 모든 규칙에서 동점이며 순서상 먼저입니다.",
        "pt": "Entregue a Dublagem {d}. Ela empata com a Dublagem {other} em todas as regras e vem primeiro.",
        "es": "Entrega el Doblaje {d}. Empata con el Doblaje {other} en todas las reglas y va primero.",
    },
    "c.start_from": {
        "en": "Don't deliver yet: Dub {d} is the best starting point.",
        "ko": "아직 납품하지 마세요. 더빙 {d} 버전이 가장 나은 출발점입니다.",
        "pt": "Não entregue ainda: a Dublagem {d} é o melhor ponto de partida.",
        "es": "No lo entregues todavía: el Doblaje {d} es el mejor punto de partida.",
    },
    "c.caution.judges": {
        "en": "Different AI models checked these dubs' translations ({models}), so part of the gap may come from the "
              "models, not the dubs. To compare them fairly, run them again with one model locked.",
        "ko": "서로 다른 AI 모델({models})이 더빙별 번역을 검사했으므로 차이의 일부는 더빙이 아니라 모델 때문일 수 있습니다. "
              "공정하게 비교하려면 모델 하나로 고정해 다시 실행하세요.",
        "pt": "Modelos de IA diferentes verificaram as traduções destas dublagens ({models}), então parte da diferença pode "
              "vir dos modelos, não das dublagens. Para comparar com justiça, rode de novo com um só modelo.",
        "es": "Modelos de IA distintos comprobaron las traducciones de estos doblajes ({models}), así que parte de la "
              "diferencia puede venir de los modelos, no de los doblajes. Para comparar con justicia, vuelve a ejecutarlos "
              "con un solo modelo.",
    },
    "c.not_ready": {
        "en": "Neither dub is ready to deliver: both have a Poor verdict. Dub {d} is the better starting point.",
        "ko": "두 더빙 모두 납품할 준비가 되지 않았습니다(둘 다 미흡 판정). 그래도 더빙 {d} 버전에서 시작하는 편이 낫습니다.",
        "pt": "Nenhuma dublagem está pronta para entrega: as duas têm resultado Ruim. A Dublagem {d} é o melhor ponto "
              "de partida.",
        "es": "Ningún doblaje está listo para entregar: los dos tienen resultado Deficiente. El Doblaje {d} es el mejor "
              "punto de partida.",
    },
    "c.not_ready_all": {
        "en": "None of the dubs is ready to deliver: all have a Poor verdict. Dub {d} is the best starting point.",
        "ko": "모든 더빙이 납품할 준비가 되지 않았습니다(모두 미흡 판정). 그래도 더빙 {d} 버전에서 시작하는 편이 가장 "
              "낫습니다.",
        "pt": "Nenhuma dublagem está pronta para entrega: todas têm resultado Ruim. A Dublagem {d} é o melhor ponto de "
              "partida.",
        "es": "Ningún doblaje está listo para entregar: todos tienen resultado Deficiente. El Doblaje {d} es el mejor "
              "punto de partida.",
    },
    "c.ranking_label": {"en": "Ranking", "ko": "순위", "pt": "Classificação", "es": "Clasificación"},
    "c.score_label": {"en": "Quality score (shown only; not part of the deciding rule)",
                      "ko": "품질 점수(참고용이며 결정 규칙에는 쓰지 않음)",
                      "pt": "Nota de qualidade (só exibida; não entra na regra de decisão)",
                      "es": "Puntuación de calidad (solo se muestra; no forma parte de la regla de decisión)"},
    "c.fix_first": {"en": "Fix first", "ko": "먼저 고칠 것", "pt": "Corrija primeiro", "es": "Corrige primero"},
    "c.verdict": {"en": "Verdict", "ko": "판정", "pt": "Resultado", "es": "Resultado"},
    "c.intervals_count_one": {"en": "{n} problem on the timeline, {sec} s in total", "ko": "문제 구간 {n}개, 총 {sec}초",
                              "pt": "{n} trecho com problema, {sec} s no total",
                              "es": "{n} tramo con problemas, {sec} s en total"},
    "c.intervals_count_many": {"en": "{n} problems on the timeline, {sec} s in total", "ko": "문제 구간 {n}개, 총 {sec}초",
                               "pt": "{n} trechos com problemas, {sec} s no total",
                               "es": "{n} tramos con problemas, {sec} s en total"},
    "c.no_intervals": {"en": "No problems on the timeline.", "ko": "문제 구간이 없습니다.", "pt": "Nenhum trecho com problema.",
                       "es": "Ningún tramo con problemas."},
    "c.asr": {"en": "Possible ASR errors (listed, not counted)", "ko": "음성 인식 오류 가능성(표시만 하고 집계하지 않음)",
              "pt": "Possíveis erros de reconhecimento de fala (listados, não contados)",
              "es": "Posibles errores del reconocimiento de voz (listados, no contados)"},
    "c.rule_label": {"en": "Deciding rule", "ko": "결정 규칙", "pt": "Regra decisiva", "es": "Regla decisiva"},
    "c.values_label": {"en": "Values", "ko": "값", "pt": "Valores", "es": "Valores"},
    "c.summary_label": {"en": "Summary", "ko": "요약", "pt": "Resumo", "es": "Resumen"},
    "c.skipped": {"en": "Rules skipped (a value is missing for one dub)", "ko": "건너뛴 규칙(한쪽 더빙에 값이 없음)",
                  "pt": "Regras ignoradas (falta um valor para uma dublagem)",
                  "es": "Reglas omitidas (falta un valor para un doblaje)"},
    "c.rule.measured": {"en": "1. More of the key checks measured", "ko": "1. 핵심 검사를 더 많이 측정함",
                        "pt": "1. Mais verificações principais medidas", "es": "1. Más comprobaciones clave medidas"},
    "c.shown.unmeasured": {"en": "{n} of {total} key checks not measured", "ko": "핵심 검사 {total}개 중 {n}개 측정 안 됨",
                           "pt": "{n} de {total} verificações principais não medidas",
                           "es": "{n} de {total} comprobaciones clave sin medir"},
    "c.why.measured": {
        "en": "Dub {win} could be measured on more of the key checks (speech timing, line length, voice clarity): "
              "{win_value}; Dub {lose}: {lose_value}. A dub whose speech couldn't be checked is not recommended over "
              "one that was, however good its verdict looks.",
        "ko": "더빙 {win} 쪽이 핵심 검사(발화 타이밍, 대사 길이, 음성 명료도)를 더 많이 측정할 수 있었습니다. 더빙 {win}: "
              "{win_value}, 더빙 {lose}: {lose_value}. 음성을 검사할 수 없었던 더빙은 판정이 아무리 좋아 보여도 검사된 "
              "더빙보다 먼저 추천하지 않습니다.",
        "pt": "A Dublagem {win} pôde ser medida em mais verificações principais (momento da fala, duração das falas, "
              "clareza da voz): {win_value}; Dublagem {lose}: {lose_value}. Uma dublagem cuja fala não pôde ser "
              "verificada não é recomendada acima de uma que foi, por melhor que pareça o resultado.",
        "es": "El Doblaje {win} se pudo medir en más comprobaciones clave (momento del habla, duración de las frases, "
              "claridad de la voz): {win_value}; Doblaje {lose}: {lose_value}. Un doblaje cuya habla no se pudo "
              "comprobar no se recomienda por encima de uno que sí, por bueno que parezca su resultado.",
    },
    "c.caution.unmeasured": {
        "en": "Careful: Dub {d} couldn't be measured on some key checks ({items}), so this recommendation rests on "
              "fewer checks than usual. Watch the dub before delivering it.",
        "ko": "주의: 더빙 {d} 버전은 일부 핵심 검사({items})를 측정할 수 없어, 이 추천은 평소보다 적은 검사에 근거합니다. "
              "납품 전에 직접 보고 확인하세요.",
        "pt": "Atenção: a Dublagem {d} não pôde ser medida em algumas verificações principais ({items}), então esta "
              "recomendação se baseia em menos verificações do que o normal. Assista à dublagem antes de entregá-la.",
        "es": "Cuidado: el Doblaje {d} no se pudo medir en algunas comprobaciones clave ({items}), así que esta "
              "recomendación se basa en menos comprobaciones de lo normal. Mira el doblaje antes de entregarlo.",
    },
    "c.rule.verdict": {"en": "2. Better overall verdict", "ko": "2. 더 좋은 전체 판정", "pt": "2. Melhor resultado geral",
                       "es": "2. Mejor resultado general"},
    "c.rule.poor_items": {"en": "3. Fewer Poor items", "ko": "3. 더 적은 미흡 항목", "pt": "3. Menos itens Ruins",
                          "es": "3. Menos elementos Deficientes"},
    "c.rule.check_items": {"en": "4. Fewer Needs review items", "ko": "4. 더 적은 검토 필요 항목", "pt": "4. Menos itens que precisam de revisão",
                           "es": "4. Menos elementos que necesitan revisión"},
    "c.rule.problem_seconds": {"en": "5. Less problem time on the timeline", "ko": "5. 문제 구간의 총 시간이 더 짧음",
                               "pt": "5. Menos tempo total em trechos com problemas",
                               "es": "5. Menos tiempo total en tramos con problemas"},
    "c.rule.meaning_score": {"en": "6. Higher translation meaning score", "ko": "6. 더 높은 번역 의미 점수",
                             "pt": "6. Maior nota de sentido da tradução", "es": "6. Mayor nota de sentido de la traducción"},
    "c.rule.speech_timing": {"en": "7. Higher speech-timing alignment", "ko": "7. 더 높은 발화 타이밍 일치도",
                             "pt": "7. Maior alinhamento do tempo de fala", "es": "7. Mayor alineación del momento del habla"},
    "c.rule.tie": {"en": "Tie: no rule separates the two dubs", "ko": "동점: 어떤 규칙으로도 두 더빙이 갈리지 않음",
                   "pt": "Empate: nenhuma regra separa as duas dublagens",
                   "es": "Empate: ninguna regla separa los dos doblajes"},
    "c.why.verdict": {
        "en": "Dub {win} has the better overall verdict ({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win} 쪽 전체 판정이 더 좋습니다({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} tem o melhor resultado geral ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} tiene el mejor resultado general ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.poor_items": {
        "en": "Dub {win} and Dub {lose} have the same verdict, and Dub {win} has fewer Poor items ({win_value}; Dub "
              "{lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정은 같지만 더빙 {win} 쪽 미흡 항목이 더 적습니다({win_value}, 더빙 {lose}: "
              "{lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} têm o mesmo resultado, e a Dublagem {win} tem menos itens Ruins "
              "({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} tienen el mismo resultado, y el Doblaje {win} tiene menos elementos "
              "Deficientes ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.check_items": {
        "en": "Dub {win} and Dub {lose} have the same verdict and Poor items, and Dub {win} has fewer Needs review items "
              "({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정과 미흡 항목 수는 같지만 더빙 {win} 쪽 검토 필요 항목이 더 적습니다"
              "({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} têm o mesmo resultado e itens Ruins, e a Dublagem {win} tem menos "
              "itens que precisam de revisão ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} tienen el mismo resultado y elementos Deficientes, y el Doblaje "
              "{win} tiene menos elementos que necesitan revisión ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.problem_seconds": {
        "en": "Dub {win} and Dub {lose} have the same verdict and item counts, and Dub {win} has less problem "
              "time on the timeline ({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정과 항목 수는 같지만 더빙 {win} 쪽 문제 구간의 총 시간이 더 짧습니다({win_value}, 더빙 {lose}: "
              "{lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} têm o mesmo resultado e o mesmo número de itens, e a "
              "Dublagem {win} tem menos tempo em trechos com problemas ({win_value}; Dublagem {lose}: "
              "{lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} tienen el mismo resultado y el mismo número de elementos, "
              "y el Doblaje {win} tiene menos tiempo en tramos con problemas ({win_value}; Doblaje {lose}: "
              "{lose_value}).",
    },
    "c.why.meaning_score": {
        "en": "Dub {win} and Dub {lose} are equal on verdict, items and problem time, and Dub {win} carries the "
              "original meaning better ({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정, 항목 수, 문제 시간은 같지만 더빙 {win} 쪽이 원본의 의미를 더 잘 "
              "전달합니다({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} empatam em resultado, itens e tempo com problemas, e a Dublagem "
              "{win} transmite melhor o sentido original ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} empatan en resultado, elementos y tiempo con problemas, y el "
              "Doblaje {win} transmite mejor el sentido original ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.speech_timing": {
        "en": "Dub {win} and Dub {lose} are equal on every earlier rule, and Dub {win} speaks more in time with the "
              "original ({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 앞 규칙은 모두 같지만 더빙 {win} 쪽이 원본과 더 같은 타이밍에 말합니다"
              "({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} empatam em todas as regras anteriores, e a Dublagem {win} fala mais "
              "no tempo do original ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} empatan en todas las reglas anteriores, y el Doblaje {win} habla "
              "más a tiempo con el original ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.tie": {
        "en": "Dub {d} and Dub {other} are tied on all seven rules, so Dub {d} is recommended because it comes first.",
        "ko": "더빙 {d}, 더빙 {other} 버전이 일곱 가지 규칙 모두에서 동점이라 순서상 먼저인 더빙 {d} 버전을 추천합니다.",
        "pt": "A Dublagem {d} e a Dublagem {other} empatam nas sete regras, então a Dublagem {d} é recomendada por vir "
              "primeiro.",
        "es": "El Doblaje {d} y el Doblaje {other} empatan en las siete reglas, así que se recomienda el Doblaje {d} "
              "por ir primero.",
    },
    "c.loser_problems": {
        "en": "Dub {dub}'s main problems: {items}.", "ko": "더빙 {dub} 버전의 주요 문제: {items}.",
        "pt": "Principais problemas da Dublagem {dub}: {items}.", "es": "Principales problemas del Doblaje {dub}: {items}.",
    },
    "c.loser_clean": {
        "en": "Dub {dub} has no Poor or Needs review items; it lost only on the rule above.",
        "ko": "더빙 {dub} 버전에는 미흡이나 검토 필요 항목이 없고, 위 규칙에서만 밀렸습니다.",
        "pt": "A Dublagem {dub} não tem itens Ruins nem itens que precisam de revisão; perdeu só na regra acima.",
        "es": "El Doblaje {dub} no tiene elementos Deficientes ni elementos que necesitan revisión; perdió solo en la regla de arriba.",
    },
    "c.ready.good": {
        "en": "Dub {dub} passed every automatic check and can be delivered.",
        "ko": "더빙 {dub} 버전은 모든 자동 검사를 통과해 납품할 수 있습니다.",
        "pt": "A Dublagem {dub} passou em todas as verificações automáticas e pode ser entregue.",
        "es": "El Doblaje {dub} pasó todas las comprobaciones automáticas y se puede entregar.",
    },
    "c.ready.check": {
        "en": "Dub {dub} can be delivered after a person reviews its Needs review items and its problems on "
              "the timeline.",
        "ko": "더빙 {dub} 버전은 사람이 검토 필요 항목과 문제 구간을 확인한 뒤 납품할 수 있습니다.",
        "pt": "A Dublagem {dub} pode ser entregue depois que uma pessoa revisar os itens que precisam de "
              "revisão e os trechos com problemas.",
        "es": "El Doblaje {dub} se puede entregar después de que una persona revise los elementos que "
              "necesitan revisión y los tramos con problemas.",
    },
    "c.ready.poor": {
        "en": "Fix Dub {dub}'s Poor items before delivering it.",
        "ko": "납품하기 전에 더빙 {dub} 버전의 미흡 항목을 고치세요.",
        "pt": "Corrija os itens Ruins da Dublagem {dub} antes de entregá-la.",
        "es": "Corrige los elementos Deficientes del Doblaje {dub} antes de entregarlo.",
    },
    "c.translation_used": {
        "en": "The translation check ran for every dub.", "ko": "번역 검토가 모든 더빙에 대해 실행됐습니다.",
        "pt": "A verificação da tradução foi feita em todas as dublagens.",
        "es": "La revisión de la traducción se hizo en todos los doblajes.",
    },
    "c.no_translation": {
        "en": "The translation check didn't run for {dubs}, so the decision was made without translation.",
        "ko": "번역 검토가 실행되지 않은 더빙이 있어({dubs}) 번역을 빼고 결정했습니다.",
        "pt": "A verificação da tradução não rodou para {dubs}, então a decisão foi tomada sem a tradução.",
        "es": "La revisión de la traducción no se hizo para {dubs}, así que la decisión se tomó sin la traducción.",
    },
    "c.rules_order": {
        "en": "Decision rule (stops at the first rule that separates the dubs): (1) more of the key checks "
              "measured (speech timing, line length, voice clarity), (2) better verdict, (3) fewer Poor items, "
              "(4) fewer Needs review items, (5) less problem time on the timeline, (6) higher meaning score, "
              "(7) higher speech-timing alignment; if still tied, the earlier dub (A before B). When DubEval "
              "isn't sure of the dub ranked first (little or unclear speech, or its translation wasn't "
              "checked), it holds the recommendation.",
        "ko": "결정 규칙(두 더빙이 처음으로 갈리는 규칙에서 멈춤): (1) 핵심 검사(발화 타이밍, 대사 길이, 음성 명료도)를 더 많이 측정함, (2) 더 좋은 판정, (3) 더 "
              "적은 미흡 항목, (4) 더 적은 검토 필요 항목, (5) 더 짧은 문제 구간 시간, (6) 더 높은 의미 점수, (7) 더 높은 발화 타이밍 일치도. 그래도 같으면 앞 "
              "순서의 더빙(A가 B보다 먼저). 1위 더빙을 확신할 수 없으면(말소리가 적거나 불분명함, 또는 번역을 확인하지 않음) 추천을 보류합니다.",
        "pt": "Regra de decisão (para na primeira regra que separa as dublagens): (1) mais verificações "
              "principais medidas (momento da fala, duração das falas, clareza da voz), (2) melhor resultado, "
              "(3) menos itens Ruins, (4) menos itens que precisam de revisão, (5) menos tempo em trechos com "
              "problemas, (6) maior nota de sentido, (7) maior alinhamento do tempo de fala; se ainda empatar, "
              "a dublagem anterior (A antes de B). Quando o DubEval não tem certeza da dublagem em primeiro "
              "lugar (pouca fala ou fala pouco clara, ou tradução não verificada), ele deixa a recomendação em "
              "suspenso.",
        "es": "Regla de decisión (se detiene en la primera regla que separa los doblajes): (1) más "
              "comprobaciones clave medidas (momento del habla, duración de las frases, claridad de la voz), "
              "(2) mejor resultado, (3) menos elementos Deficientes, (4) menos elementos que necesitan "
              "revisión, (5) menos tiempo en tramos con problemas, (6) mayor nota de sentido, (7) mayor "
              "alineación del momento del habla; si siguen empatados, el doblaje anterior (A antes que B). "
              "Cuando DubEval no está seguro del doblaje en primer lugar (se habla poco o la voz no se "
              "entiende bien, o la traducción no se comprobó), retiene la recomendación.",
    },
    "c.table.check": {"en": "Check", "ko": "항목", "pt": "Verificação", "es": "Comprobación"},
    "c.open_report": {"en": "Full report", "ko": "전체 보고서", "pt": "Relatório completo", "es": "Informe completo"},
    "c.meta.title": {"en": "Title", "ko": "제목", "pt": "Título", "es": "Título"},
    "c.meta.languages": {"en": "Languages", "ko": "언어", "pt": "Idiomas", "es": "Idiomas"},
    "c.meta.length": {"en": "Length", "ko": "길이", "pt": "Duração", "es": "Duración"},
    "c.meta.lipsync": {"en": "Lip-sync", "ko": "립싱크", "pt": "Sincronização labial", "es": "Sincronización labial"},
    "c.meta.project": {"en": "Perso project", "ko": "Perso 프로젝트", "pt": "Projeto Perso", "es": "Proyecto Perso"},
    "c.meta.evaluated": {"en": "Evaluated video", "ko": "평가한 영상", "pt": "Vídeo avaliado", "es": "Video evaluado"},
    "c.meta.link": {"en": "Link", "ko": "링크", "pt": "Link", "es": "Enlace"},
    "c.yes": {"en": "Yes", "ko": "예", "pt": "Sim", "es": "Sí"},
    "c.no": {"en": "No", "ko": "아니요", "pt": "Não", "es": "No"},
    "c.note.not_measured": {
        "en": "{label}, not measured for {dubs}. {reason}",
        "ko": "{label}: 측정하지 못함 ({dubs}). {reason}",
        "pt": "{label}: sem medição para {dubs}. {reason}",
        "es": "{label}, no medido en: {dubs}. {reason}",
    },
    "c.note.not_measured_each": {
        "en": "{label}, not measured. {items}",
        "ko": "{label}: 측정하지 못함. {items}",
        "pt": "{label}: sem medição. {items}",
        "es": "{label}, no medido. {items}",
    },
    "c.title_two": {"en": "{a} vs {b}", "ko": "{a} 대 {b}", "pt": "{a} x {b}", "es": "{a} vs. {b}"},
    "c.title_more": {"en": "{first} and {n} more", "ko": "{first} 외 {n}개", "pt": "{first} e mais {n}",
                     "es": "{first} y {n} más"},
    "c.note.same_reason": {
        "en": "{label}, not measured for {dubs}, for the same reason. {first}: {reason}",
        "ko": "{label}: 같은 이유로 측정하지 못함 ({dubs}). {first}: {reason}",
        "pt": "{label}: sem medição para {dubs}, pelo mesmo motivo. {first}: {reason}",
        "es": "{label}, no medido en: {dubs}, por el mismo motivo. {first}: {reason}",
    },
    "c.note.others_numbers_one": {"en": "The numbers for {others} are in its own report.",
                                  "ko": "다음 더빙의 수치는 해당 보고서에 있습니다: {others}.",
                                  "pt": "Os números de {others} estão no relatório dela.",
                                  "es": "Las cifras de {others} están en su propio informe."},
    "c.note.others_numbers_many": {"en": "The numbers for {others} are in their own reports.",
                                   "ko": "다음 더빙의 수치는 각 보고서에 있습니다: {others}.",
                                   "pt": "Os números de {others} estão nos relatórios delas.",
                                   "es": "Las cifras de {others} están en sus propios informes."},
    "c.every_dub": {"en": "any of the dubs", "ko": "모든 더빙", "pt": "todas as dublagens", "es": "todos los doblajes"},
    "c.both_dubs": {"en": "either dub", "ko": "두 더빙 모두", "pt": "as duas dublagens", "es": "los dos doblajes"},
    "c.note.same_project": {
        "en": "Both links point to the same Perso project, so the two results describe the same dub.",
        "ko": "두 링크가 같은 Perso 프로젝트를 가리켜 두 결과가 같은 더빙에 대한 것입니다.",
        "pt": "Os dois links apontam para o mesmo projeto Perso, então os dois resultados descrevem a mesma dublagem.",
        "es": "Los dos enlaces apuntan al mismo proyecto de Perso, así que los dos resultados describen el mismo doblaje.",
    },
    "c.note.other_video": {
        "en": "The two originals differ in length ({a} s and {b} s); the links may not be dubs of the same video.",
        "ko": "두 원본의 길이가 다릅니다({a}초, {b}초). 같은 영상의 더빙이 아닐 수 있습니다.",
        "pt": "Os dois originais têm durações diferentes ({a} s e {b} s); os links podem não ser do mesmo vídeo.",
        "es": "Los dos originales duran distinto ({a} s y {b} s); puede que los enlaces no sean del mismo video.",
    },
    "c.note.other_language": {
        "en": "The two dubs are in different languages ({a} and {b}).", "ko": "두 더빙의 언어가 다릅니다({a}, {b}).",
        "pt": "As duas dublagens estão em idiomas diferentes ({a} e {b}).",
        "es": "Los dos doblajes están en idiomas distintos ({a} y {b}).",
    },
    "c.note.none": {"en": "Everything was measured for every dub.", "ko": "모든 더빙에서 모든 항목을 측정했습니다.",
                    "pt": "Tudo foi medido em todas as dublagens.", "es": "Se midió todo en todos los doblajes."},
    "c.footer_no_time": {"en": "DubEval {version} · {time}", "ko": "DubEval {version} · {time}",
                         "pt": "DubEval {version} · {time}", "es": "DubEval {version} · {time}"},
    "c.footer": {"en": "DubEval {version} · run time {sec} s · {time}",
                 "ko": "DubEval {version} · 실행 시간 {sec}초 · {time}",
                 "pt": "DubEval {version} · tempo de execução {sec} s · {time}",
                 "es": "DubEval {version} · tiempo de ejecución {sec} s · {time}"},

    # ----- batch mode (dubeval/batch.py) -----
    "b.title": {"en": "Batch summary", "ko": "일괄 평가 요약", "pt": "Resumo do lote", "es": "Resumen del lote"},
    "b.counts": {"en": "{n} links: {good} Good · {check} Needs review · {poor} Poor · {failed} failed",
                 "ko": "링크 {n}개: 좋음 {good} · 검토 필요 {check} · 미흡 {poor} · 실패 {failed}",
                 "pt": "{n} links: {good} Bom · {check} Requer revisão · {poor} Ruim · {failed} com falha",
                 "es": "{n} enlaces: {good} Bien · {check} Requiere revisión · {poor} Deficiente · {failed} con error"},
    "b.failed": {"en": "could not evaluate", "ko": "평가하지 못함", "pt": "não foi possível avaliar", "es": "no se pudo evaluar"},
    "b.person": {"en": "person", "ko": "사람", "pt": "pessoa", "es": "persona"},
    "b.meaning": {"en": "meaning", "ko": "의미", "pt": "sentido", "es": "sentido"},
    "b.items": {"en": "{poor} Poor, {check} Needs review", "ko": "미흡 {poor}, 검토 필요 {check}", "pt": "{poor} Ruim, {check} Precisa de revisão",
                "es": "{poor} Deficiente, {check} Necesita revisión"},
    "b.agreement": {
        "en": "Agreement with your verdicts: {agree} of {n} ({pct}%). Stricter than you: {strict}. More lenient: {lenient}.",
        "ko": "사람 판정과 일치: {n}개 중 {agree}개({pct}%). 사람보다 엄격: {strict}, 사람보다 관대: {lenient}.",
        "pt": "Concordância com seus resultados: {agree} de {n} ({pct}%). Mais rigoroso que você: {strict}. Mais "
              "brando: {lenient}.",
        "es": "Coincidencia con tus resultados: {agree} de {n} ({pct}%). Más estricto que tú: {strict}. Más "
              "permisivo: {lenient}.",
    },
    "b.person_tool": {"en": "person ↓ / tool →", "ko": "사람 ↓ / 도구 →", "pt": "pessoa ↓ / ferramenta →",
                      "es": "persona ↓ / herramienta →"},
    "b.no_labels": {
        "en": "Add your own verdicts to see how often the tool agrees with you: after a link (link,good / check / "
              "poor), or in the label column of a test-set sheet.",
        "ko": "직접 판정을 넣으면 도구가 사람과 얼마나 일치하는지 볼 수 있습니다. 링크 뒤에 붙이거나(링크,good / check / "
              "poor) 테스트 세트 시트의 label 열에 적으세요.",
        "pt": "Adicione seus próprios resultados para ver quanto a ferramenta concorda com você: depois de um link "
              "(link,good / check / poor) ou na coluna label de uma planilha de teste.",
        "es": "Añade tus propios resultados para ver cuánto coincide la herramienta contigo: después de un enlace "
              "(enlace,good / check / poor) o en la columna label de una hoja de prueba.",
    },

    # ----- history (dubeval/history.py) -----
    "h.title": {"en": "Evaluation history", "ko": "평가 기록", "pt": "Histórico de avaliações", "es": "Historial de evaluaciones"},
    "h.empty": {"en": "No evaluations recorded yet. Every evaluation you run is added here.",
                "ko": "아직 기록된 평가가 없습니다. 평가를 실행할 때마다 여기에 추가됩니다.",
                "pt": "Nenhuma avaliação registrada ainda. Cada avaliação que você fizer aparece aqui.",
                "es": "Todavía no hay evaluaciones registradas. Cada evaluación que hagas se añade aquí."},
    "h.totals": {
        "en": "Dubs: {dubs} · evaluations run: {runs}. A dub evaluated again counts once.",
        "ko": "더빙: {dubs}개 · 실행한 평가: {runs}번. 다시 평가한 더빙은 한 번으로 셉니다.",
        "pt": "Dublagens: {dubs} · avaliações feitas: {runs}. Uma dublagem avaliada de novo conta só uma vez.",
        "es": "Doblajes: {dubs} · evaluaciones hechas: {runs}. Un doblaje evaluado de nuevo cuenta una vez.",
    },
    "h.pairs": {"en": "By language pair", "ko": "언어 쌍별", "pt": "Por par de idiomas", "es": "Por par de idiomas"},
    "h.pair": {"en": "Languages", "ko": "언어", "pt": "Idiomas", "es": "Idiomas"},
    "h.dubs": {"en": "Dubs", "ko": "더빙 수", "pt": "Dublagens", "es": "Doblajes"},
    "h.score": {"en": "Score", "ko": "점수", "pt": "Nota", "es": "Puntuación"},
    "h.score_avg": {"en": "Score (avg)", "ko": "점수(평균)", "pt": "Nota (média)", "es": "Puntuación (media)"},
    "h.timing": {"en": "Timing (avg)", "ko": "타이밍(평균)", "pt": "Tempo (média)", "es": "Momento (media)"},
    "h.meaning": {"en": "Meaning (avg)", "ko": "의미(평균)", "pt": "Sentido (média)", "es": "Sentido (media)"},
    "h.problems": {"en": "Most frequent problems", "ko": "가장 자주 나오는 문제", "pt": "Problemas mais frequentes",
                   "es": "Problemas más frecuentes"},
    "h.problem_counts": {"en": "Poor in {poor} dubs, Needs review in {check}", "ko": "미흡 {poor}개, 검토 필요 {check}개",
                         "pt": "Ruim em {poor} dublagens, Precisa de revisão em {check}",
                         "es": "Deficiente en {poor} doblajes, Necesita revisión en {check}"},
    "h.no_problems": {"en": "No measure was Needs review or Poor.", "ko": "검토 필요나 미흡 항목이 없습니다.",
                      "pt": "Nenhuma medida ficou em Precisa de revisão ou Ruim.", "es": "Ninguna medida quedó en Necesita revisión o Deficiente."},
    "h.weekly": {"en": "Week by week (█ Good ▒ Needs review ░ Poor)", "ko": "주별 추이(█ 좋음 ▒ 검토 필요 ░ 미흡)",
                 "pt": "Semana a semana (█ Bom ▒ Requer revisão ░ Ruim)", "es": "Semana a semana (█ Bien ▒ Requiere revisión ░ Deficiente)"},
    "h.week_counts": {"en": "{n} dubs: {good} / {check} / {poor}", "ko": "더빙 {n}개: {good} / {check} / {poor}",
                      "pt": "{n} dublagens: {good} / {check} / {poor}", "es": "{n} doblajes: {good} / {check} / {poor}"},
    "h.recent": {"en": "Latest evaluations", "ko": "최근 평가", "pt": "Avaliações recentes", "es": "Evaluaciones recientes"},
    "h.weekly_chart": {"en": "Week by week", "ko": "주별 추이", "pt": "Semana a semana", "es": "Semana a semana"},
    "h.week": {"en": "Week", "ko": "주", "pt": "Semana", "es": "Semana"},
    "h.when": {"en": "When", "ko": "시각", "pt": "Quando", "es": "Cuándo"},
    "h.mode": {"en": "From", "ko": "실행 방식", "pt": "Origem", "es": "Origen"},
    "h.days": {"en": "Period", "ko": "기간", "pt": "Período", "es": "Período"},
    "h.all_time": {"en": "All time", "ko": "전체", "pt": "Tudo", "es": "Todo"},
    "h.last_days": {"en": "Last {n} days", "ko": "최근 {n}일", "pt": "Últimos {n} dias", "es": "Últimos {n} días"},
    "h.open": {"en": "History", "ko": "평가 기록", "pt": "Histórico", "es": "Historial"},

    # ----- reviewer feedback (dubeval/feedback.py) -----
    "f.title": {"en": "Reviewer feedback", "ko": "검토자 피드백", "pt": "Opinião dos revisores", "es": "Opinión de los revisores"},
    "f.empty": {
        "en": "No votes yet. In the app, mark each problem on the timeline as a real problem (👍) or a false alarm (👎); this "
              "summary then shows which checks flag too much.",
        "ko": "아직 투표가 없습니다. 앱에서 각 문제 구간을 실제 문제(👍) 또는 잘못된 경고(👎)로 표시하면, 어떤 검사가 지나치게 "
              "많이 표시하는지 이 요약에서 보여 줍니다.",
        "pt": "Ainda não há votos. No app, marque cada trecho com problema como problema real (👍) ou alarme falso (👎); este "
              "resumo mostra então quais verificações sinalizam demais.",
        "es": "Todavía no hay votos. En la app, marca cada tramo con problemas como problema real (👍) o falsa alarma (👎); "
              "este resumen muestra luego qué comprobaciones marcan de más.",
    },
    "f.totals": {
        "en": "{n} intervals reviewed: {real} real problems, {false} false alarms ({pct}% confirmed).",
        "ko": "검토한 구간 {n}개: 실제 문제 {real}개, 잘못된 경고 {false}개(확인율 {pct}%).",
        "pt": "{n} trechos revisados: {real} problemas reais, {false} alarmes falsos ({pct}% confirmados).",
        "es": "{n} tramos revisados: {real} problemas reales, {false} falsas alarmas ({pct}% confirmados).",
    },
    "f.check": {"en": "Check", "ko": "검사", "pt": "Verificação", "es": "Comprobación"},
    "f.real": {"en": "Real problem", "ko": "실제 문제", "pt": "Problema real", "es": "Problema real"},
    "f.false": {"en": "False alarm", "ko": "잘못된 경고", "pt": "Alarme falso", "es": "Falsa alarma"},
    "f.confirmed": {"en": "Confirmed", "ko": "확인율", "pt": "Confirmados", "es": "Confirmados"},
    "f.status.few": {"en": "too few votes yet", "ko": "아직 투표가 적음", "pt": "poucos votos ainda", "es": "aún pocos votos"},
    "f.status.noisy": {"en": "flags too much: consider loosening its thresholds",
                       "ko": "지나치게 많이 표시함: 기준 완화를 검토하세요",
                       "pt": "sinaliza demais: considere afrouxar os limites",
                       "es": "marca de más: considera relajar sus umbrales"},
    "f.status.reliable": {"en": "reliable", "ko": "신뢰할 만함", "pt": "confiável", "es": "fiable"},
    "f.vote_real": {"en": "Real problem", "ko": "실제 문제", "pt": "Problema real", "es": "Problema real"},
    "f.vote_false": {"en": "False alarm", "ko": "잘못된 경고", "pt": "Alarme falso", "es": "Falsa alarma"},
    "f.saved_real": {"en": "Marked as a real problem.", "ko": "실제 문제로 표시했습니다.", "pt": "Marcado como problema real.",
                     "es": "Marcado como problema real."},
    "f.saved_false": {"en": "Marked as a false alarm.", "ko": "잘못된 경고로 표시했습니다.", "pt": "Marcado como alarme falso.",
                      "es": "Marcado como falsa alarma."},
    # The quality score (report._score)
    "r.score.h.title": {"en": "Quality score", "ko": "품질 점수", "pt": "Nota de qualidade", "es": "Puntuación de calidad"},
    "r.score.h.section": {"en": "Section", "ko": "항목", "pt": "Seção", "es": "Sección"},
    "r.score.h.got": {"en": "Points", "ko": "반영 점수", "pt": "Pontos", "es": "Puntos"},
    "r.score.value": {"en": "{score} / 100", "ko": "{score}/100", "pt": "{score} / 100", "es": "{score} / 100"},
    "r.score.of": {"en": "{got} of {share}", "ko": "{share}점 중 {got}점", "pt": "{got} de {share}", "es": "{got} de {share}"},
    "r.score.part_na": {"en": "Not checked", "ko": "확인 안 함", "pt": "Não verificado", "es": "No comprobado"},
    "r.score.lost_total": {"en": "{lost} points lost, so {score} / 100", "ko": "{lost}점이 깎여 {score}/100",
                           "pt": "{lost} pontos perdidos, então {score} / 100",
                           "es": "{lost} puntos perdidos, así que {score} / 100"},
    "r.score.lost_total_rounded": {"en": "{lost} points lost, so {score} / 100 (rounded)",
                                   "ko": "{lost}점이 깎여 {score}/100 (반올림)",
                                   "pt": "{lost} pontos perdidos, então {score} / 100 (arredondado)",
                                   "es": "{lost} puntos perdidos, así que {score} / 100 (redondeado)"},
    "r.score.lost_how": {
        "en": "A check that needs review loses points by how far its result is from Good; a Poor one costs a "
              "fixed amount by how serious it is: {critical} when it makes the dub unusable, {cost} for most "
              "problems, {minor} for ones the mix can fix.",
        "ko": "검토 필요인 검사는 결과가 좋음 기준에서 떨어진 만큼 점수를 잃고, 미흡인 검사는 심각한 정도에 따라 정해진 점수를 잃습니다: 더빙을 쓸 수 없게 만들면 "
              "{critical}점, 대부분의 문제는 {cost}점, 믹싱으로 고칠 수 있으면 {minor}점.",
        "pt": "Uma verificação que precisa de revisão perde pontos conforme o resultado se afasta de Bom; uma "
              "Ruim custa um valor fixo conforme a gravidade: {critical} quando torna a dublagem inutilizável, "
              "{cost} na maioria dos problemas, {minor} quando a mixagem resolve.",
        "es": "Una comprobación que necesita revisión pierde puntos según lo lejos que esté su resultado de "
              "Bien; una Deficiente cuesta una cantidad fija según su gravedad: {critical} si deja el doblaje "
              "inservible, {cost} en la mayoría de los problemas, {minor} si la mezcla lo arregla.",
    },
    "r.score.part_doesnt_apply": {
        "en": "Doesn't apply",
        "ko": "해당 없음",
        "pt": "Não se aplica",
        "es": "No aplica",
    },
    "r.score.item_doesnt_apply": {
        "en": "Doesn't apply to this dub · no share",
        "ko": "이 더빙에는 해당 없음 · 배점 없음",
        "pt": "Não se aplica a esta dublagem · sem parte",
        "es": "No aplica a este doblaje · sin parte",
    },
    "r.score.item_zero": {
        "en": "Counts as 0: the dub made it impossible to measure",
        "ko": "0점으로 계산: 더빙 때문에 측정할 수 없음",
        "pt": "Conta como 0: a dublagem impediu a medição",
        "es": "Cuenta como 0: el doblaje impidió medirlo",
    },
    "r.score.why_poor": {
        "en": "{result} · Poor: a serious problem",
        "ko": "{result} · 미흡: 심각한 문제",
        "pt": "{result} · Ruim: um problema sério",
        "es": "{result} · Deficiente: un problema grave",
    },
    "r.score.why_poor_unsure": {
        "en": "{result} · Poor, but DubEval isn't sure of it, so it loses only its share",
        "ko": "{result} · 미흡이지만 DubEval이 확신하지 못해 배점만 잃습니다",
        "pt": "{result} · Ruim, mas o DubEval não tem certeza, então só perde a sua parte",
        "es": "{result} · Deficiente, pero DubEval no está seguro, así que solo pierde su parte",
    },
    "r.score.lost_how_check": {
        "en": "A check that needs review loses points by how far its result is from Good.",
        "ko": "검토 필요인 검사는 결과가 좋음 기준에서 떨어진 만큼 점수를 잃습니다.",
        "pt": "Uma verificação que precisa de revisão perde pontos conforme o resultado se afasta de Bom.",
        "es": "Una comprobación que necesita revisión pierde puntos según lo lejos que esté su resultado de "
              "Bien.",
    },
    "r.score.poor_extra": {
        "en": "Poor results cost {extra} points more than their share, so the sections add up to {raw} but the "
              "score is {score}.",
        "ko": "미흡 결과는 배점보다 {extra}점을 더 잃으므로 항목별 점수의 합은 {raw}점이지만 최종 점수는 {score}점입니다.",
        "pt": "Os resultados Ruins custam {extra} pontos a mais que a sua parte, então as seções somam {raw}, "
              "mas a nota é {score}.",
        "es": "Los resultados Deficientes cuestan {extra} puntos más que su parte, así que las secciones suman "
              "{raw}, pero la puntuación es {score}.",
    },
    "r.score.h.extra": {
        "en": "Extra for Poor results",
        "ko": "미흡 결과 추가 감점",
        "pt": "Extra pelos resultados Ruins",
        "es": "Extra por resultados Deficientes",
    },
    "r.score.also_missing_one": {
        "en": "{checks} wasn't measured either, so its points go to the other checks in its section.",
        "ko": "측정하지 못한 검사가 하나 더 있습니다: {checks}. 그 배점은 같은 항목의 다른 검사에 나눠 줍니다.",
        "pt": "Também ficou sem medição: {checks}. Os seus pontos vão para as outras verificações da seção.",
        "es": "{checks} tampoco se midió, así que sus puntos van a las demás comprobaciones de su sección.",
    },
    "r.score.also_missing_many": {
        "en": "{checks} weren't measured either, so their points go to the other checks in their sections.",
        "ko": "측정하지 못한 검사가 더 있습니다: {checks}. 그 배점은 같은 항목의 다른 검사에 나눠 줍니다.",
        "pt": "Também ficaram sem medição: {checks}. Os seus pontos vão para as outras verificações das suas "
              "seções.",
        "es": "{checks} tampoco se midieron, así que sus puntos van a las demás comprobaciones de sus "
              "secciones.",
    },
    "r.score.why_poor_unusable": {
        "en": "{result} · Poor: makes the dub unusable",
        "ko": "{result} · 미흡: 더빙을 쓸 수 없게 만드는 문제",
        "pt": "{result} · Ruim: torna a dublagem inutilizável",
        "es": "{result} · Deficiente: deja el doblaje inservible",
    },
    "r.score.why_poor_minor": {
        "en": "{result} · Poor: the mix can fix it",
        "ko": "{result} · 미흡: 믹싱으로 고칠 수 있음",
        "pt": "{result} · Ruim: a mixagem resolve",
        "es": "{result} · Deficiente: la mezcla lo arregla",
    },
    "r.score.why_zero": {
        "en": "Couldn't be measured because of the dub itself, so it counts as 0",
        "ko": "더빙 자체 때문에 측정할 수 없어 0점으로 계산합니다",
        "pt": "Não pôde ser medida por causa da própria dublagem, então conta como 0",
        "es": "No se pudo medir por culpa del propio doblaje, así que cuenta como 0",
    },
    "r.score.provisional_coverage": {
        "en": "Provisional: only {pct}% of the checks that apply to this dub were measured (less than {min}%).",
        "ko": "잠정 점수: 이 더빙에 해당하는 검사 중 {pct}%만 측정했습니다({min}% 미만).",
        "pt": "Provisória: só foram medidas {pct}% das verificações que se aplicam a esta dublagem (menos de "
              "{min}%).",
        "es": "Provisional: solo se midió el {pct}% de las comprobaciones que aplican a este doblaje (menos "
              "del {min}%).",
    },
    "r.score.na_from_one": {
        "en": "{sections} doesn't apply to this dub, so its {weight} points are shared among the other "
              "sections.",
        "ko": "이 더빙에 해당하지 않는 항목: {sections}. 그 배점 {weight}점은 다른 항목에 나눠 줍니다.",
        "pt": "A seção {sections} não se aplica a esta dublagem, então os seus {weight} pontos são divididos "
              "entre as outras.",
        "es": "{sections} no aplica a este doblaje, así que sus {weight} puntos se reparten entre las demás "
              "secciones.",
    },
    "r.score.na_from_many": {
        "en": "{sections} don't apply to this dub, so their {weight} points are shared among the other "
              "sections.",
        "ko": "이 더빙에 해당하지 않는 항목: {sections}. 그 배점 {weight}점은 다른 항목에 나눠 줍니다.",
        "pt": "As seções {sections} não se aplicam a esta dublagem, então os seus {weight} pontos são "
              "divididos entre as outras.",
        "es": "{sections} no aplican a este doblaje, así que sus {weight} puntos se reparten entre las demás "
              "secciones.",
    },
    "r.score.too_little": {
        "en": "Only {pct}% of the checks that apply to this dub could be measured, too little for a score (it "
              "takes {min}%).",
        "ko": "이 더빙에 해당하는 검사 중 {pct}%만 측정할 수 있어 점수를 내기에 부족합니다({min}% 필요).",
        "pt": "Só {pct}% das verificações que se aplicam a esta dublagem puderam ser medidas, pouco demais "
              "para dar uma nota (são precisos {min}%).",
        "es": "Solo se pudo medir el {pct}% de las comprobaciones que aplican a este doblaje, demasiado poco "
              "para una puntuación (hace falta el {min}%).",
    },
    "r.score.too_little_display": {"en": "Too little measured", "ko": "측정한 검사가 너무 적음", "pt": "Pouco medido",
                                   "es": "Muy poco medido"},
    "r.score.coverage": {
        "en": "{pct}% of the checks that apply to this dub were measured.",
        "ko": "이 더빙에 해당하는 검사 중 {pct}%를 측정했습니다.",
        "pt": "Foram medidas {pct}% das verificações que se aplicam a esta dublagem.",
        "es": "Se midió el {pct}% de las comprobaciones que aplican a este doblaje.",
    },
    "r.score.dub_zero": {
        "en": "Couldn't be measured because of the dub itself, so they count as 0 instead of being shared: "
              "{checks}.",
        "ko": "더빙 자체 때문에 측정할 수 없는 검사는 나눠 주지 않고 0점으로 계산합니다: {checks}.",
        "pt": "Não puderam ser medidas por causa da própria dublagem e contam como 0, em vez de serem "
              "divididas: {checks}.",
        "es": "No se pudieron medir por culpa del propio doblaje y cuentan como 0 en vez de repartirse: "
              "{checks}.",
    },
    "r.score.item": {"en": "{share}% of the score → {got} points", "ko": "점수의 {share}% → {got}점",
                     "pt": "{share}% da nota → {got} pontos", "es": "{share}% de la puntuación → {got} puntos"},
    "r.score.item_na": {"en": "Not measured · no share", "ko": "측정 안 함 · 반영 없음", "pt": "Não medido · sem peso",
                        "es": "No medido · sin peso"},
    "r.score.h.lost": {"en": "Points lost", "ko": "깎인 점수", "pt": "Pontos perdidos", "es": "Puntos perdidos"},
    "r.score.h.how": {"en": "How the score is worked out", "ko": "점수 계산 방법", "pt": "Como a nota é calculada",
                      "es": "Cómo se calcula la puntuación"},
    "r.score.h.none": {"en": "No check lost points.", "ko": "점수가 깎인 검사가 없습니다.",
                       "pt": "Nenhuma verificação perdeu pontos.", "es": "Ninguna comprobación perdió puntos."},
    "r.score.lost": {"en": "−{lost} points", "ko": "−{lost}점", "pt": "−{lost} pontos", "es": "−{lost} puntos"},
    "r.score.share": {
        "en": "{got} of {share} points",
        "ko": "점수 {share}점 중 {got}점",
        "pt": "{got} de {share} pontos",
        "es": "{got} de {share} puntos",
    },
    "r.score.section": {
        "en": "{got} of {share} points",
        "ko": "점수 {share}점 중 {got}점",
        "pt": "{got} de {share} pontos",
        "es": "{got} de {share} puntos",
    },
    "r.score.item_out": {"en": "Not counted in the score", "ko": "점수에 반영 안 됨", "pt": "Não entra na nota",
                         "es": "No cuenta en la puntuación"},
    "r.score.part_needs": {
        "en": "Not counted: needs the {check}",
        "ko": "반영 안 됨: 필요한 검사가 실행되지 않음({check})",
        "pt": "Não conta: requer {check}",
        "es": "No cuenta: necesita la {check}",
    },
    "r.score.value_provisional": {"en": "{score} / 100 (provisional)", "ko": "{score}/100 (잠정)",
                                  "pt": "{score} / 100 (provisória)", "es": "{score} / 100 (provisional)"},
    "r.score.provisional": {
        "en": "Provisional: the translation wasn't checked, so {section} ({weight} points) isn't counted. The "
              "{check} row says why and how to turn the check on; numbers alone can't tell whether a "
              "translation is right.",
        "ko": "잠정 점수: 번역을 검사하지 않아 {section} 항목(배점 {weight}점)이 빠졌습니다. 이유와 검사를 켜는 방법은 '{check}' 항목에 있습니다. 숫자만으로는 "
              "번역이 맞는지 알 수 없습니다.",
        "pt": "Provisória: a tradução não foi verificada, então a seção {section} ({weight} pontos) não conta. "
              "A linha {check} diz por quê e como ativar a verificação; só os números não dizem se uma "
              "tradução está certa.",
        "es": "Provisional: la traducción no se comprobó, así que {section} ({weight} puntos) no cuenta. La "
              "fila {check} dice por qué y cómo activar la comprobación; los números por sí solos no dicen si "
              "una traducción es correcta.",
    },
    "r.tr.screen_removed": {
        "en": "This evaluation was made with an offline meaning check that DubEval no longer has: it found only about 1 in "
              "4 of the translation errors an AI checker finds, so its moments aren't shown any more.",
        "ko": "이 평가에는 DubEval에서 없앤 오프라인 의미 검사가 쓰였습니다. AI 검사기가 찾는 번역 오류 중 약 4분의 1만 찾아서 "
              "그 검사가 표시한 부분은 더 이상 보여 주지 않습니다.",
        "pt": "Esta avaliação foi feita com uma verificação de sentido offline que o DubEval não tem mais: ela encontrava "
              "só cerca de 1 em 4 dos erros de tradução que um verificador de IA encontra, então os seus momentos não "
              "aparecem mais.",
        "es": "Esta evaluación se hizo con una comprobación de sentido sin conexión que DubEval ya no tiene: encontraba "
              "solo alrededor de 1 de cada 4 errores de traducción que encuentra un verificador de IA, así que sus "
              "momentos ya no se muestran."},
    "r.score.na": {
        "en": "Not measured",
        "ko": "측정 안 함",
        "pt": "Não medido",
        "es": "No medido",
    },
    "r.score.na_why": {"en": "No weighted check could be graded, so there is no score.",
                       "ko": "가중치가 있는 검사 중 평가된 것이 없어 점수가 없습니다.",
                       "pt": "Nenhuma verificação com peso pôde ser avaliada, então não há nota.",
                       "es": "No se pudo evaluar ninguna comprobación con peso, así que no hay puntuación."},
    "r.score.all": {"en": "Every section was measured.", "ko": "모든 항목이 측정되었습니다.",
                    "pt": "Todas as seções foram medidas.", "es": "Se midieron todas las secciones."},
    "r.score.from_one": {
        "en": "{sections} wasn't checked, so its {weight} points are shared among the other sections.",
        "ko": "확인하지 않은 항목: {sections}. 그 배점 {weight}점은 다른 항목에 나눠 줍니다.",
        "pt": "A seção {sections} não foi verificada, então os seus {weight} pontos são divididos entre as "
              "outras.",
        "es": "{sections} no se comprobó, así que sus {weight} puntos se reparten entre las demás secciones.",
    },
    "r.score.from_many": {
        "en": "{sections} weren't checked, so their {weight} points are shared among the other sections.",
        "ko": "확인하지 않은 항목: {sections}. 그 배점 {weight}점은 다른 항목에 나눠 줍니다.",
        "pt": "As seções {sections} não foram verificadas, então os seus {weight} pontos são divididos entre "
              "as outras.",
        "es": "{sections} no se comprobaron, así que sus {weight} puntos se reparten entre las demás "
              "secciones.",
    },
    "r.score.and": {"en": " and ", "ko": ", ", "pt": " e ", "es": " y "},
    "r.score.section_out": {"en": "Not in the score", "ko": "점수에 반영 안 됨", "pt": "Não entra na nota",
                            "es": "No cuenta en la puntuación"},
    "r.score.weight": {"en": "{section} {weight}%", "ko": "{section} {weight}%", "pt": "{section} {weight}%",
                       "es": "{section} {weight}%"},
    "r.score.rule": {
        "en": "A summary for comparing dubs; it never replaces the checks.\n"
              "Each check: Good {good}, Poor {poor}; Needs review by where its result sits between the two "
              "limits (the translation check and voice quality: the share of lines or stretches without a "
              "problem; a check with no number to place: {check}).\n"
              "In a Poor verdict each Poor result costs at least a set amount by how serious it is, so one "
              "serious problem can't hide behind good ones: {critical} when it makes the dub unusable (no "
              "speech, the wrong language, another video, a broken file), {minor} when the mix can fix it "
              "(loudness, silence), {cost} for anything else.\n"
              "Each section: the average of its checks, added up by weight: {weights}.\n"
              "Not measured: a check that doesn't apply to this dub (lip sync on a dub that isn't lip-synced) "
              "is left out and its points shared; so is one that couldn't be measured, and the score says how "
              "much of what applies it covers (provisional under {coverage}%, no score under {floor}%); one "
              "the dub itself made impossible to measure (no speech in the dub) counts as 0.\n"
              "Only a dub with every check Good scores 100. The video file must pass and has no weight. The "
              "weights are reasoned, not yet tested against reviewers' grades.",
        "ko": "더빙을 비교하기 위한 요약이며 검사 결과를 대신하지 않습니다.\n"
              "검사별: 좋음 {good}점, 미흡 {poor}점이며, 검토 필요는 결과가 두 기준 사이 어디에 있는지에 따라 정합니다(번역 검사와 음성 품질은 문제가 없는 대사나 구간의 "
              "비율, 비교할 수치가 없는 검사는 {check}점).\n"
              "미흡 판정에서 미흡 결과는 심각한 정도에 따라 정해진 점수 이상을 잃으므로 심각한 문제 하나가 좋은 결과에 가려지지 않습니다: 더빙을 쓸 수 없게 만드는 문제(말소리 "
              "없음, 다른 언어, 다른 영상, 손상된 파일)는 {critical}점, 믹싱으로 고칠 수 있는 문제(음량, 무음)는 {minor}점, 그 밖의 문제는 "
              "{cost}점입니다.\n"
              "항목별: 검사 점수의 평균에 가중치를 반영해 더합니다(가중치: {weights}).\n"
              "측정 못 한 검사: 이 더빙에 해당하지 않는 검사(립싱크하지 않은 더빙의 립싱크)는 빼고 그 배점을 나눠 주며, 측정하지 못한 검사도 빼되 점수가 해당 검사의 몇 %를 "
              "반영하는지 표시합니다({coverage}% 미만이면 잠정 점수, {floor}% 미만이면 점수 없음). 더빙 자체 때문에 측정할 수 없는 검사(더빙에 말소리가 없음)는 "
              "0점으로 계산합니다.\n"
              "모든 검사가 좋음인 더빙만 100점입니다. 영상 파일 검사는 통과해야 하고 가중치는 없습니다. 가중치는 근거를 두고 정했지만 아직 검토자 평가와 대조해 검증하지 "
              "않았습니다.",
        "pt": "Um resumo para comparar dublagens; nunca substitui as verificações.\n"
              "Cada verificação: Bom {good}, Ruim {poor}; Precisa de revisão conforme o resultado fica entre "
              "os dois limites (a verificação da tradução e a qualidade da voz: a parte das falas ou trechos "
              "sem problema; uma verificação sem número para situar: {check}).\n"
              "Num resultado geral Ruim, cada resultado Ruim custa pelo menos um valor fixo conforme a "
              "gravidade, para que um problema sério não se esconda atrás dos bons: {critical} quando torna a "
              "dublagem inutilizável (sem fala, idioma errado, outro vídeo, arquivo danificado), {minor} "
              "quando a mixagem resolve (volume, silêncio), {cost} nos demais casos.\n"
              "Cada seção: a média das suas verificações, somada pelo peso: {weights}.\n"
              "Sem medição: uma verificação que não se aplica a esta dublagem (sincronia labial numa dublagem "
              "sem ela) fica de fora e os seus pontos são divididos; o mesmo vale para uma que não pôde ser "
              "medida, e a nota diz quanto do que se aplica ela cobre (provisória abaixo de {coverage}%, sem "
              "nota abaixo de {floor}%); uma que a própria dublagem impediu de medir (sem fala na dublagem) "
              "conta como 0.\n"
              "Só uma dublagem com todas as verificações Bom chega a 100. O arquivo de vídeo precisa passar e "
              "não tem peso. Os pesos foram definidos com critério, mas ainda não foram comparados com as "
              "notas de revisores.",
        "es": "Un resumen para comparar doblajes; nunca sustituye a las comprobaciones.\n"
              "Cada comprobación: Bien {good}, Deficiente {poor}; Necesita revisión según dónde queda su "
              "resultado entre los dos límites (la revisión de la traducción y la calidad de la voz: la parte "
              "de frases o tramos sin problema; una comprobación sin número que situar: {check}).\n"
              "Con un resultado general Deficiente, cada resultado Deficiente cuesta al menos una cantidad "
              "fija según su gravedad, para que un problema grave no se esconda tras los buenos: {critical} "
              "cuando deja el doblaje inservible (sin voz, idioma equivocado, otro video, archivo dañado), "
              "{minor} cuando la mezcla lo arregla (volumen, silencio), {cost} en los demás casos.\n"
              "Cada sección: la media de sus comprobaciones, sumada según su peso: {weights}.\n"
              "Sin medir: una comprobación que no aplica a este doblaje (la sincronización labial en un "
              "doblaje sin ella) queda fuera y sus puntos se reparten; igual una que no se pudo medir, y la "
              "puntuación dice cuánto de lo que aplica cubre (provisional por debajo del {coverage}%, sin "
              "puntuación por debajo del {floor}%); una que el propio doblaje impidió medir (sin voz en el "
              "doblaje) cuenta como 0.\n"
              "Solo un doblaje con todas las comprobaciones en Bien llega a 100. El archivo de video debe "
              "pasar y no tiene peso. Los pesos son razonados, pero aún no se han contrastado con las notas de "
              "revisores.",
    },
    "r.score.rule_short": {
        "en": "Each check scores {good} when Good, {poor} when Poor, and in between by its result when Needs "
              "review ({check} when it has no number); in a Poor verdict a Poor result costs {critical} points "
              "when it makes the dub unusable, otherwise at least {cost} ({minor} when the mix can fix it); "
              "sections are averaged and weighted ({weights}); checks that don't apply are left out, checks "
              "that couldn't be measured are left out and the score says how much it covers (provisional under "
              "{coverage}%, no score under {floor}%), and checks the dub itself made unmeasurable count as 0. "
              "The weights are reasoned, not yet tested against reviewers' grades.",
        "ko": "검사별 점수는 좋음 {good}점, 미흡 {poor}점이고, 검토 필요는 결과에 따라 그 사이(수치가 없으면 {check}점)입니다. 미흡 판정에서 미흡 결과는 더빙을 쓸 "
              "수 없게 만들면 {critical}점, 그 밖에는 최소 {cost}점(믹싱으로 고칠 수 있으면 {minor}점)을 잃습니다. 항목별 평균에 가중치를 "
              "반영합니다({weights}). 해당하지 않는 검사는 빼고, 측정하지 못한 검사도 빼되 반영 비율을 표시하며({coverage}% 미만이면 잠정 점수, {floor}% "
              "미만이면 점수 없음), 더빙 때문에 측정할 수 없는 검사는 0점입니다. 가중치는 근거를 두고 정했지만 아직 검토자 평가와 대조해 검증하지 않았습니다.",
        "pt": "Cada verificação vale {good} quando Bom, {poor} quando Ruim e, quando Precisa de revisão, um "
              "valor entre os dois conforme o resultado ({check} se não tem número); num resultado geral Ruim, "
              "um resultado Ruim custa {critical} pontos se torna a dublagem inutilizável e, nos demais casos, "
              "pelo menos {cost} ({minor} se a mixagem resolve); as seções são médias com pesos ({weights}); "
              "verificações que não se aplicam ficam de fora, as que não puderam ser medidas também, e a nota "
              "diz quanto cobre (provisória abaixo de {coverage}%, sem nota abaixo de {floor}%), e as que a "
              "própria dublagem impediu de medir contam como 0. Os pesos foram definidos com critério, mas "
              "ainda não foram comparados com as notas de revisores.",
        "es": "Cada comprobación vale {good} si es Bien, {poor} si es Deficiente y, si Necesita revisión, un "
              "valor entre ambos según su resultado ({check} si no tiene número); con un resultado general "
              "Deficiente, un resultado Deficiente cuesta {critical} puntos si deja el doblaje inservible y, "
              "en los demás casos, al menos {cost} ({minor} si la mezcla lo arregla); las secciones se "
              "promedian y se ponderan ({weights}); las comprobaciones que no aplican quedan fuera, las que no "
              "se pudieron medir también, y la puntuación dice cuánto cubre (provisional por debajo del "
              "{coverage}%, sin puntuación por debajo del {floor}%), y las que el propio doblaje impidió medir "
              "cuentan como 0. Los pesos son razonados, pero aún no se han contrastado con las notas de "
              "revisores.",
    },
}
