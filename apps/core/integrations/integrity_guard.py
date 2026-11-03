"""Parse Sova Integrity Guard scores without requiring the feature on every test.

The Integrity Guard score-push schema was confirmed from a production test
on 2026-11-03. Its `integrity_findings` contain diagnostic IDs, statuses,
and per-activity statuses. Keep vendor aliases for backwards compatibility.
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



# Numeric IDs and meanings are confirmed by comparing an actual Sova score
# callback with the corresponding four controls in the Sova recruiter UI.
# This is a vendor data mapping, NOT an AI inference.
SOVA_DIAGNOSTIC_IDS = {
    1: "ip_address",
    2: "devices_used",
    3: "browser_patrolling",
    4: "question_engagement",
}


def _sova_findings(value):
    """Normalise the real Sova integrity_findings structure.

    The nested activity status is specific to a monitoring check; never treat
    it as the assessment's completion status.
    """
    if not isinstance(value, list):
        return []
    output = []
    for raw in value[:30]:
        if not isinstance(raw, dict):
            continue
        fields = _fields(raw)
        identifier = fields.get("diagnostic")
        if isinstance(identifier, bool):
            continue
        if isinstance(identifier, str) and identifier.isdigit():
            identifier = int(identifier)
        if not isinstance(identifier, int) or not 1 <= identifier <= 999:
            continue
        status = _status(fields.get("diagnostic_status"), {1, 2, 3})
        if status is None:
            continue

        activities = []
        for activity in (fields.get("activities") or [])[:100] if isinstance(fields.get("activities"), list) else []:
            if not isinstance(activity, dict):
                continue
            item = _fields(activity)
            name = item.get("activity")
            activity_status = _status(item.get("status"), {1, 2, 3})
            if isinstance(name, str) and name.strip() and activity_status is not None:
                activities.append({"name": name.strip()[:160], "status": activity_status})

        key = SOVA_DIAGNOSTIC_IDS.get(identifier, f"diagnostic_{identifier}")
        output.append({
            "key": key,
            "status": status,
            "activities": activities,
        })
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

    findings = _sova_findings(fields.get("integrity_findings"))
    for finding in findings:
        diagnostics[finding["key"]] = finding["status"]

    # Some score templates expose each diagnostic directly within the guard object.
    for name, raw in fields.items():
        if name.endswith("_status") and name not in {"overall_status", "status", "status_description"}:
            diagnostic_name = name.removesuffix("_status")
            code = _status(raw, {1, 2, 3})
            if code is not None:
                diagnostics[diagnostic_name] = code

    if status is None and description is None and not diagnostics:
        return None
    return {"overall_status": status, "overall_description": description, "diagnostics": diagnostics, "findings": findings}


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

# Fixed UI texts, independent of AI and assessment scores.
# Diagnostic IDs 1..4 are mapped to these four controls based on the actual
# Sova score callback and its recruiter UI. Unknown IDs get neutral labels.
_DIAGNOSTIC_DESCRIPTIONS = {
    "ip_address": (
        "Kontrollen granskar ovanliga mönster med IP-adresser vid testgenomförandet. Nätverksbyten kan ha naturliga orsaker.",
        "This check looks for unusual IP address patterns during the assessments. Network changes may have innocent causes.",
    ),
    "devices_used": (
        "Kontrollen granskar ovanlig användning av flera enheter under testet. Tekniska problem eller tillgänglighetsskäl kan förklara byten.",
        "This check looks for unusual use of multiple devices. Technical or accessibility reasons may explain device changes.",
    ),
    "browser_patrolling": (
        "Kontrollen granskar upprepade eller långvariga byten mellan flikar och webbläsare under testerna.",
        "This check looks for repeated or sustained switching between tabs or browsers during assessments.",
    ),
    "question_engagement": (
        "Kontrollen granskar ihållande ovanliga svarstider och svarsmönster. En avvikelse innebär inte att någon har fuskat.",
        "This check looks for sustained unusual response times or patterns. A concern does not prove cheating.",
    ),
}
_DIAGNOSTIC_LABELS = {
    "ip": ("IP-adress", "IP address"),
    "ip_address": ("IP-adress", "IP address"),
    "devices_used": ("Använda enheter", "Devices used"),
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
        # Preserve Sova's order for the four numbered checks and attach
        # each check's real per-test statuses, without guessing missing tests.
        raw_findings = raw.get("findings")
        activity_by_key = {}
        if isinstance(raw_findings, list):
            for finding in raw_findings:
                if not isinstance(finding, dict) or not isinstance(finding.get("key"), str):
                    continue
                key = finding["key"]
                checks = []
                for activity in finding.get("activities") or []:
                    if not isinstance(activity, dict):
                        continue
                    code = _status(activity.get("status"), {1, 2, 3})
                    name = activity.get("name")
                    if code is not None and isinstance(name, str) and name.strip():
                        checks.append({"name": name.strip(), "state": _STATES[code]})
                activity_by_key[key] = checks
        order = list(dict.fromkeys(
            [f["key"] for f in raw_findings if isinstance(f, dict) and isinstance(f.get("key"), str)]
        )) if isinstance(raw_findings, list) else []
        order += [key for key in sorted(diagnostics) if key not in order]
        display_diagnostics = []
        for key in order:
            code = diagnostics.get(key)
            if code not in (1, 2, 3):
                continue
            labels = _DIAGNOSTIC_LABELS.get(key)
            if labels is None and key.startswith("diagnostic_"):
                identifier = key.removeprefix("diagnostic_")
                labels = (f"Kontroll {identifier}", f"Check {identifier}")
            if labels is None:
                labels = (key.replace("_", " ").capitalize(),) * 2
            descriptions = _DIAGNOSTIC_DESCRIPTIONS.get(key, ("", ""))
            display_diagnostics.append({
                "name_sv": labels[0],
                "name_en": labels[1],
                "description_sv": descriptions[0],
                "description_en": descriptions[1],
                "state": _STATES[code],
                "activities": activity_by_key.get(key, []),
            })
        entries.append({
            "state": state,
            "description": description,
            "diagnostics": display_diagnostics,
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
