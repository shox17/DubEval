

def test_subtitle_agreement_ignores_case_punctuation_and_spacing():
    from dubeval.evaluate import subtitle_agreement
    heard = [{"text": "hammaga salom men"}, {"text": "Frensisman"}]
    cues = [{"text": "Hammaga salom!"}, {"text": "Men  Frensisman."}]
    assert subtitle_agreement(heard, cues) == 1.0
    assert subtitle_agreement(heard, [{"text": "completely different words here"}]) < 0.45
    assert subtitle_agreement([], cues) is None and subtitle_agreement(heard, None) is None
