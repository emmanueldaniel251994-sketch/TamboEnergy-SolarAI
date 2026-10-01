from datetime import datetime, timezone


def acknowledge_alert_record(alert):
    """Move an alert from open to acknowledged."""
    if alert.status == "resolved":
        raise ValueError("Resolved alert cannot be acknowledged")

    if alert.status == "acknowledged":
        return alert

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    return alert


def resolve_alert_record(alert):
    """Move an acknowledged alert to resolved."""
    if alert.status == "resolved":
        return alert

    if alert.status != "acknowledged":
        raise ValueError(
            "Alert must be acknowledged before it can be resolved"
        )

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    return alert
