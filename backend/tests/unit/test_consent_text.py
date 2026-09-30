"""The consent text versions the backend accepts must exist in docs/consent-text/."""

from app.core.config import REPO_ROOT, settings


def test_current_consent_texts_exist_and_match_their_version():
    for version in (settings.consent_text_face, settings.consent_text_voice):
        path = REPO_ROOT / "docs" / "consent-text" / f"{version}.md"
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert f"version: {version}" in text
        assert "—" not in text  # no em dash in user-facing text
        for topic in ("Data apa", "Untuk apa", "Berapa lama", "Cara mencabut"):
            assert topic in text, (version, topic)
