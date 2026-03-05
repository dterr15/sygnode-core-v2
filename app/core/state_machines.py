"""
State Machines — R5: Explicit, validated transitions.
All 5 machines from doc 03 implemented as pure functions.
"""

from fastapi import HTTPException


# ─── 1. IntakeList (validation_status) ───
INTAKE_VALIDATION_TRANSITIONS: dict[str, list[str]] = {
    "STAGED_PENDING_VALIDATION": ["APPROVED_GENERATED", "REJECTED_MIN_DATA_PENDING"],
    "APPROVED_GENERATED": ["PENDIENTE_REVISION"],
    "REJECTED_MIN_DATA_PENDING": [],
}

# ─── 1b. IntakeList (status — operational) ───
INTAKE_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "PENDIENTE_REVISION": ["EN_COTIZACION", "ARCHIVADA"],
    "EN_COTIZACION": ["CERRADA", "ARCHIVADA"],
    "ARCHIVADA": [],
    "CERRADA": [],
}

# ─── 2. DecisionCase ───
CASE_TRANSITIONS: dict[str, list[str]] = {
    "OPEN": ["FROZEN", "ARCHIVED"],
    "FROZEN": ["ARCHIVED"],
    "ARCHIVED": [],
}

# ─── 3. RFQ ───
RFQ_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["open"],
    "open": ["sent"],
    "sent": ["closed"],
    "closed": [],
}

# ─── 4. Quote ───
QUOTE_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["approved", "rejected"],
    "approved": [],
    "rejected": [],
}

# ─── 5. CaseFulfillment ───
FULFILLMENT_TRANSITIONS: dict[str, list[str]] = {
    "PENDING": ["MATCH", "VARIANCE_JUSTIFIED"],
    "MATCH": [],
    "VARIANCE_JUSTIFIED": [],
}


def validate_transition(machine: dict[str, list[str]], current: str, target: str) -> None:
    """
    Validate a state transition. Raises ValueError with specific message
    if the transition is not allowed.
    """
    allowed = machine.get(current, [])
    if target not in allowed:
        raise ValueError(f"Transición {current} → {target} no permitida")


def validate_intake_validation_transition(current: str, target: str) -> None:
    validate_transition(INTAKE_VALIDATION_TRANSITIONS, current, target)


def validate_intake_status_transition(current: str, target: str) -> None:
    validate_transition(INTAKE_STATUS_TRANSITIONS, current, target)


def validate_case_transition(current: str, target: str, actor_role: str) -> None:
    """Case transitions require admin_org or master_admin."""
    if actor_role not in ("admin_org", "master_admin"):
        raise PermissionError("Solo admin_org puede transicionar casos")
    validate_transition(CASE_TRANSITIONS, current, target)


def validate_rfq_transition(current: str, target: str) -> None:
    validate_transition(RFQ_TRANSITIONS, current, target)


def validate_quote_transition(current: str, target: str) -> None:
    validate_transition(QUOTE_TRANSITIONS, current, target)


def validate_fulfillment_transition(current: str, target: str) -> None:
    validate_transition(FULFILLMENT_TRANSITIONS, current, target)
