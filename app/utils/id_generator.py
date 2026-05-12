from datetime import datetime, timezone
from uuid import uuid4


def generate_command_id(prefix: str) -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid4().hex[:8].upper()
    return f"{prefix}_{date_part}_{suffix}"
