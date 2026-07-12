from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkProfile:
    name: str
    date: str = ""
    media: str = ""
    page: str = "001"
    rule: str = "{DATE}_{MEDIA}_{PAGE}"
    recursive: bool = False


def load_profiles(path: Path) -> dict[str, WorkProfile]:
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    profiles: dict[str, WorkProfile] = {}
    for name, values in data.items():
        if isinstance(values, dict):
            profiles[name] = WorkProfile(name=name, **{key: value for key, value in values.items() if key != "name"})
    return profiles


def save_profile(path: Path, profile: WorkProfile) -> None:
    profiles = load_profiles(path)
    profiles[profile.name] = profile
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {name: asdict(saved_profile) for name, saved_profile in sorted(profiles.items())}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
