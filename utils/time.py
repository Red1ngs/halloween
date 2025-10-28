from datetime import datetime, timezone

def get_current_timestamp() -> int:
    """Повертає поточну позначку часу UTC у секундах."""
    return int(datetime.now(timezone.utc).timestamp())

def has_time_elapsed(start_ts: int, seconds: int) -> bool:
    """Перевіряє, чи минула задана кількість секунд з початкової позначки часу."""
    if seconds < 0:
        raise ValueError("Аргумент 'seconds' не може бути від’ємним.")
    current_ts: int = get_current_timestamp()
    elapsed: int = current_ts - start_ts
    return elapsed >= seconds