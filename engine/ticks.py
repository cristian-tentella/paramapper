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
    target_count = max(1, target_count)

    if min_val == max_val:
        if data_type == "DATETIME":
            label = _format_datetime(min_val, 86400.0)
        else:
            label = _format_numeric(min_val, 1.0)
        return [AxisTick(fraction=0.0, label=label)]

    val_range = max_val - min_val
    nice_step = _nice_step(val_range, target_count)

    tick_min = math.ceil(min_val / nice_step) * nice_step

    ticks = []
    i = 0
    while True:
        v = tick_min + i * nice_step
        if v > max_val + nice_step * 1e-9:
            break
        fraction = max(0.0, min(1.0, (v - min_val) / val_range))
        if data_type == "DATETIME":
            label = _format_datetime(v, nice_step)
        else:
            label = _format_numeric(v, nice_step)
        ticks.append(AxisTick(fraction=fraction, label=label))
        i += 1

    return ticks


def _nice_step(val_range: float, target_count: int) -> float:
    raw_step = val_range / target_count
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude

    if normalized < 1.5:
        nice = 1.0
    elif normalized < 3.0:
        nice = 2.0
    elif normalized < 7.0:
        nice = 5.0
    else:
        nice = 10.0

    return nice * magnitude


def _format_numeric(value: float, step: float) -> str:
    if step >= 1.0:
        return str(int(round(value)))
    decimals = abs(math.floor(math.log10(step)))
    return f"{value:.{decimals}f}"


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
