from __future__ import annotations

import re
from hashlib import sha1


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_")
    return cleaned or "item"


def stable_id(*parts: object) -> str:
    basis = "::".join(str(part) for part in parts if part is not None)
    digest = sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"xmi_{slug(str(parts[-1]) if parts else 'id')}_{digest}"
