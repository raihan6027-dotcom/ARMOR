"""ARMOR Explain: human reasons and safe prompt suggestions per reason code.

Two audiences, two texts:

* `reason`: full Indonesian explanation for the identity owner and the audit log.
* the requester view (`public_code`, `message`, `suggestion`): never reveals
  whether another person is registered, has locked their identity, set a
  permission, or answered a consent request (CLAUDE.md bagian 7, pesan seragam).

All text is plain Indonesian without em dashes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schema.common import Decision, Intent

# --- Owner / audit reasons --------------------------------------------------

REASONS: dict[str, str] = {
    # Absolute rules
    "HARMFUL_IMPERSONATION": "Meniru orang lain seolah ia mengatakan atau melakukan sesuatu "
    "tidak diizinkan.",
    "HARMFUL_DEFAMATION": "Konten yang merendahkan atau mencemarkan nama baik orang lain tidak "
    "diizinkan.",
    "HARMFUL_SEXUAL": "Konten seksual yang memakai wajah, suara, atau nama orang lain tidak "
    "diizinkan.",
    "HARMFUL_DECEPTIVE": "Konten yang memakai orang lain untuk menipu atau menyesatkan tidak "
    "diizinkan.",
    "SATIRE_REALISTIC": "Satire yang tampak nyata dapat dikira kejadian sungguhan, sehingga "
    "diperlakukan seperti fitnah atau penipuan.",
    "VOICE_CLONE_NO_CONSENT": "Meniru suara orang lain membutuhkan persetujuan pemilik suara "
    "untuk media suara.",
    "GUARDIAN_CHILD": "Identitas ini didaftarkan lewat mode wali. Semua penggunaan identitas "
    "anak ditolak.",
    "PERMISSION_DENIED": "Pemilik identitas tidak mengizinkan tujuan ini untuk media ini.",
    "CONSENT_DENIED": "Pemilik identitas menolak permintaan persetujuan untuk penggunaan ini.",
    # Matrix
    "IDENTITY_LOCKED": "Pemilik mengunci identitasnya untuk media dan tujuan ini.",
    "SELF_ALLOWED": "Kamu memakai identitasmu sendiri dengan risiko rendah atau sedang.",
    "SELF_HIGH_RISK_REVIEW": "Kamu memakai identitasmu sendiri, tetapi risikonya tinggi sehingga "
    "perlu ditinjau.",
    "SELF_CRITICAL_RISK": "Risikonya sangat tinggi meskipun memakai identitasmu sendiri.",
    "CONSENTED_ALLOWED": "Pemilik identitas sudah mengizinkan penggunaan ini dan risikonya "
    "rendah atau sedang.",
    "CONSENTED_HIGH_RISK_REVIEW": "Pemilik sudah mengizinkan, tetapi risikonya tinggi sehingga "
    "perlu ditinjau.",
    "CONSENTED_CRITICAL_RISK": "Risikonya sangat tinggi meskipun pemilik sudah mengizinkan.",
    "CONSENT_REQUIRED": "Penggunaan identitas terdaftar ini membutuhkan persetujuan pemiliknya.",
    "NO_CONSENT_HIGH_RISK": "Risikonya tinggi dan pemilik identitas belum memberi persetujuan.",
    "UNREGISTERED_ALLOWED_LABEL": "Orang dalam media tidak terdaftar dan risikonya rendah. "
    "Hasil wajib diberi label AI.",
    "UNREGISTERED_MEDIUM_REVIEW": "Orang dalam media tidak terdaftar dan risikonya sedang, "
    "sehingga perlu ditinjau.",
    "UNREGISTERED_HIGH_RISK": "Risikonya tinggi untuk orang yang tidak bisa memberi persetujuan.",
    "UNCLEAR_REVIEW": "Wajah atau suara dalam media tidak cukup jelas untuk diperiksa.",
    "UNCLEAR_HIGH_RISK": "Wajah atau suara tidak jelas dan risikonya tinggi.",
    "NO_TARGET_ALLOWED": "Tidak ada orang yang terdeteksi dan risikonya rendah atau sedang.",
    "NO_TARGET_HIGH_RISK_REVIEW": "Tidak ada orang yang terdeteksi, tetapi risikonya tinggi.",
    "NO_TARGET_CRITICAL_RISK": "Risiko kontennya sangat tinggi.",
    # Fail-safe
    "COMPONENT_UNAVAILABLE": "Salah satu pemeriksaan AI tidak tersedia, jadi permintaan "
    "ditinjau dulu.",
    "RISK_UNDETERMINED": "Tingkat risiko tidak dapat ditentukan, jadi permintaan ditinjau dulu.",
    "INTENT_UNCERTAIN": "Tujuan permintaan tidak dapat dipastikan, jadi permintaan ditinjau dulu.",
}

# Reason codes that do not depend on who is registered: safe to show the requester.
_HARMFUL_CODES = {
    "HARMFUL_IMPERSONATION",
    "HARMFUL_DEFAMATION",
    "HARMFUL_SEXUAL",
    "HARMFUL_DECEPTIVE",
    "SATIRE_REALISTIC",
}
_FAIL_SAFE_CODES = {"COMPONENT_UNAVAILABLE", "RISK_UNDETERMINED"}

HARMFUL_CODE_BY_INTENT: dict[Intent, str] = {
    Intent.IMPERSONATION: "HARMFUL_IMPERSONATION",
    Intent.DEFAMATION: "HARMFUL_DEFAMATION",
    Intent.SEXUAL_EXPLICIT: "HARMFUL_SEXUAL",
    Intent.DECEPTIVE: "HARMFUL_DECEPTIVE",
}

# --- Safe prompt suggestions (nearest allowed intent) -----------------------

SUGGESTIONS: dict[str, str] = {
    "HARMFUL_IMPERSONATION": "Buat ilustrasi kartun orang ini tanpa menambahkan ucapan atau "
    "pernyataan apa pun.",
    "HARMFUL_DEFAMATION": "Buat karikatur superhero dari foto ini.",
    "HARMFUL_SEXUAL": "Buat ilustrasi karakter fiksi dengan pakaian sopan, tanpa wajah orang "
    "sungguhan.",
    "HARMFUL_DECEPTIVE": "Buat poster edukasi tentang cara mengenali penipuan, tanpa memakai "
    "wajah orang sungguhan.",
    "SATIRE_REALISTIC": "Buat versi karikatur bergaya kartun yang jelas bukan foto asli.",
    "VOICE_CLONE_NO_CONSENT": "Pakai suaramu sendiri atau suara sintetis umum untuk narasi ini.",
    "NOT_PERMITTED": "Pakai wajah atau suaramu sendiri, atau buat ilustrasi tanpa orang sungguhan.",
    "INTENT_UNCLEAR": "Jelaskan tujuan kontennya, misalnya: buat avatar kartun untuk foto profil "
    "pribadi.",
}

# Extra-specific DENY wording when the prompt shows a recognizable pattern.
_DEFAMATION_DETAIL = (
    (
        ("tahanan", "borgol", "penjara", "prisoner", "handcuff"),
        "Konten yang membuat orang lain terlihat seperti tahanan dapat mencemarkan nama baiknya.",
    ),
    (
        ("narkob", "drug", "mabuk"),
        "Konten yang mengaitkan orang lain dengan narkoba atau mabuk dapat mencemarkan nama "
        "baiknya.",
    ),
    (
        ("korupsi", "koruptor"),
        "Konten yang menuduh orang lain korupsi tanpa bukti dapat mencemarkan nama baiknya.",
    ),
)


@dataclass(frozen=True)
class RequesterView:
    public_code: str
    message: str
    suggestion: str | None


_PUBLIC_MESSAGES: dict[str, str] = {
    "ALLOWED": "Permintaan ini boleh diproses. Hasilnya akan diberi label AI.",
    "NEEDS_REVIEW": "Permintaan ini perlu ditinjau sebelum diproses.",
    "CHECK_UNAVAILABLE": "Salah satu pemeriksaan sedang tidak tersedia, jadi permintaan ini "
    "ditinjau dulu sebelum diproses.",
    "INTENT_UNCLEAR": "Tujuan permintaan ini belum jelas. Tambahkan konteks agar bisa diperiksa.",
    "NOT_PERMITTED": "Permintaan ini tidak dapat diproses karena berisiko merugikan orang yang "
    "ada di dalamnya.",
    "VOICE_CLONE_NOT_ALLOWED": "Meniru suara orang lain tanpa persetujuannya tidak diizinkan.",
}


def reason_for(code: str, prompt: str | None = None) -> str:
    if code == "HARMFUL_DEFAMATION" and prompt:
        low = prompt.lower()
        for keywords, text in _DEFAMATION_DETAIL:
            if any(k in low for k in keywords):
                return text
    return REASONS[code]


def requester_view(
    decision: Decision,
    reason_code: str,
    *,
    only_self: bool,
    prompt: str | None = None,
) -> RequesterView:
    """Map an internal reason code to what the requester is allowed to see.

    When every target is the requester (or there is no person at all), nothing
    about a third party can leak, so the full reason is shown.
    """
    # Fail-safe outcomes never depend on who is registered: same public code for all.
    if reason_code in _FAIL_SAFE_CODES:
        return RequesterView("CHECK_UNAVAILABLE", _PUBLIC_MESSAGES["CHECK_UNAVAILABLE"], None)
    if reason_code == "INTENT_UNCERTAIN":
        return RequesterView(
            "INTENT_UNCLEAR", _PUBLIC_MESSAGES["INTENT_UNCLEAR"], SUGGESTIONS["INTENT_UNCLEAR"]
        )
    if only_self:
        suggestion = SUGGESTIONS.get(reason_code)
        return RequesterView(reason_code, reason_for(reason_code, prompt), suggestion)

    if reason_code in _HARMFUL_CODES:
        return RequesterView(
            reason_code, reason_for(reason_code, prompt), SUGGESTIONS.get(reason_code)
        )
    if reason_code == "VOICE_CLONE_NO_CONSENT":
        return RequesterView(
            "VOICE_CLONE_NOT_ALLOWED",
            _PUBLIC_MESSAGES["VOICE_CLONE_NOT_ALLOWED"],
            SUGGESTIONS["VOICE_CLONE_NO_CONSENT"],
        )
    if decision is Decision.ALLOW:
        return RequesterView("ALLOWED", _PUBLIC_MESSAGES["ALLOWED"], None)
    if decision is Decision.REVIEW:
        return RequesterView("NEEDS_REVIEW", _PUBLIC_MESSAGES["NEEDS_REVIEW"], None)
    return RequesterView(
        "NOT_PERMITTED", _PUBLIC_MESSAGES["NOT_PERMITTED"], SUGGESTIONS["NOT_PERMITTED"]
    )
