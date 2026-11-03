"""Parse Sova Integrity Guard scores without requiring the feature on every test.

The sandbox score-push schema has not yet been confirmed against a real payload.
Keep vendor key aliases here so the mapping can be adjusted after inspection.
Never interpret a personality 'Integrity' competency as an Integrity Guard signal.
"""
import re


GUARD_KEYS = {"integrity_guard", "integrity_guard_results", "integrity_guard_result", "integrity_guard_data"}
OVERALL_KEYS = ("overall_status", "overall", "status", "code")
DESCRIPTION_KEYS = ("overall_description", "overall_status_description", "status_description", "description", "summary_description")
DIAGNOSTIC_KEYS = ("diagnostics", "diagnostic_statuses", "checks", "details")


def _key(value):
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value)).lower()).strip("_")


def _fields(mapping):
    return {_key(key): value for key, value in mapping.items()}


def _status(value, allowed):
    # bool is a subclass of int but is never a valid status from Sova.
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in allowed:
        return value
    if isinstance(value, str) and value.strip() in {str(i) for i in allowed}:
        return int(value.strip())
    return None


def _description(value):
    return value if isinstance(value, str) and value.strip() else None


def _diagnostics(value):
    """Keep only explicitly monitored diagnostics with statuses 1-3."""
    output = {}
    if isinstance(value, dict):
        for name, raw in value.items():
            if isinstance(raw, dict):
                fields = _fields(raw)
                raw = fields.get("status", fields.get("code"))
            status = _status(raw, {1, 2, 3})
            if status is not None:
                output[_key(name)] = status
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            fields = _fields(item)
            name = fields.get("name") or fields.get("diagnostic") or fields.get("key") or fields.get("type")
            status = _status(fields.get("status", fields.get("code")), {1, 2, 3})
            if isinstance(name, str) and name.strip() and status is not None:
                output[_key(name)] = status
    return output


def _guard_entry(value):
    if isinstance(value, (int, str)) and not isinstance(value, bool):
        status = _status(value, {0, 1, 2, 3})
        return {"overall_status": status, "overall_description": None, "diagnostics": {}} if status is not None else None
    if not isinstance(value, dict):
        return None
    fields = _fields(value)
    status = next(
        (code for name in OVERALL_KEYS if (code := _status(fields.get(name), {0, 1, 2, 3})) is not None),
        None,
    )
    description = next(
        (text for name in DESCRIPTION_KEYS if (text := _description(fields.get(name))) is not None),
        None,
    )
    diagnostics = {}
    for name in DIAGNOSTIC_KEYS:
        if name in fields:
            diagnostics.update(_diagnostics(fields[name]))

    # Some score templates expose each diagnostic directly within the guard object.
    for name, raw in fields.items():
        if name.endswith("_status") and name not in {"overall_status", "status", "status_description"}:
            diagnostic_name = name.removesuffix("_status")
            code = _status(raw, {1, 2, 3})
            if code is not None:
                diagnostics[diagnostic_name] = code

    if status is None and description is None and not diagnostics:
        return None
    return {"overall_status": status, "overall_description": description, "diagnostics": diagnostics}


def _inline_entry(value):
    """Support flattened score templates with explicit integrity_guard_ prefixes."""
    fields = _fields(value)
    guard_status = fields.get("integrity_guard_status", fields.get("integrity_guard_overall_status"))
    status = _status(guard_status, {0, 1, 2, 3})
    description = _description(
        fields.get("integrity_guard_description", fields.get("integrity_guard_status_description"))
    )
    diagnostics = {}
    for key in ("integrity_guard_diagnostics", "integrity_guard_diagnostic_statuses"):
        if key in fields:
            diagnostics.update(_diagnostics(fields[key]))
    if status is None and description is None and not diagnostics:
        return None
    return {"overall_status": status, "overall_description": description, "diagnostics": diagnostics}


def extract_integrity_guard(payload):
    """Return only validated Guard statuses, or None when absent.

    Discovery is restricted to keys explicitly naming Integrity Guard.
    Paths are structural (no candidate identifiers or raw payload content).
    """
    if not isinstance(payload, dict):
        return None

    entries = []

    def walk(value, path, depth=0):
        if depth > 16:
            return
        if isinstance(value, dict):
            flat = _inline_entry(value)
            if flat:
                entries.append({"path": path, **flat})
            for key, child in value.items():
                normalized = _key(key)
                child_path = f"{path}.{normalized}"
                if normalized in GUARD_KEYS:
                    entry = _guard_entry(child)
                    if entry:
                        entries.append({"path": child_path, **entry})
                else:
                    walk(child, child_path, depth + 1)
        elif isinstance(value, list):
            for index, child in enumerate(value[:500]):
                walk(child, f"{path}[{index}]", depth + 1)

    walk(payload, "payload")
    if not entries:
        return None

    # Keep all source entries, including separate assessments, rather than
    # silently collapsing conflicting per-test statuses.
    primary = next((entry for entry in entries if entry["overall_status"] is not None), entries[0])
    return {
        "overall_status": primary["overall_status"],
        "overall_description": primary["overall_description"],
        "diagnostics": primary["diagnostics"],
        "sources": entries,
    }


# Presentation mapping is deliberately deterministic. Integrity Guard never
# enters Talena's AI prompts, interpretation or candidate results portal.
_STATES = {0: "not_monitored", 1: "clear", 2: "concern", 3: "error"}

# Human-readable labels for documented Sova checks. Unknown vendor keys are
# merely formatted, never guessed or interpreted.
_DIAGNOSTIC_LABELS = {
    "ip": ("IP-adress", "IP address"),
    "ip_address": ("IP-adress", "IP address"),
    "collaboration_ip_address": ("IP-adress", "IP address"),
    "device": ("Enheter", "Devices"),
    "devices_used": ("Enheter", "Devices used"),
    "device_switching": ("Enhetsbyte", "Device switching"),
    "browser_patrolling": ("Byte av flik eller webbläsare", "Tab or browser switching"),
    "tab_switching": ("Byte av flik eller webbläsare", "Tab or browser switching"),
    "question_engagement": ("Svarsmönster", "Question engagement"),
    "response_pattern": ("Svarsmönster", "Response pattern"),
    "session_cookies": ("Webbläsarsessioner", "Browser sessions"),
}


def _effective_state(overall, diagnostics):
    """A flag in one assessment must not disappear behind a clear overall."""
    values = [overall] if overall in _STATES else []
    values.extend(code for code in diagnostics.values() if code in (1, 2, 3))
    for code in (2, 3, 1, 0):
        if code in values:
            return _STATES[code]
    return "unknown"


def integrity_guard_for_display(stored):
    """Build safe, static, UI-only statuses from validated Sova values.

    Do not expose structural payload paths, candidate identifiers, or raw
    diagnostic contents. The absence of data is NOT an all-clear.
    """
    if not isinstance(stored, dict) or not stored:
        return {"visible": False, "state": "unknown", "entries": []}

    raw_entries = stored.get("sources")
    if not isinstance(raw_entries, list) or not raw_entries:
        raw_entries = [stored]

    entries = []
    for raw in raw_entries[:100]:
        if not isinstance(raw, dict):
            continue
        overall = _status(raw.get("overall_status"), {0, 1, 2, 3})
        diagnostics = _diagnostics(raw.get("diagnostics"))
        description = _description(raw.get("overall_description"))
        state = _effective_state(overall, diagnostics)
        if state == "unknown" and not description:
            continue
        entries.append({
            "state": state,
            "description": description,
            "diagnostics": [
                {
                    "name_sv": _DIAGNOSTIC_LABELS.get(
                        name, (name.replace("_", " ").capitalize(),) * 2
                    )[0],
                    "name_en": _DIAGNOSTIC_LABELS.get(
                        name, (name.replace("_", " ").capitalize(),) * 2
                    )[1],
                    "state": _STATES[code],
                }
                for name, code in sorted(diagnostics.items())
            ],
        })

    # Combine every monitored assessment rather than presenting only the
    # first assessment's status. Most important is never hiding a concern.
    states = [entry["state"] for entry in entries]
    state = next((s for s in ("concern", "error", "clear", "not_monitored") if s in states), "unknown")
    return {"visible": bool(entries), "state": state, "entries": entries}


def without_integrity_guard(value):
    """Remove monitoring signals from any nested payload destined for AI.

    Only explicit Guard key families are stripped. A normal personality
    competency named "Integrity" remains valid assessment evidence.
    The original Sova data and stored diagnostics are not mutated.
    """
    if isinstance(value, dict):
        return {
            key: without_integrity_guard(child)
            for key, child in value.items()
            if not (_key(key) in GUARD_KEYS or _key(key).startswith("integrity_guard_"))
        }
    if isinstance(value, list):
        return [without_integrity_guard(child) for child in value]
    return value
