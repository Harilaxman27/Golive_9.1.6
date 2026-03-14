from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Source:
    id: str
    kind: str  # 'input' | 'media' | 'image' | 'text' | ...
    name: str
    settings: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class SceneItem:
    id: str
    source_id: str
    z: int = 0
    visible: bool = True
    opacity: float = 1.0
    transform: Dict[str, Any] = field(default_factory=dict)
    audio: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    id: str
    name: str
    items: List[SceneItem] = field(default_factory=list)


@dataclass
class Project:
    version: int = 1
    sources: List[Source] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    program_scene_id: Optional[str] = None
    preview_scene_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Project":
        p = Project(version=int(data.get('version', 1) or 1))
        for s in data.get('sources', []) or []:
            try:
                p.sources.append(Source(**s))
            except Exception:
                # tolerate older/partial entries
                p.sources.append(Source(
                    id=str(s.get('id')),
                    kind=str(s.get('kind', 'unknown')),
                    name=str(s.get('name', 'Source')),
                    settings=dict(s.get('settings', {}) or {}),
                    enabled=bool(s.get('enabled', True)),
                ))
        for sc in data.get('scenes', []) or []:
            items: List[SceneItem] = []
            for it in sc.get('items', []) or []:
                try:
                    items.append(SceneItem(**it))
                except Exception:
                    items.append(SceneItem(
                        id=str(it.get('id')),
                        source_id=str(it.get('source_id')),
                        z=int(it.get('z', 0) or 0),
                        visible=bool(it.get('visible', True)),
                        opacity=float(it.get('opacity', 1.0) or 1.0),
                        transform=dict(it.get('transform', {}) or {}),
                        audio=dict(it.get('audio', {}) or {}),
                    ))
            p.scenes.append(Scene(
                id=str(sc.get('id')),
                name=str(sc.get('name', 'Scene')),
                items=items,
            ))
        p.program_scene_id = data.get('program_scene_id')
        p.preview_scene_id = data.get('preview_scene_id')
        return p
