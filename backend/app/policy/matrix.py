"""The ARMOR decision matrix (CLAUDE.md bagian 7), as data.

Rows are the situation of one target; columns are the risk level. Each cell is
(decision, reason_code). Keeping it as a table makes it trivially reviewable
against CLAUDE.md and lets the tests iterate over every cell.
"""

from __future__ import annotations

from enum import Enum

from app.schema.common import Decision, RiskLevel

A, R, D = Decision.ALLOW, Decision.REVIEW, Decision.DENY
L, M, H, C = RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL


class Row(str, Enum):
    SELF = "SELF"
    # OTHER_REGISTERED with consent, a trusted-circle membership, or an owner
    # permission of ALLOW that covers this intent x media (a standing consent).
    REGISTERED_CONSENTED = "REGISTERED_CONSENTED"
    REGISTERED_NO_CONSENT = "REGISTERED_NO_CONSENT"
    REGISTERED_LOCKED = "REGISTERED_LOCKED"
    UNREGISTERED = "UNREGISTERED"
    UNCLEAR = "UNCLEAR"
    # No person detected at all (e.g. a landscape, or text with no name).
    NO_TARGET = "NO_TARGET"


MATRIX: dict[Row, dict[RiskLevel, tuple[Decision, str]]] = {
    Row.SELF: {
        L: (A, "SELF_ALLOWED"),
        M: (A, "SELF_ALLOWED"),
        H: (R, "SELF_HIGH_RISK_REVIEW"),
        C: (D, "SELF_CRITICAL_RISK"),
    },
    Row.REGISTERED_CONSENTED: {
        L: (A, "CONSENTED_ALLOWED"),
        M: (A, "CONSENTED_ALLOWED"),
        H: (R, "CONSENTED_HIGH_RISK_REVIEW"),
        C: (D, "CONSENTED_CRITICAL_RISK"),
    },
    Row.REGISTERED_NO_CONSENT: {
        L: (R, "CONSENT_REQUIRED"),
        M: (R, "CONSENT_REQUIRED"),
        H: (D, "NO_CONSENT_HIGH_RISK"),
        C: (D, "NO_CONSENT_HIGH_RISK"),
    },
    Row.REGISTERED_LOCKED: {
        L: (D, "IDENTITY_LOCKED"),
        M: (D, "IDENTITY_LOCKED"),
        H: (D, "IDENTITY_LOCKED"),
        C: (D, "IDENTITY_LOCKED"),
    },
    Row.UNREGISTERED: {
        L: (A, "UNREGISTERED_ALLOWED_LABEL"),
        M: (R, "UNREGISTERED_MEDIUM_REVIEW"),
        H: (D, "UNREGISTERED_HIGH_RISK"),
        C: (D, "UNREGISTERED_HIGH_RISK"),
    },
    Row.UNCLEAR: {
        L: (R, "UNCLEAR_REVIEW"),
        M: (R, "UNCLEAR_REVIEW"),
        H: (D, "UNCLEAR_HIGH_RISK"),
        C: (D, "UNCLEAR_HIGH_RISK"),
    },
    Row.NO_TARGET: {
        L: (A, "NO_TARGET_ALLOWED"),
        M: (A, "NO_TARGET_ALLOWED"),
        H: (R, "NO_TARGET_HIGH_RISK_REVIEW"),
        C: (D, "NO_TARGET_CRITICAL_RISK"),
    },
}


def lookup(row: Row, risk: RiskLevel) -> tuple[Decision, str]:
    return MATRIX[row][risk]
