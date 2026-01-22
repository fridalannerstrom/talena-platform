class SafeDict(dict):
    def __missing__(self, key):
        # lämna kvar placeholdern om den saknas, istället för att krascha
        return "{" + key + "}"


def render_placeholders(text: str, context: dict) -> str:
    return (text or "").format_map(SafeDict(**context))