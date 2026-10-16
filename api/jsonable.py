"""
Robust JSON serializer for numeric/scientific computing outputs.

Converts NumPy types, NaN, +/-inf, and datetimes to standard JSON-safe Python primitives.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np


def to_jsonable(val: Any) -> Any:
    """Recursively convert NumPy objects, NaNs, and dates into JSON-serializable primitives."""
    if val is None:
        return None
    if isinstance(val, (bool, str)):
        return val
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, np.ndarray):
        return [to_jsonable(item) for item in val.tolist()]
    if isinstance(val, dict):
        return {str(k): to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [to_jsonable(item) for item in val]
    if hasattr(val, "model_dump"):
        return to_jsonable(val.model_dump(mode="python"))
    if hasattr(val, "to_dict"):
        return to_jsonable(val.to_dict())
    if hasattr(val, "__dict__"):
        return to_jsonable(val.__dict__)
    return str(val)
