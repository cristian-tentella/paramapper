import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AxisTick:
    fraction: float
    label: str


def generate_ticks(
    min_val: float,
    max_val: float,
    target_count: int = 5,
    data_type: str = "NUMERIC",
) -> list[AxisTick]:
    count = max(2, target_count)

    if min_val == max_val:
        if data_type == "DATETIME":
            label = _format_datetime(min_val, 86400.0)
        else:
            label = _format_numeric(min_val, 1.0)
        return [AxisTick(fraction=0.0, label=label)]

    val_range = max_val - min_val
    step = val_range / (count - 1)

    ticks = []
    for k in range(count):
        fraction = k / (count - 1)
        value = min_val + fraction * val_range
        if data_type == "DATETIME":
            label = _format_datetime(value, step)
        else:
            label = _format_numeric(value, step)
        ticks.append(AxisTick(fraction=fraction, label=label))

    return ticks


def _format_numeric(value: float, step: float) -> str:
    return f"{value:.{_decimals_for_step(step)}f}"


def _decimals_for_step(step: float) -> int:
    if step <= 0:
        return 0
    if abs(step - round(step)) < 1e-9 * max(1.0, abs(step)):
        return 0
    exponent = math.floor(math.log10(step))
    return max(0, 1 - exponent)


def _format_datetime(epoch: float, step_seconds: float) -> str:
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)

    if step_seconds >= 365 * 86400:
        return dt.strftime("%Y")
    elif step_seconds >= 28 * 86400:
        return dt.strftime("%b %Y")
    elif step_seconds >= 86400:
        return dt.strftime("%b %d")
    elif step_seconds >= 3600:
        return dt.strftime("%H:%M")
    else:
        return dt.strftime("%H:%M:%S")
