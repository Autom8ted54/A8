"""Tests voor processor.cpv_filter.matches — pure logica, geen database."""

from processor.cpv_filter import matches


def test_exact_hoofdcode_matcht():
    assert matches(["79340000"]) is True


def test_specifiekere_subcode_matcht_op_prefix():
    assert matches(["79341400"]) is True  # campagnediensten onder reclamediensten


def test_irrelevante_code_matcht_niet():
    assert matches(["45000000"]) is False  # bouwwerkzaamheden


def test_mix_met_een_relevante_code_matcht():
    assert matches(["45000000", "79952000"]) is True


def test_lege_lijst_matcht_niet():
    assert matches([]) is False


def test_gelijkaardige_maar_andere_prefix_matcht_niet():
    # 79343xxx valt buiten de gekozen prefixen (79340/79341/79342)
    assert matches(["79343000"]) is False


def test_event_keywords_match_events_published_as_logistics():
    from processor.cpv_filter import is_relevant, matches_event_keywords

    assert matches_event_keywords("Logistieke ondersteuning van evenementen")
    assert matches_event_keywords("Organisation d'un Événement de lancement")
    assert matches_event_keywords(None, "Opbouw beursstand Batibouw")
    assert is_relevant(["60000000"], "Organisatie van de jaarlijkse infodagen")


def test_event_keywords_ignore_eventueel():
    from processor.cpv_filter import matches_event_keywords

    assert not matches_event_keywords("Levering van bureaumateriaal, eventueel met plaatsing")
    assert not matches_event_keywords(None, None)
