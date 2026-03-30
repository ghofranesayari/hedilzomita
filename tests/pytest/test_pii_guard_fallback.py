from src.ingestion.pii_guard import PIIGuard


def test_pii_guard_regex_fallback_masks_email_and_phone():
    guard = PIIGuard.__new__(PIIGuard)
    guard.analyzer = None

    text = "Contact: jean.dupont@example.com, +33 7 53 00 10 67"
    anonymized = guard.anonymize_text(text)

    assert "<EMAIL>" in anonymized
    assert "<PHONE>" in anonymized
    assert "jean.dupont@example.com" not in anonymized
