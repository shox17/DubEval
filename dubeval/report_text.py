"""Every sentence of the quality report in English, Korean, Portuguese (Brazil) and Spanish.

Keys start with "r."; dubeval/i18n.py merges them into TEXT, so tests/test_i18n.py checks that every entry has all four
languages with the same {placeholders}. Counted texts come in _one / _many pairs (see report._pl).
"""

REPORT_TEXT = {
    # ----- measure names -----
    "r.m.length_match": {"en": "Length match", "ko": "길이 일치", "pt": "Duração", "es": "Duración"},
    "r.m.loudness_match": {"en": "Loudness match", "ko": "음량 일치", "pt": "Volume", "es": "Volumen"},
    "r.m.silence": {"en": "Silence", "ko": "무음", "pt": "Silêncio", "es": "Silencio"},
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
    "r.m.lip_movement": {"en": "Lip movement", "ko": "입 움직임", "pt": "Movimento dos lábios",
                         "es": "Movimiento de los labios"},

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
        "en": "Good when the lengths differ by at most {good}%, Check up to {check}%, otherwise Poor.",
        "ko": "길이 차이가 {good}% 이하면 좋음, {check}% 이하면 확인 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se as durações diferem até {good}%, Verificar até {check}%, acima disso Ruim.",
        "es": "Bien si las duraciones difieren como mucho un {good}%, Revisar hasta un {check}%, si no Deficiente.",
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
        "en": "Good within {good} dB of the original, Check within {check} dB, otherwise Poor. About 1 dB is the "
              "smallest change most people can hear.",
        "ko": "원본과의 차이가 {good} dB 이내면 좋음, {check} dB 이내면 확인 필요, 그보다 크면 미흡입니다. 대부분의 "
              "사람은 약 1 dB부터 차이를 느낍니다.",
        "pt": "Bom até {good} dB de diferença do original, Verificar até {check} dB, acima disso Ruim. Cerca de 1 dB é a "
              "menor mudança que a maioria das pessoas percebe.",
        "es": "Bien hasta {good} dB de diferencia con el original, Revisar hasta {check} dB, si no Deficiente. Cerca de "
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
        "en": "Good when the dub is silent at most {good} points more of the time than the original, Check up to "
              "{check} points, otherwise Poor.",
        "ko": "더빙의 무음 비율이 원본보다 {good}%p 이하로 많으면 좋음, {check}%p 이하면 확인 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se a dublagem fica em silêncio no máximo {good} pontos a mais que o original, Verificar até {check} "
              "pontos, acima disso Ruim.",
        "es": "Bien si el doblaje está en silencio como mucho {good} puntos más que el original, Revisar hasta {check} "
              "puntos, si no Deficiente.",
    },

    # ----- clipping -----
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
        "en": "Good when at most {good}% of the audio hits the maximum level, Check up to {check}%, otherwise Poor.",
        "ko": "최대 음량에 닿는 비율이 {good}% 이하면 좋음, {check}% 이하면 확인 필요, 그보다 크면 미흡입니다.",
        "pt": "Bom se no máximo {good}% do áudio atinge o nível máximo, Verificar até {check}%, acima disso Ruim.",
        "es": "Bien si como mucho el {good}% del audio llega al nivel máximo, Revisar hasta el {check}%, si no Deficiente.",
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
        "en": "Good up to {good} {unit}, Check up to {check} {unit}, otherwise Poor (faster than people normally speak).",
        "ko": "{good} {unit}까지 좋음, {check} {unit}까지 확인 필요, 그보다 빠르면 미흡입니다(보통 사람이 말하는 속도보다 빠름).",
        "pt": "Bom até {good} {unit}, Verificar até {check} {unit}, acima disso Ruim (mais rápido do que se fala "
              "normalmente).",
        "es": "Bien hasta {good} {unit}, Revisar hasta {check} {unit}, si no Deficiente (más rápido de lo que se habla "
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
        "en": "Good when at least {good}% of the speech is understood clearly, Check from {check}%, otherwise Poor.",
        "ko": "말소리의 {good}% 이상을 또렷하게 알아들으면 좋음, {check}% 이상이면 확인 필요, 그보다 낮으면 미흡입니다.",
        "pt": "Bom se pelo menos {good}% da fala é entendida com clareza, Verificar a partir de {check}%, abaixo disso Ruim.",
        "es": "Bien si al menos el {good}% del habla se entiende con claridad, Revisar desde el {check}%, si no Deficiente.",
    },
    "r.script": {
        "en": "{acc} of your script was heard in the dub. A different but correct wording also lowers this score.",
        "ko": "스크립트의 {acc}가 더빙에서 들렸습니다. 표현이 다르지만 올바른 번역도 점수를 낮춥니다.",
        "pt": "{acc} do seu roteiro foi ouvido na dublagem. Uma redação diferente, mas correta, também baixa esta nota.",
        "es": "Se oyó el {acc} de tu guion en el doblaje. Una redacción distinta pero correcta también baja esta nota.",
    },
    "r.g.script": {
        "en": "Good from {good}%, Check from {check}%, otherwise Poor.",
        "ko": "{good}% 이상이면 좋음, {check}% 이상이면 확인 필요, 그보다 낮으면 미흡입니다.",
        "pt": "Bom a partir de {good}%, Verificar a partir de {check}%, abaixo disso Ruim.",
        "es": "Bien desde el {good}%, Revisar desde el {check}%, si no Deficiente.",
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
    "r.align.display": {"en": "{ov} lined up", "ko": "{ov} 일치", "pt": "{ov} coincide", "es": "{ov} coincide"},
    "r.g.align": {
        "en": "Good when at least {good}% of the speaking time lines up, Check from {check}%, otherwise Poor. Languages "
              "have different rhythms, so 100% isn't expected.",
        "ko": "말하는 시간의 {good}% 이상이 일치하면 좋음, {check}% 이상이면 확인 필요, 그보다 낮으면 미흡입니다. 언어마다 "
              "리듬이 달라 100%는 기대하지 않습니다.",
        "pt": "Bom se pelo menos {good}% do tempo de fala coincide, Verificar a partir de {check}%, abaixo disso Ruim. Cada "
              "idioma tem seu ritmo, então 100% não é esperado.",
        "es": "Bien si coincide al menos el {good}% del tiempo de habla, Revisar desde el {check}%, si no Deficiente. Cada "
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
    "r.earlier": {"en": "earlier", "ko": "일찍", "pt": "antes", "es": "antes"},

    # ----- translation -----
    "r.meaning.good": {
        "en": "The meaning comes across correctly.", "ko": "의미가 올바르게 전달됩니다.",
        "pt": "O sentido é transmitido corretamente.", "es": "El sentido se transmite correctamente.",
    },
    "r.meaning.check": {
        "en": "Some meaning is lost or changed; read the issues below.",
        "ko": "일부 의미가 빠지거나 달라졌습니다. 아래 문제를 확인하세요.",
        "pt": "Parte do sentido se perdeu ou mudou; leia os problemas abaixo.",
        "es": "Parte del sentido se pierde o cambia; lee los problemas de abajo.",
    },
    "r.meaning.poor": {
        "en": "The dub often says something different from the original; the translation needs to be redone.",
        "ko": "더빙이 원본과 다른 내용을 말하는 경우가 많습니다. 번역을 다시 해야 합니다.",
        "pt": "A dublagem muitas vezes diz algo diferente do original; a tradução precisa ser refeita.",
        "es": "El doblaje a menudo dice algo distinto del original; hay que rehacer la traducción.",
    },
    "r.g.meaning": {
        "en": "Rated 1–5 by {model} from both transcripts: Good from {good}, Check at {check}, otherwise Poor.",
        "ko": "두 받아쓰기를 비교해 1–5점으로 평가(평가 모델: {model}): {good}점 이상 좋음, {check}점 확인 필요, 그보다 낮으면 미흡.",
        "pt": "Nota de 1 a 5 dada por {model} com base nas duas transcrições: Bom a partir de {good}, Verificar em {check}, "
              "abaixo disso Ruim.",
        "es": "Nota de 1 a 5 de {model} a partir de las dos transcripciones: Bien desde {good}, Revisar en {check}, si no "
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
        "en": "Good with no problems, Check with minor ones only, Poor with any serious one. Probable speech-recognition "
              "errors don't count.",
        "ko": "문제가 없으면 좋음, 사소한 문제만 있으면 확인 필요, 심각한 문제가 하나라도 있으면 미흡입니다. 음성 인식 "
              "오류로 보이는 것은 계산하지 않습니다.",
        "pt": "Bom sem problemas, Verificar só com problemas leves, Ruim com qualquer problema grave. Prováveis erros do "
              "reconhecimento de fala não contam.",
        "es": "Bien sin problemas, Revisar solo con problemas leves, Deficiente con cualquier problema grave. Los "
              "probables errores del reconocimiento de voz no cuentan.",
    },
    "r.judge.off": {
        "en": "The translation check was turned off for this run.",
        "ko": "이번 실행에서는 번역 검토를 끄고 진행했습니다.",
        "pt": "A verificação da tradução foi desligada nesta execução.",
        "es": "La revisión de la traducción se desactivó en esta ejecución.",
    },
    "r.judge.unrecognized": {"en": "Not checked: speech recognition couldn't make out the dub's language, so its words can't be compared with the original. Add the dub's subtitle file, or try the large speech model.", "ko": "검사 안 함: 음성 인식이 더빙 언어를 알아듣지 못해 더빙의 말을 원본과 비교할 수 없습니다. 더빙 자막 파일을 추가하거나 큰 음성 인식 모델을 사용해 보세요.", "pt": "Não verificado: o reconhecimento de fala não entendeu o idioma da dublagem, então suas palavras não podem ser comparadas com o original. Adicione o arquivo de legendas da dublagem ou experimente o modelo de fala grande.", "es": "No comprobado: el reconocimiento de voz no entendió el idioma del doblaje, así que sus palabras no se pueden comparar con el original. Añade el archivo de subtítulos del doblaje o prueba el modelo de habla grande."},
    "r.screen.unrecognized": {"en": "Not compared: speech recognition couldn't make out the dub's language.", "ko": "비교 안 함: 음성 인식이 더빙 언어를 알아듣지 못했습니다.", "pt": "Não comparado: o reconhecimento de fala não entendeu o idioma da dublagem.", "es": "No comparado: el reconocimiento de voz no entendió el idioma del doblaje."},
    "r.m.naturalness": {"en": "Natural wording", "ko": "자연스러운 표현", "pt": "Naturalidade", "es": "Naturalidad"},
    "r.m.context_fit": {"en": "Fits the context", "ko": "문맥 일관성", "pt": "Coerência com o contexto", "es": "Coherencia con el contexto"},
    "r.m.terminology": {"en": "Consistent terms", "ko": "용어·표현 일관성", "pt": "Termos consistentes", "es": "Términos coherentes"},
    "r.m.localization": {"en": "Localization", "ko": "현지화", "pt": "Localização", "es": "Localización"},
    "r.rubric.summary": {"en": "Averages {avg} / 10 over {n} lines; {low} scored {flag} or lower.", "ko": "{n}개 줄 평균 {avg}/10점. {flag}점 이하인 줄 수: {low}.", "pt": "Média {avg} / 10 em {n} falas; {low} tiveram {flag} ou menos.", "es": "Promedio {avg} / 10 en {n} frases; {low} obtuvieron {flag} o menos."},
    "r.rubric.low_count_one": {"en": "{n} line ≤ {flag}", "ko": "{flag}점 이하 {n}줄", "pt": "{n} fala ≤ {flag}", "es": "{n} frase ≤ {flag}"},
    "r.rubric.low_count_many": {"en": "{n} lines ≤ {flag}", "ko": "{flag}점 이하 {n}줄", "pt": "{n} falas ≤ {flag}", "es": "{n} frases ≤ {flag}"},
    "r.g.rubric_meaning": {"en": "{model} scores every line from 1 to 10 for meaning, against written descriptions of each score. Poor when a line scores {poor} or lower, Check when a line scores {flag} or lower, otherwise Good. Lines that speech recognition may have misheard are listed but don't count.", "ko": "{model} 모델이 각 점수의 설명에 따라 모든 줄의 의미를 1~10점으로 평가합니다. 어느 줄이든 {poor}점 이하면 나쁨, {flag}점 이하면 확인 필요, 그 외에는 좋음입니다. 음성 인식이 잘못 들었을 수 있는 줄은 목록에만 표시하고 평가에 넣지 않습니다.", "pt": "{model} dá a cada fala uma nota de 1 a 10 para o sentido, seguindo descrições escritas de cada nota. Ruim quando uma fala tem {poor} ou menos, Verificar quando tem {flag} ou menos; senão, Bom. Falas que o reconhecimento de fala pode ter ouvido errado são listadas, mas não contam.", "es": "{model} puntúa cada frase de 1 a 10 por el sentido, según descripciones escritas de cada nota. Mal cuando una frase obtiene {poor} o menos, Revisar cuando obtiene {flag} o menos; si no, Bien. Las frases que el reconocimiento de voz pudo oír mal se listan, pero no cuentan."},
    "r.g.rubric_other": {"en": "{model} scores every line from 1 to 10, against written descriptions of each score. Check when a line scores {flag} or lower, otherwise Good. Lines that may be misheard don't count.", "ko": "{model} 모델이 각 점수의 설명에 따라 모든 줄을 1~10점으로 평가합니다. 어느 줄이든 {flag}점 이하면 확인 필요, 그 외에는 좋음입니다. 잘못 들었을 수 있는 줄은 평가에 넣지 않습니다.", "pt": "{model} dá a cada fala uma nota de 1 a 10, seguindo descrições escritas de cada nota. Verificar quando uma fala tem {flag} ou menos; senão, Bom. Falas que podem ter sido ouvidas errado não contam.", "es": "{model} puntúa cada frase de 1 a 10, según descripciones escritas de cada nota. Revisar cuando una frase obtiene {flag} o menos; si no, Bien. Las frases que pudieron oírse mal no cuentan."},
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
              ".env file), or run a local model with Ollama (ollama pull qwen3:8b), then run again.",
        "ko": "번역 검토에는 판정 모델이 필요합니다. 설정 → API 키(또는 .env 파일)에 Claude, Gemini, ChatGPT 키 중 하나를 "
              "추가하거나, Ollama로 로컬 모델을 실행한 뒤(ollama pull qwen3:8b) 다시 실행하세요.",
        "pt": "A verificação da tradução precisa de um avaliador: adicione uma chave do Claude, do Gemini ou do ChatGPT em "
              "Configurações → Chaves de API (ou no arquivo .env), ou rode um modelo local com o Ollama (ollama pull "
              "qwen3:8b), e execute de novo.",
        "es": "La revisión de la traducción necesita un evaluador: añade una clave de Claude, Gemini o ChatGPT en Ajustes "
              "→ Claves de API (o en el archivo .env), o ejecuta un modelo local con Ollama (ollama pull qwen3:8b), y "
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
    "r.judge.daily_quota": {"en": "{model} didn't check the translation: this API key has used up today's requests (a free key allows only a few dozen a day for each model). Run the evaluation again after the daily reset (midnight US Pacific time), turn on billing for the key, or choose another checker. The other results are not affected.", "ko": "{model} 번역 검사를 하지 못했습니다. 이 API 키의 오늘 요청 횟수를 모두 썼습니다(무료 키는 모델마다 하루 수십 번만 가능). 매일 초기화된 뒤(미국 태평양 시간 자정) 다시 평가하거나, 키에 결제를 켜거나, 다른 검사기를 고르세요. 다른 결과에는 영향이 없습니다.", "pt": "O {model} não verificou a tradução: esta chave de API usou todos os pedidos de hoje (uma chave gratuita permite só algumas dezenas por dia para cada modelo). Rode a avaliação de novo depois da renovação diária (meia-noite no horário do Pacífico dos EUA), ative o faturamento da chave ou escolha outro verificador. Os outros resultados não são afetados.", "es": "{model} no revisó la traducción: esta clave de API agotó las solicitudes de hoy (una clave gratuita permite solo unas decenas al día por modelo). Vuelve a evaluar tras el reinicio diario (medianoche, hora del Pacífico de EE. UU.), activa la facturación de la clave o elige otro revisor. Los demás resultados no se ven afectados."},
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
        "ko": "원본의 1개 부분({sec}초)이 더빙 영상에 없습니다. 확인할 항목에 표시했습니다.",
        "pt": "1 parte do original ({sec} s) não está na dublagem; ela aparece em Itens a verificar.",
        "es": "1 parte del original ({sec} s) no está en el doblaje; aparece en Cosas que revisar.",
    },
    "r.pair.cov_missing_many": {
        "en": "{n} parts of the original ({sec} s in all) aren't in the dub; they're listed under Things to check.",
        "ko": "원본의 {n}개 부분(모두 {sec}초)이 더빙 영상에 없습니다. 확인할 항목에 표시했습니다.",
        "pt": "{n} partes do original ({sec} s no total) não estão na dublagem; elas aparecem em Itens a verificar.",
        "es": "{n} partes del original ({sec} s en total) no están en el doblaje; aparecen en Cosas que revisar.",
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
              "file has no picture, the background sound matches), Check from {check}%, otherwise Poor.",
        "ko": "가장 잘 맞는 시간 어긋남에서 샘플 프레임의 {good}% 이상이 원본과 일치하면(화면이 없는 파일이면 배경음이 "
              "일치하면) 좋음, {check}% 이상이면 확인 필요, 그 미만이면 나쁨입니다.",
        "pt": "Bom quando pelo menos {good}% dos quadros amostrados coincidem com os do original no melhor deslocamento "
              "(ou, se um arquivo não tem imagem, o som de fundo coincide), Verificar a partir de {check}%, senão Ruim.",
        "es": "Bien cuando al menos el {good}% de los fotogramas muestreados coincide con el original en el mejor desfase "
              "(o, si un archivo no tiene imagen, el sonido de fondo coincide), Revisar desde el {check}%, si no Mal.",
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
        "en": "Good when at least {good}% of the original is found in the dub, Check from {check}%, otherwise Poor.",
        "ko": "원본의 {good}% 이상이 더빙 영상에 있으면 좋음, {check}% 이상이면 확인 필요, 그 미만이면 나쁨입니다.",
        "pt": "Bom quando pelo menos {good}% do original está na dublagem, Verificar a partir de {check}%, senão Ruim.",
        "es": "Bien cuando al menos el {good}% del original está en el doblaje, Revisar desde el {check}%, si no Mal.",
    },
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
        "en": "{bad} of {n} lines differ from the original's length by more than {band}% ({long} longer, {short} "
              "shorter). A line that's too long gets rushed or cut; one that's too short leaves the speaker's mouth "
              "moving in silence. They're listed under Things to check.",
        "ko": "대사 {n}개 중 {bad}개가 원본 길이와 {band}% 넘게 다릅니다(길어짐 {long}개, 짧아짐 {short}개). 너무 긴 대사는 "
              "빨라지거나 잘리고, 너무 짧은 대사는 입은 움직이는데 소리가 없습니다. 확인할 항목에 표시했습니다.",
        "pt": "{bad} de {n} falas diferem da duração original em mais de {band}% ({long} mais longas, {short} mais "
              "curtas). Uma fala longa demais fica corrida ou cortada; uma curta demais deixa a boca se mexendo em "
              "silêncio. Elas aparecem em Itens a verificar.",
        "es": "{bad} de {n} frases difieren de la duración original en más de un {band}% ({long} más largas, {short} "
              "más cortas). Una frase demasiado larga se acelera o se corta; una demasiado corta deja la boca moviéndose "
              "en silencio. Aparecen en Cosas que revisar.",
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
        "en": "1 dub line keeps going after the original's next line has started, so two lines overlap or the next one "
              "starts late. It's listed under Things to check.",
        "ko": "더빙 대사 1개가 다음 원본 대사가 시작된 뒤에도 이어져 두 대사가 겹치거나 다음 대사가 늦게 시작됩니다. 확인할 "
              "항목에 표시했습니다.",
        "pt": "1 fala da dublagem continua depois que a próxima fala do original começou, então as duas se sobrepõem ou a "
              "próxima começa atrasada. Ela aparece em Itens a verificar.",
        "es": "1 frase del doblaje sigue después de que empieza la siguiente frase del original, así que se solapan o la "
              "siguiente empieza tarde. Aparece en Cosas que revisar.",
    },
    "r.overrun.some_many": {
        "en": "{n} dub lines keep going after the original's next line has started, so lines overlap or start late. "
              "They're listed under Things to check.",
        "ko": "더빙 대사 {n}개가 다음 원본 대사가 시작된 뒤에도 이어져 대사가 겹치거나 늦게 시작됩니다. 확인할 항목에 "
              "표시했습니다.",
        "pt": "{n} falas da dublagem continuam depois que a próxima fala do original começou, então as falas se "
              "sobrepõem ou começam atrasadas. Elas aparecem em Itens a verificar.",
        "es": "{n} frases del doblaje siguen después de que empieza la siguiente frase del original, así que se solapan "
              "o empiezan tarde. Aparecen en Cosas que revisar.",
    },
    "r.overrun.display_one": {"en": "1 line", "ko": "1개 대사", "pt": "1 fala", "es": "1 frase"},
    "r.overrun.display_many": {"en": "{n} lines", "ko": "{n}개 대사", "pt": "{n} falas", "es": "{n} frases"},
    "r.g.line_length": {
        "en": "Each original line of at least {min} s is compared with the dub speech matched to it, from first to "
              "last word. Good when at least {good}% of the lines are within ±{band}%, Check from {check}%, otherwise "
              "Poor. Poor needs at least {count} lines off.",
        "ko": "{min}초 이상인 원본 대사마다 짝지은 더빙 음성과 첫 단어부터 마지막 단어까지 비교합니다. 대사의 {good}% 이상이 "
              "±{band}% 안이면 좋음, {check}% 이상이면 확인 필요, 그 미만이면 나쁨입니다. 나쁨은 맞지 않는 대사가 {count}개 이상일 때만입니다.",
        "pt": "Cada fala original de pelo menos {min} s é comparada com a fala da dublagem ligada a ela, da primeira à "
              "última palavra. Bom quando pelo menos {good}% das falas estão dentro de ±{band}%, Verificar a partir de "
              "{check}%, senão Ruim. Ruim exige pelo menos {count} falas fora.",
        "es": "Cada frase original de al menos {min} s se compara con la voz del doblaje emparejada, de la primera a la "
              "última palabra. Bien cuando al menos el {good}% de las frases está dentro de ±{band}%, Revisar desde el "
              "{check}%, si no Mal. Mal requiere al menos {count} frases fuera.",
    },
    "r.g.line_overrun": {
        "en": "A dub line runs over when it ends more than {sec} s after the original's next line starts. Good when "
              "none does, Check up to {share}% of the lines, otherwise Poor. Poor needs at least {count} such lines.",
        "ko": "더빙 대사가 다음 원본 대사 시작 후 {sec}초 넘게 이어지면 침범으로 봅니다. 하나도 없으면 좋음, 대사의 {share}%까지 "
              "확인 필요, 그보다 많으면 나쁨입니다. 나쁨은 그런 대사가 {count}개 이상일 때만입니다.",
        "pt": "Uma fala da dublagem invade quando termina mais de {sec} s depois do início da próxima fala do original. "
              "Bom quando nenhuma invade, Verificar até {share}% das falas, senão Ruim. Ruim exige pelo menos {count} falas assim.",
        "es": "Una frase del doblaje invade cuando termina más de {sec} s después de que empiece la siguiente frase del "
              "original. Bien cuando ninguna invade, Revisar hasta el {share}% de las frases, si no Mal. Mal requiere al menos {count} frases así.",
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

    # ----- meaning screen (dubeval/meaning.py) and dub types -----
    "r.m.meaning_screen": {"en": "Meaning similarity (offline)", "ko": "의미 유사도 (오프라인)",
                           "pt": "Semelhança de sentido (offline)", "es": "Similitud de sentido (sin conexión)"},
    "r.screen.display": {"en": "{low} of {n} lines low · median {median}", "ko": "{n}개 중 {low}개 낮음 · 중앙값 {median}",
                         "pt": "{low} de {n} falas baixas · mediana {median}",
                         "es": "{low} de {n} frases bajas · mediana {median}"},
    "r.screen.good": {
        "en": "Every line's meaning is close to the original's (median similarity {median}), by an offline comparison of "
              "the sentences.",
        "ko": "오프라인 문장 비교에서 모든 대사의 의미가 원본과 가깝습니다(유사도 중앙값 {median}).",
        "pt": "O sentido de todas as falas está próximo do original (semelhança mediana {median}), por uma comparação "
              "offline das frases.",
        "es": "El sentido de todas las frases está cerca del original (similitud mediana {median}), según una "
              "comparación sin conexión de las frases.",
    },
    "r.screen.low": {
        "en": "{low} of {n} lines may not mean what the original says (similarity below {min}). This quick offline "
              "comparison can be fooled by misheard words, so the translation check or a listen confirms it. They're "
              "listed under Things to check.",
        "ko": "대사 {n}개 중 {low}개가 원본과 뜻이 다를 수 있습니다(유사도 {min} 미만). 이 빠른 오프라인 비교는 잘못 인식된 "
              "단어에 속을 수 있으니 번역 검토나 직접 들어 보고 확인하세요. 확인할 항목에 표시했습니다.",
        "pt": "{low} de {n} falas podem não dizer o que o original diz (semelhança abaixo de {min}). Esta comparação "
              "offline rápida pode ser enganada por palavras mal reconhecidas; a verificação da tradução ou uma escuta "
              "confirma. Elas aparecem em Itens a verificar.",
        "es": "{low} de {n} frases pueden no decir lo que dice el original (similitud por debajo de {min}). Esta "
              "comparación rápida sin conexión puede confundirse con palabras mal reconocidas; la revisión de la "
              "traducción o una escucha lo confirma. Aparecen en Cosas que revisar.",
    },
    "r.screen.off": {
        "en": "The offline meaning comparison is turned off (DUBEVAL_MEANING_SCREEN=off).",
        "ko": "오프라인 의미 비교가 꺼져 있습니다(DUBEVAL_MEANING_SCREEN=off).",
        "pt": "A comparação de sentido offline está desligada (DUBEVAL_MEANING_SCREEN=off).",
        "es": "La comparación de sentido sin conexión está desactivada (DUBEVAL_MEANING_SCREEN=off).",
    },
    "r.screen.not_installed": {
        "en": "The offline meaning comparison isn't installed. Install it with: pip install \"dubeval[meaning]\".",
        "ko": "오프라인 의미 비교가 설치되어 있지 않습니다. 설치: pip install \"dubeval[meaning]\".",
        "pt": "A comparação de sentido offline não está instalada. Instale com: pip install \"dubeval[meaning]\".",
        "es": "La comparación de sentido sin conexión no está instalada. Instálala con: pip install \"dubeval[meaning]\".",
    },
    "r.screen.no_lines": {
        "en": "No line was spoken by both the original and the dub, so their meaning couldn't be compared.",
        "ko": "원본과 더빙이 함께 말한 대사가 없어 의미를 비교할 수 없었습니다.",
        "pt": "Nenhuma fala foi dita pelo original e pela dublagem, então o sentido não pôde ser comparado.",
        "es": "Ninguna frase la dicen a la vez el original y el doblaje, así que no se pudo comparar el sentido.",
    },
    "r.screen.error": {
        "en": "The offline meaning comparison couldn't run (the model couldn't be loaded); the other results are not affected.",
        "ko": "오프라인 의미 비교를 실행하지 못했습니다(모델을 불러오지 못함). 다른 결과에는 영향이 없습니다.",
        "pt": "A comparação de sentido offline não pôde ser executada (o modelo não carregou); os outros resultados não "
              "são afetados.",
        "es": "La comparación de sentido sin conexión no pudo ejecutarse (no se cargó el modelo); los demás resultados "
              "no se ven afectados.",
    },
    "r.g.meaning_screen": {
        "en": "A multilingual sentence model (BGE-M3) compares each original line with the dub line said at the same "
              "time, from 0 to 1. Good when no line scores below {min}, otherwise Check. Never Poor: the translation "
              "check decides.",
        "ko": "다국어 문장 모델(BGE-M3)이 원본 대사와 같은 시간의 더빙 대사를 0~1로 비교합니다. {min} 미만인 대사가 없으면 "
              "좋음, 있으면 확인 필요입니다. 나쁨은 없습니다(번역 검토가 판단).",
        "pt": "Um modelo de frases multilíngue (BGE-M3) compara cada fala original com a fala da dublagem no mesmo "
              "momento, de 0 a 1. Bom quando nenhuma fala fica abaixo de {min}, senão Verificar. Nunca Ruim: a "
              "verificação da tradução decide.",
        "es": "Un modelo de frases multilingüe (BGE-M3) compara cada frase original con la frase del doblaje dicha al "
              "mismo tiempo, de 0 a 1. Bien cuando ninguna frase queda por debajo de {min}, si no Revisar. Nunca Mal: "
              "la revisión de la traducción decide.",
    },
    "r.cat.meaning_drift": {"en": "meaning may differ", "ko": "의미 다를 수 있음", "pt": "sentido pode diferir",
                            "es": "el sentido puede diferir"},
    "r.int.meaning_drift": {
        "en": "Line {n}: the dub may not mean what the original says (similarity {sim}).",
        "ko": "{n}번 대사: 더빙이 원본과 뜻이 다를 수 있습니다(유사도 {sim}).",
        "pt": "Fala {n}: a dublagem pode não dizer o que o original diz (semelhança {sim}).",
        "es": "Frase {n}: el doblaje puede no decir lo que dice el original (similitud {sim}).",
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
              "other programs that use the graphics card, raise DUBEVAL_OLLAMA_TIMEOUT, or try a smaller model "
              "(DUBEVAL_OLLAMA_MODEL=qwen3:4b).",
        "ko": "로컬 판정 모델({model})이 {sec}초 안에 응답하지 않았습니다. 컴퓨터에 따라 로컬 모델은 느릴 수 있습니다. 그래픽 "
              "카드를 쓰는 다른 프로그램을 닫거나, DUBEVAL_OLLAMA_TIMEOUT을 늘리거나, 더 작은 모델"
              "(DUBEVAL_OLLAMA_MODEL=qwen3:4b)을 써 보세요.",
        "pt": "O avaliador local ({model}) não respondeu em {sec} s. Modelos locais são lentos em alguns computadores: "
              "feche outros programas que usam a placa de vídeo, aumente DUBEVAL_OLLAMA_TIMEOUT ou tente um modelo "
              "menor (DUBEVAL_OLLAMA_MODEL=qwen3:4b).",
        "es": "El evaluador local ({model}) no respondió en {sec} s. Los modelos locales son lentos en algunos equipos: "
              "cierra otros programas que usen la tarjeta gráfica, aumenta DUBEVAL_OLLAMA_TIMEOUT o prueba un modelo "
              "más pequeño (DUBEVAL_OLLAMA_MODEL=qwen3:4b).",
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
    "r.speech.none_dub": {"en": "No speech was recognized in the dub (music, singing or noise?) while the original has speech: a dub without a voice is graded Poor, and the speech, timing and meaning checks couldn't run. Listen to confirm.", "ko": "원본에는 음성이 있는데 더빙에서 인식된 음성이 없습니다(음악, 노래, 잡음?). 목소리가 없는 더빙은 나쁨으로 평가하며, 음성·타이밍·의미 검사를 할 수 없었습니다. 직접 들어 확인하세요.", "pt": "Nenhuma fala foi reconhecida na dublagem (música, canto ou ruído?), embora o original tenha fala: uma dublagem sem voz é avaliada como Ruim, e as verificações de fala, tempo e sentido não puderam rodar. Ouça para confirmar.", "es": "No se reconoció habla en el doblaje (¿música, canto o ruido?), aunque el original sí la tiene: un doblaje sin voz se califica como Mal, y no se pudieron hacer las comprobaciones de habla, tiempo y sentido. Escúchalo para confirmar."},
    "r.speech.none_original": {
        "en": "No speech was recognized in the original (music, singing or noise?), so the dub couldn't be compared "
              "with it. A person should watch it.",
        "ko": "원본에서 인식된 음성이 없어(음악, 노래, 잡음?) 더빙과 비교할 수 없었습니다. 직접 보고 확인하세요.",
        "pt": "Nenhuma fala foi reconhecida no original (música, canto ou ruído?), então a dublagem não pôde ser "
              "comparada com ele. Uma pessoa deve assistir.",
        "es": "No se reconoció habla en el original (¿música, canto o ruido?), así que el doblaje no se pudo comparar "
              "con él. Una persona debería verlo.",
    },
    "r.g.speech_found": {"en": "Poor when the dub has no recognized speech while the original has (nothing was dubbed); Check when the original has none: the checks that need speech can't run.", "ko": "원본에는 음성이 있는데 더빙에 인식된 음성이 전혀 없으면 나쁨(더빙되지 않음), 원본에 음성이 없으면 확인 필요입니다. 음성이 필요한 검사를 할 수 없습니다.", "pt": "Ruim quando a dublagem não tem fala reconhecida e o original tem (nada foi dublado); Verificar quando o original não tem: as verificações que precisam de fala não podem rodar.", "es": "Mal cuando el doblaje no tiene habla reconocida y el original sí (no se dobló nada); Revisar cuando el original no la tiene: las comprobaciones que necesitan habla no pueden hacerse."},
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
    "r.lips.info": {
        "en": "Mouth movement and voice line up with a score of {r}; the original video scores {orig}. Compare the two: "
              "a score close to or above the original's is better. This is an experimental hint, not a grade.",
        "ko": "입 움직임과 목소리의 일치 점수는 {r}이고, 원본 영상은 {orig}입니다. 두 값을 비교하세요. 원본에 가깝거나 "
              "더 높으면 좋습니다. 실험적인 참고 지표이며 등급이 아닙니다.",
        "pt": "O movimento da boca e a voz combinam com nota {r}; o vídeo original tem {orig}. Compare os dois: uma nota "
              "próxima ou acima da do original é melhor. É uma indicação experimental, não uma nota final.",
        "es": "El movimiento de la boca y la voz coinciden con una nota de {r}; el video original tiene {orig}. Compara las "
              "dos: una nota cercana o superior a la del original es mejor. Es una pista experimental, no una nota.",
    },
    "r.lips.display": {"en": "score {r}", "ko": "점수 {r}", "pt": "nota {r}", "es": "nota {r}"},
    "r.lips.not_lipsynced": {
        "en": "This dub isn't lip-synced, so there are no re-drawn lips to check.",
        "ko": "립싱크 영상이 아니라 다시 그려진 입 모양이 없어 확인할 것이 없습니다.",
        "pt": "Esta dublagem não tem sincronização labial, então não há lábios refeitos para verificar.",
        "es": "Este doblaje no tiene sincronización labial, así que no hay labios regenerados que revisar.",
    },
    "r.lips.skipped": {
        "en": "Lip movement was skipped for this run.", "ko": "이번 실행에서는 입 움직임 측정을 건너뛰었습니다.",
        "pt": "O movimento dos lábios foi pulado nesta execução.",
        "es": "El movimiento de los labios se omitió en esta ejecución.",
    },
    "r.lips.failed": {
        "en": "Lip movement couldn't be measured: {reason}", "ko": "입 움직임을 측정할 수 없습니다: {reason}",
        "pt": "Não foi possível medir o movimento dos lábios: {reason}",
        "es": "No se pudo medir el movimiento de los labios: {reason}",
    },
    "r.lips.no_video": {
        "en": "the video couldn't be opened.", "ko": "영상을 열 수 없습니다.",
        "pt": "o vídeo não pôde ser aberto.", "es": "no se pudo abrir el video.",
    },
    "r.lips.few_frames": {
        "en": "the video is too short (only {n} frames).", "ko": "영상이 너무 짧습니다({n}프레임).",
        "pt": "o vídeo é curto demais (só {n} quadros).", "es": "el video es demasiado corto (solo {n} fotogramas).",
    },
    "r.lips.few_faces": {
        "en": "a face is visible in only {pct} of the video.", "ko": "영상의 {pct}에서만 얼굴이 보입니다.",
        "pt": "um rosto aparece em só {pct} do vídeo.", "es": "solo se ve una cara en el {pct} del video.",
    },
    "r.lips.no_motion": {
        "en": "the mouth never moves.", "ko": "입이 움직이지 않습니다.",
        "pt": "a boca nunca se mexe.", "es": "la boca nunca se mueve.",
    },

    # ----- things to check -----
    "r.cat.timing": {"en": "timing", "ko": "타이밍", "pt": "tempo", "es": "momento"},
    "r.cat.clarity": {"en": "clarity", "ko": "명료도", "pt": "clareza", "es": "claridad"},
    "r.cat.missing": {"en": "missing speech", "ko": "누락된 말", "pt": "fala faltando", "es": "habla que falta"},
    "r.cat.added": {"en": "added speech", "ko": "추가된 말", "pt": "fala acrescentada", "es": "habla añadida"},
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
        "en": "The dub's voice sounds as clean as the original's where both speak (score {dub} against {orig} on a 1-5 "
              "scale). No robotic or distorted sound stands out.",
        "ko": "두 트랙이 함께 말하는 구간에서 더빙 목소리가 원본만큼 깨끗하게 들립니다(1~5점 중 더빙 {dub}, 원본 {orig}). "
              "기계음이나 찌그러짐이 눈에 띄지 않습니다.",
        "pt": "A voz da dublagem soa tão limpa quanto a do original onde os dois falam (nota {dub} contra {orig}, de 1 a "
              "5). Nenhum som robótico ou distorcido se destaca.",
        "es": "La voz del doblaje suena tan limpia como la del original donde hablan los dos (nota {dub} frente a "
              "{orig}, de 1 a 5). No destaca ningún sonido robótico ni distorsionado.",
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
        "en": "A voice-quality model trained on listener scores rates both tracks at the same moments (about 9 s each), "
              "where both speak, on a 1-5 scale for the voice and for the whole sound. A stretch is Check when the "
              "dub's voice scores {sig} or more below the original's or the whole sound {ovr} or more below, Poor from "
              "{sig_poor} / {ovr_poor}. The worst stretch sets the level. A muffled voice is not detected.",
        "ko": "청취자 평가로 학습한 목소리 품질 모델이 두 트랙이 함께 말하는 같은 순간(약 9초씩)을 목소리와 전체 소리에 "
              "대해 1~5점으로 평가합니다. 더빙 목소리 점수가 원본보다 {sig}점 이상 또는 전체 소리 점수가 {ovr}점 이상 "
              "낮으면 확인 필요, {sig_poor} / {ovr_poor}점 이상이면 미흡입니다. 가장 나쁜 구간이 등급을 정합니다. "
              "먹먹한 목소리는 감지하지 못합니다.",
        "pt": "Um modelo de qualidade de voz treinado com notas de ouvintes avalia as duas faixas nos mesmos momentos "
              "(cerca de 9 s cada), onde as duas falam, de 1 a 5 para a voz e para o som todo. Um trecho é Verificar "
              "quando a voz da dublagem fica {sig} ou mais abaixo da original ou o som todo {ovr} ou mais abaixo, Ruim "
              "a partir de {sig_poor} / {ovr_poor}. O pior trecho define o nível. Uma voz abafada não é detectada.",
        "es": "Un modelo de calidad de voz entrenado con notas de oyentes califica las dos pistas en los mismos momentos "
              "(unos 9 s cada uno), donde hablan las dos, de 1 a 5 para la voz y para todo el sonido. Un tramo es "
              "Revisar cuando la voz del doblaje queda {sig} o más por debajo de la original o todo el sonido {ovr} o "
              "más, Deficiente desde {sig_poor} / {ovr_poor}. El peor tramo fija el nivel. Una voz apagada no se "
              "detecta.",
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
        "en": "The dub voices sound like the original speakers ({sim} alike, typical over {n} lines compared at the "
              "same moments). The voice cloning kept each speaker recognisable.",
        "ko": "더빙 목소리가 원래 화자와 닮았습니다(같은 순간에 비교한 {n}문장의 대표 유사도 {sim}). 음성 복제가 각 화자를 "
              "알아볼 수 있게 유지했습니다.",
        "pt": "As vozes da dublagem se parecem com as dos falantes originais ({sim} de semelhança típica em {n} falas "
              "comparadas nos mesmos momentos). A clonagem manteve cada falante reconhecível.",
        "es": "Las voces del doblaje se parecen a las de los hablantes originales ({sim} de parecido típico en {n} "
              "frases comparadas en los mismos momentos). La clonación mantuvo reconocible a cada hablante.",
    },
    "r.vs.check": {
        "en": "The dub voices don't sound much like the original speakers ({sim} alike, typical over {n} lines). That's "
              "expected if a different voice was chosen on purpose; if the voice should be cloned, check the voice "
              "settings.",
        "ko": "더빙 목소리가 원래 화자와 그다지 닮지 않았습니다({n}문장의 대표 유사도 {sim}). 일부러 다른 목소리를 골랐다면 "
              "정상이지만, 목소리를 복제해야 한다면 음성 설정을 확인하세요.",
        "pt": "As vozes da dublagem não se parecem muito com as dos falantes originais ({sim} de semelhança típica em "
              "{n} falas). É esperado se outra voz foi escolhida de propósito; se a voz deveria ser clonada, revise a "
              "configuração.",
        "es": "Las voces del doblaje no se parecen mucho a las de los hablantes originales ({sim} de parecido típico "
              "en {n} frases). Es normal si se eligió otra voz a propósito; si la voz debía clonarse, revisa la "
              "configuración.",
    },
    "r.g.vs": {
        "en": "A speaker-recognition model compares the voice of each original line (2 s or longer, with a quiet "
              "background) with the dub at the same moment. The same voice scores about 80%, two different people "
              "about 10%. Good from {good}, otherwise Check (never Poor: a new voice can be a deliberate choice).",
        "ko": "화자 인식 모델이 원본의 각 문장(2초 이상, 배경이 조용한 부분)의 목소리를 같은 순간의 더빙과 비교합니다. "
              "같은 목소리는 약 80%, 서로 다른 사람은 약 10%입니다. {good}부터 좋음, 그 아래는 확인 필요입니다(일부러 "
              "다른 목소리를 고를 수 있어 미흡은 없음).",
        "pt": "Um modelo de reconhecimento de falante compara a voz de cada fala original (2 s ou mais, com fundo "
              "silencioso) com a dublagem no mesmo momento. A mesma voz dá cerca de 80%, duas pessoas diferentes cerca "
              "de 10%. Bom a partir de {good}, senão Verificar (nunca Ruim: outra voz pode ser uma escolha).",
        "es": "Un modelo de reconocimiento de hablante compara la voz de cada frase original (2 s o más, con fondo "
              "tranquilo) con el doblaje en el mismo momento. La misma voz da cerca del 80%, dos personas distintas "
              "cerca del 10%. Bien desde {good}, si no Revisar (nunca Deficiente: otra voz puede ser una elección).",
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
    "r.warn.lips": {
        "en": "Lip movement couldn't be measured on the dubbed video.",
        "ko": "더빙 영상에서 입 움직임을 측정할 수 없었습니다.",
        "pt": "Não foi possível medir o movimento dos lábios no vídeo dublado.",
        "es": "No se pudo medir el movimiento de los labios en el video doblado.",
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
        "en": "The dub looks mostly fine. {n} item needs a quick human check; see the details and Things to check.",
        "ko": "더빙이 대체로 괜찮습니다. {n}개 항목은 사람이 잠깐 확인해야 합니다. 세부 내용과 확인할 사항을 보세요.",
        "pt": "A dublagem parece boa no geral. {n} item precisa de uma conferência rápida; veja os detalhes e os Pontos a "
              "verificar.",
        "es": "El doblaje se ve bien en general. {n} elemento necesita una revisión rápida; mira los detalles y Cosas que "
              "revisar.",
    },
    "r.headline.check_many": {
        "en": "The dub looks mostly fine. {n} items need a quick human check; see the details and Things to check.",
        "ko": "더빙이 대체로 괜찮습니다. {n}개 항목은 사람이 잠깐 확인해야 합니다. 세부 내용과 확인할 사항을 보세요.",
        "pt": "A dublagem parece boa no geral. {n} itens precisam de uma conferência rápida; veja os detalhes e os Pontos a "
              "verificar.",
        "es": "El doblaje se ve bien en general. {n} elementos necesitan una revisión rápida; mira los detalles y Cosas que "
              "revisar.",
    },
    "r.headline.poor_one": {
        "en": "The dub has {n} serious problem that should be fixed before publishing.",
        "ko": "더빙에 게시 전에 고쳐야 할 심각한 문제가 {n}개 있습니다.",
        "pt": "A dublagem tem {n} problema grave que deve ser corrigido antes de publicar.",
        "es": "El doblaje tiene {n} problema grave que conviene corregir antes de publicar.",
    },
    "r.headline.poor_many": {
        "en": "The dub has {n} serious problems that should be fixed before publishing.",
        "ko": "더빙에 게시 전에 고쳐야 할 심각한 문제가 {n}개 있습니다.",
        "pt": "A dublagem tem {n} problemas graves que devem ser corrigidos antes de publicar.",
        "es": "El doblaje tiene {n} problemas graves que conviene corregir antes de publicar.",
    },
    "r.headline.plus_check_one": {
        "en": "{n} more item needs a quick check.", "ko": "그 밖에 {n}개 항목도 확인이 필요합니다.",
        "pt": "Mais {n} item precisa de conferência.", "es": "{n} elemento más necesita revisión.",
    },
    "r.headline.plus_check_many": {
        "en": "{n} more items need a quick check.", "ko": "그 밖에 {n}개 항목도 확인이 필요합니다.",
        "pt": "Mais {n} itens precisam de conferência.", "es": "{n} elementos más necesitan revisión.",
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
    "r.note.lipsync": {
        "en": "This measure is experimental: it is shown to help you look, but it never changes the overall verdict.",
        "ko": "이 항목은 실험적인 지표로, 확인에 참고하도록 보여 주지만 전체 판정에는 영향을 주지 않습니다.",
        "pt": "Esta medida é experimental: aparece para ajudar na conferência, mas nunca muda o resultado geral.",
        "es": "Esta medida es experimental: se muestra para ayudarte a revisar, pero nunca cambia el resultado general.",
    },
    "r.evaluated.lipsync": {"en": "lip-synced video", "ko": "립싱크 영상", "pt": "vídeo com sincronização labial",
                            "es": "video con sincronización labial"},
    "r.evaluated.dub": {"en": "dubbed video", "ko": "더빙 영상", "pt": "vídeo dublado", "es": "video doblado"},

    # ----- report labels (text and HTML versions) -----
    "r.label.title": {"en": "Dubbing QA Report", "ko": "더빙 품질 보고서", "pt": "Relatório de qualidade da dublagem",
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
    "r.label.generated": {"en": "Generated by DubEval.", "ko": "DubEval에서 생성했습니다.",
                          "pt": "Gerado pelo DubEval.", "es": "Generado por DubEval."},

    # ----- compare mode (dubeval/compare.py) -----
    "c.title": {"en": "Dub comparison", "ko": "더빙 비교", "pt": "Comparação de dublagens", "es": "Comparación de doblajes"},
    "c.sec.recommended": {"en": "Recommended version", "ko": "추천 버전", "pt": "Versão recomendada",
                          "es": "Versión recomendada"},
    "c.sec.intervals": {"en": "Problem intervals", "ko": "문제 구간", "pt": "Trechos com problemas",
                        "es": "Tramos con problemas"},
    "c.sec.reasoning": {"en": "Reasoning", "ko": "판단 근거", "pt": "Justificativa", "es": "Razonamiento"},
    "c.sec.table": {"en": "Every check, side by side", "ko": "전체 항목 나란히 보기", "pt": "Todas as verificações lado a lado",
                    "es": "Todas las comprobaciones, lado a lado"},
    "c.sec.links": {"en": "The two links", "ko": "두 링크 정보", "pt": "Os dois links", "es": "Los dos enlaces"},
    "c.sec.notes": {"en": "Measurement notes", "ko": "측정 참고 사항", "pt": "Notas sobre a medição",
                    "es": "Notas de medición"},
    "c.dub": {"en": "Dub {d}", "ko": "더빙 {d}", "pt": "Dublagem {d}", "es": "Doblaje {d}"},
    "c.recommend": {"en": "Deliver Dub {d}.", "ko": "더빙 {d} 버전을 납품하세요.", "pt": "Entregue a Dublagem {d}.",
                    "es": "Entrega el Doblaje {d}."},
    "c.recommend_tie": {
        "en": "Deliver Dub {d}. It is tied with Dub {other} on every rule, and comes first.",
        "ko": "더빙 {d} 버전을 납품하세요. 더빙 {other} 버전과 모든 규칙에서 동점이며 순서상 먼저입니다.",
        "pt": "Entregue a Dublagem {d}. Ela empata com a Dublagem {other} em todas as regras e vem primeiro.",
        "es": "Entrega el Doblaje {d}. Empata con el Doblaje {other} en todas las reglas y va primero.",
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
    "c.fix_first": {"en": "Fix first", "ko": "먼저 고칠 것", "pt": "Corrija primeiro", "es": "Corrige primero"},
    "c.verdict": {"en": "Verdict", "ko": "판정", "pt": "Resultado", "es": "Resultado"},
    "c.intervals_count_one": {"en": "{n} problem interval, {sec} s in total", "ko": "문제 구간 {n}개, 총 {sec}초",
                              "pt": "{n} trecho com problema, {sec} s no total",
                              "es": "{n} tramo con problemas, {sec} s en total"},
    "c.intervals_count_many": {"en": "{n} problem intervals, {sec} s in total", "ko": "문제 구간 {n}개, 총 {sec}초",
                               "pt": "{n} trechos com problemas, {sec} s no total",
                               "es": "{n} tramos con problemas, {sec} s en total"},
    "c.no_intervals": {"en": "No problem intervals.", "ko": "문제 구간이 없습니다.", "pt": "Nenhum trecho com problema.",
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
    "c.rule.check_items": {"en": "4. Fewer Check items", "ko": "4. 더 적은 확인 필요 항목", "pt": "4. Menos itens a Verificar",
                           "es": "4. Menos elementos a Revisar"},
    "c.rule.problem_seconds": {"en": "5. Less total time in problem intervals", "ko": "5. 문제 구간의 총 시간이 더 짧음",
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
        "en": "Dub {win} and Dub {lose} have the same verdict and Poor items, and Dub {win} has fewer Check items "
              "({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정과 미흡 항목 수는 같지만 더빙 {win} 쪽 확인 필요 항목이 더 적습니다"
              "({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} têm o mesmo resultado e itens Ruins, e a Dublagem {win} tem menos "
              "itens a Verificar ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} tienen el mismo resultado y elementos Deficientes, y el Doblaje "
              "{win} tiene menos elementos a Revisar ({win_value}; Doblaje {lose}: {lose_value}).",
    },
    "c.why.problem_seconds": {
        "en": "Dub {win} and Dub {lose} have the same verdict and item counts, and Dub {win} spends less time in "
              "problem intervals ({win_value}; Dub {lose}: {lose_value}).",
        "ko": "더빙 {win}, 더빙 {lose}의 판정과 항목 수는 같지만 더빙 {win} 쪽 문제 구간의 총 시간이 더 짧습니다"
              "({win_value}, 더빙 {lose}: {lose_value}).",
        "pt": "A Dublagem {win} e a Dublagem {lose} têm o mesmo resultado e contagens, e a Dublagem {win} passa menos "
              "tempo em trechos com problemas ({win_value}; Dublagem {lose}: {lose_value}).",
        "es": "El Doblaje {win} y el Doblaje {lose} tienen el mismo resultado y recuentos, y el Doblaje {win} pasa "
              "menos tiempo en tramos con problemas ({win_value}; Doblaje {lose}: {lose_value}).",
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
        "en": "Dub {dub} has no Poor or Check items; it lost only on the rule above.",
        "ko": "더빙 {dub} 버전에는 미흡이나 확인 필요 항목이 없고, 위 규칙에서만 밀렸습니다.",
        "pt": "A Dublagem {dub} não tem itens Ruins nem a Verificar; perdeu só na regra acima.",
        "es": "El Doblaje {dub} no tiene elementos Deficientes ni a Revisar; perdió solo en la regla de arriba.",
    },
    "c.ready.good": {
        "en": "Dub {dub} passed every automatic check and can be delivered.",
        "ko": "더빙 {dub} 버전은 모든 자동 검사를 통과해 납품할 수 있습니다.",
        "pt": "A Dublagem {dub} passou em todas as verificações automáticas e pode ser entregue.",
        "es": "El Doblaje {dub} pasó todas las comprobaciones automáticas y se puede entregar.",
    },
    "c.ready.check": {
        "en": "Dub {dub} can be delivered after a person reviews its Check items and problem intervals.",
        "ko": "더빙 {dub} 버전은 사람이 확인 필요 항목과 문제 구간을 검토한 뒤 납품할 수 있습니다.",
        "pt": "A Dublagem {dub} pode ser entregue depois que uma pessoa revisar os itens a Verificar e os trechos com "
              "problemas.",
        "es": "El Doblaje {dub} se puede entregar después de que una persona revise los elementos a Revisar y los "
              "tramos con problemas.",
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
        "en": "Decision rule (stops at the first rule that separates the dubs): 1 more of the key checks measured "
              "(speech timing, line length, voice clarity), 2 better verdict, 3 fewer Poor items, 4 fewer Check items, "
              "5 less time in problem intervals, 6 higher meaning score, 7 higher speech-timing alignment; if still "
              "tied, the earlier dub (A before B).",
        "ko": "결정 규칙(두 더빙이 처음으로 갈리는 규칙에서 멈춤): 1 핵심 검사(발화 타이밍, 대사 길이, 음성 명료도)를 더 많이 "
              "측정함, 2 더 좋은 판정, 3 더 적은 미흡 항목, 4 더 적은 확인 필요 항목, 5 더 짧은 문제 구간 시간, 6 더 높은 의미 "
              "점수, 7 더 높은 발화 타이밍 일치도. 그래도 같으면 앞 순서의 더빙(A가 B보다 먼저).",
        "pt": "Regra de decisão (para na primeira regra que separa as dublagens): 1 mais verificações principais medidas "
              "(momento da fala, duração das falas, clareza da voz), 2 melhor resultado, 3 menos itens Ruins, 4 menos "
              "itens a Verificar, 5 menos tempo em trechos com problemas, 6 maior nota de sentido, 7 maior alinhamento "
              "do tempo de fala; se ainda empatar, a dublagem anterior (A antes de B).",
        "es": "Regla de decisión (se detiene en la primera regla que separa los doblajes): 1 más comprobaciones clave "
              "medidas (momento del habla, duración de las frases, claridad de la voz), 2 mejor resultado, 3 menos "
              "elementos Deficientes, 4 menos elementos a Revisar, 5 menos tiempo en tramos con problemas, 6 mayor nota "
              "de sentido, 7 mayor alineación del habla; si siguen empatados, el doblaje anterior (A antes que B).",
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
    "c.note.not_measured": {"en": "Dub {dub}, not measured: {items}", "ko": "더빙 {dub}, 측정하지 못한 항목: {items}",
                            "pt": "Dublagem {dub}, não medido: {items}", "es": "Doblaje {dub}, no medido: {items}"},
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
    "b.items": {"en": "{poor} Poor, {check} Check", "ko": "미흡 {poor}, 확인 필요 {check}", "pt": "{poor} Ruim, {check} Verificar",
                "es": "{poor} Deficiente, {check} Revisar"},
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
        "en": "{runs} runs on {dubs} dubs (reruns of a link count once): {good} Good · {check} Needs review · {poor} "
              "Poor. {pct}% passed every automatic check.",
        "ko": "더빙 {dubs}개에 대해 {runs}번 실행(같은 링크의 재실행은 한 번으로 계산): 좋음 {good} · 검토 필요 {check} · "
              "미흡 {poor}. {pct}%가 모든 자동 검사를 통과했습니다.",
        "pt": "{runs} execuções em {dubs} dublagens (reexecuções de um link contam uma vez): {good} Bom · {check} Requer "
              "revisão · {poor} Ruim. {pct}% passaram em todas as verificações automáticas.",
        "es": "{runs} ejecuciones sobre {dubs} doblajes (las repeticiones de un enlace cuentan una vez): {good} Bien · "
              "{check} Requiere revisión · {poor} Deficiente. El {pct}% pasó todas las comprobaciones automáticas.",
    },
    "h.pairs": {"en": "By language pair", "ko": "언어 쌍별", "pt": "Por par de idiomas", "es": "Por par de idiomas"},
    "h.pair": {"en": "Languages", "ko": "언어", "pt": "Idiomas", "es": "Idiomas"},
    "h.dubs": {"en": "Dubs", "ko": "더빙 수", "pt": "Dublagens", "es": "Doblajes"},
    "h.timing": {"en": "Timing (avg)", "ko": "타이밍(평균)", "pt": "Tempo (média)", "es": "Momento (media)"},
    "h.meaning": {"en": "Meaning (avg)", "ko": "의미(평균)", "pt": "Sentido (média)", "es": "Sentido (media)"},
    "h.problems": {"en": "Most frequent problems", "ko": "가장 자주 나오는 문제", "pt": "Problemas mais frequentes",
                   "es": "Problemas más frecuentes"},
    "h.problem_counts": {"en": "Poor in {poor} dubs, Check in {check}", "ko": "미흡 {poor}개, 확인 필요 {check}개",
                         "pt": "Ruim em {poor} dublagens, Verificar em {check}",
                         "es": "Deficiente en {poor} doblajes, Revisar en {check}"},
    "h.no_problems": {"en": "No measure was Check or Poor.", "ko": "확인 필요나 미흡 항목이 없습니다.",
                      "pt": "Nenhuma medida ficou em Verificar ou Ruim.", "es": "Ninguna medida quedó en Revisar o Deficiente."},
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
    "h.good_pct": {"en": "Passed", "ko": "통과율", "pt": "Aprovadas", "es": "Aprobados"},
    "h.open": {"en": "History", "ko": "평가 기록", "pt": "Histórico", "es": "Historial"},

    # ----- reviewer feedback (dubeval/feedback.py) -----
    "f.title": {"en": "Reviewer feedback", "ko": "검토자 피드백", "pt": "Opinião dos revisores", "es": "Opinión de los revisores"},
    "f.empty": {
        "en": "No votes yet. In the app, mark each problem interval as a real problem (👍) or a false alarm (👎); this "
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
}
