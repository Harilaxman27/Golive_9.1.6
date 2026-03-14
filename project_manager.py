from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from project_model import Project, Source, Scene, SceneItem


class ProjectManager:
    def __init__(self, project_dir: Optional[Path] = None):
        # Store in the same config dir convention as config.py
        if project_dir is None:
            home = Path.home()
            project_dir = home / '.config' / 'golive_studio'
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.project_path = self.project_dir / 'project.json'
        self.project: Project = Project()

    def load(self) -> Project:
        if self.project_path.exists():
            try:
                data = json.loads(self.project_path.read_text(encoding='utf-8'))
                self.project = Project.from_dict(data if isinstance(data, dict) else {})
            except Exception:
                self.project = Project()
        else:
            self.project = Project()
        self._ensure_default_structure()
        return self.project

    def save(self) -> None:
        self.project_dir.mkdir(parents=True, exist_ok=True)
        data = self.project.to_dict()
        self.project_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def _ensure_default_structure(self) -> None:
        # Minimal default: one scene, and placeholders for your current fixed slots.
        if not self.project.scenes:
            s = Scene(id='scene_1', name='Scene 1', items=[])
            self.project.scenes.append(s)
            self.project.program_scene_id = s.id
            self.project.preview_scene_id = s.id

        # Ensure sources exist for the current fixed 1..3 slots
        existing_ids = {s.id for s in self.project.sources}
        for i in (1, 2, 3):
            sid = f'input_{i}'
            if sid not in existing_ids:
                self.project.sources.append(Source(id=sid, kind='input', name=f'Input {i}', settings={'slot': i}))
                existing_ids.add(sid)
        for i in (1, 2, 3):
            sid = f'media_{i}'
            if sid not in existing_ids:
                self.project.sources.append(Source(id=sid, kind='media', name=f'Media {i}', settings={'slot': i}))
                existing_ids.add(sid)

        # Ensure the default scene has items referencing those sources (hidden until configured)
        scene = self.project.scenes[0]
        existing_item_src = {it.source_id for it in scene.items}
        z = 0
        for s in self.project.sources:
            if s.id in existing_item_src:
                continue
            z += 1
            scene.items.append(SceneItem(id=f'item_{s.id}', source_id=s.id, z=z, visible=True, opacity=1.0))

    def set_source_name(self, source_id: str, name: str) -> None:
        for s in self.project.sources:
            if s.id == source_id:
                s.name = name
                return

    def set_source_settings(self, source_id: str, settings: Dict[str, Any]) -> None:
        for s in self.project.sources:
            if s.id == source_id:
                s.settings = dict(settings)
                return
