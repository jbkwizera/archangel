"""Shared structured logging helper: consistent key=value event lines.

Produces log messages like:
    event=takenoff drone_id=0 alt=10.0

so mission logs are consistent across nodes and easy to grep or parse.
"""


def event_str(event: str, **fields) -> str:
    """Format an event and its fields as a single key=value log line.

    Floats are rendered to three decimals; everything else uses str().
    Field order is preserved as given by the caller.
    """
    parts = [f"event={event}"]
    for key, value in fields.items():
        if isinstance(value, float):
            parts.append(f"{key}={value:.3f}")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)
