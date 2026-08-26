from app.services.hosted_email_abuse_service import HostedEmailAbuseService


def test_abuse_score_detects_keywords_links_and_caps():
    service = HostedEmailAbuseService()
    score, signals = service._heuristic_spam_score(
        "URGENT OFFER",
        "FREE MONEY https://a.test https://b.test https://c.test",
    )
    assert score > 0
    assert signals["keyword_hits"] >= 1
    assert signals["link_count"] == 3


def test_abuse_helpers_normalize_domains_and_hashes():
    service = HostedEmailAbuseService()
    assert service._extract_domain("User@Example.TEST") == "example.test"
    assert service._hash_text("same") == service._hash_text("same")
