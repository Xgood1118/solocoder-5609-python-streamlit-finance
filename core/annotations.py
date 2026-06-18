import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class AnnotationManager:
    def __init__(self, storage_path: str = "data/annotations.json"):
        self.storage_path = storage_path
        self.annotations: Dict[str, List[Dict]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.annotations = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.annotations = {}
        else:
            self.annotations = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.annotations, f, ensure_ascii=False, indent=2)

    def add_annotation(self, chart_id: str, content: str,
                       author: str = "匿名",
                       x_value: Optional[str] = None,
                       y_value: Optional[float] = None) -> Dict:
        if chart_id not in self.annotations:
            self.annotations[chart_id] = []

        annotation = {
            'id': f"ann_{len(self.annotations[chart_id]) + 1}_{int(datetime.now().timestamp())}",
            'content': content,
            'author': author,
            'created_at': datetime.now().isoformat(),
            'x_value': x_value,
            'y_value': y_value,
        }
        self.annotations[chart_id].append(annotation)
        self._save()
        return annotation

    def get_annotations(self, chart_id: str) -> List[Dict]:
        return self.annotations.get(chart_id, [])

    def update_annotation(self, chart_id: str, ann_id: str, content: str) -> bool:
        if chart_id not in self.annotations:
            return False
        for ann in self.annotations[chart_id]:
            if ann['id'] == ann_id:
                ann['content'] = content
                ann['updated_at'] = datetime.now().isoformat()
                self._save()
                return True
        return False

    def delete_annotation(self, chart_id: str, ann_id: str) -> bool:
        if chart_id not in self.annotations:
            return False
        original_len = len(self.annotations[chart_id])
        self.annotations[chart_id] = [
            a for a in self.annotations[chart_id] if a['id'] != ann_id
        ]
        if len(self.annotations[chart_id]) != original_len:
            self._save()
            return True
        return False

    def get_all_annotations(self) -> Dict[str, List[Dict]]:
        return self.annotations.copy()
