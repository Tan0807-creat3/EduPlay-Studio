"""
Project Manager - Handles project lifecycle and file management
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from eduplay.core.path_resolver import PathResolver

class ProjectManager:
    """Manages EduPlay projects and their lifecycle"""
    
    def __init__(self):
        """Initialize project manager"""
        self.projects_dir = self._get_projects_directory()
        self.current_project = None
        self.ensure_projects_directory()
    
    def _get_projects_directory(self) -> Path:
        """Get the projects directory path"""
        try:
            projects_dir = PathResolver.resolve_projects_dir()
        except Exception:
            user_profile = os.environ.get('USERPROFILE') or os.environ.get('HOME')
            base = Path(user_profile) if user_profile else Path(os.getcwd())
            projects_dir = base / "EduPlay" / "Projects"
        return projects_dir
    
    def ensure_projects_directory(self):
        """Ensure projects directory exists"""
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_game_type(self, game_type: str) -> str:
        gt = str(game_type or "").strip().lower()
        if gt in ("quiz", "quiz_classic", "classic", "trắc nghiệm", "trac nghiem"):
            return "quiz_classic"
        if ("bắt cá" in gt) or ("bat ca" in gt) or ("câu cá" in gt) or ("cau ca" in gt) or ("fishing" in gt) or (gt == "fish"):
            return "fishing"
        if ("triệu phú" in gt) or ("trieu phu" in gt) or ("millionaire" in gt) or ("ai la trieu phu" in gt) or ("ai là triệu phú" in gt):
            return "quiz_millionaire"
        return gt or "quiz_classic"

    def _normalize_tags(self, tags: Any) -> List[str]:
        if not isinstance(tags, list):
            return []
        out: List[str] = []
        seen = set()
        for tag in tags:
            text = str(tag or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            out.append(text)
        return out
    
    def create_project(self, name: str, description: str, game_type: str) -> Dict:
        """Create a new project"""
        game_type = self._normalize_game_type(game_type)
        project_id = self._generate_project_id(name)
        project_dir = self.projects_dir / project_id
        
        # Create project directory
        project_dir.mkdir(exist_ok=True)
        
        # Create project metadata
        project_data = {
            "id": project_id,
            "name": name,
            "description": description,
            "game_type": game_type,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "tags": [],
            "questions": [],
            "game_config": self._get_default_game_config(game_type),
            "media_files": []
        }
        if game_type == "fishing":
            try:
                project_data["force_variant"] = "fishing"
                project_data["variant_marker"] = "fishing"
                cfg = dict(project_data.get("game_config") or {})
                cfg["variant_marker"] = "fishing"
                cfg["game_type"] = "Fishing Game"
                project_data["game_config"] = cfg
            except Exception:
                pass
        try:
            assets_dir = Path(__file__).parent.parent / "assets_bundle"
            defaults = [
                ("background_music", assets_dir / "sound" / "background.mp3"),
                ("correct_sound", assets_dir / "sound" / "correct.wav"),
                ("wrong_sound", assets_dir / "sound" / "wrong.wav"),
                ("click_sound", assets_dir / "sound" / "click.wav"),
                ("bg_seaweed", assets_dir / "kenney_platformer-kit" / "PNG" / "Default" / "background_seaweed_a.png"),
                ("bg_rock", assets_dir / "kenney_platformer-kit" / "PNG" / "Default" / "background_rock_a.png")
            ]
            for name, path in defaults:
                p = str(path)
                if os.path.exists(p):
                    project_data["media_files"].append({"name": name, "path": p})
        except Exception:
            pass
        
        # Save project file
        project_file = project_dir / f"{project_id}.eduplay"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        # Create media directory
        media_dir = project_dir / "media"
        media_dir.mkdir(exist_ok=True)
        
        self.current_project = project_data
        return project_data
    
    def load_project(self, project_id: str) -> Optional[Dict]:
        """Load a project by ID"""
        project_file = self.projects_dir / project_id / f"{project_id}.eduplay"
        
        if not project_file.exists():
            return None
        
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            changed = False
            try:
                qs = project_data.get("questions", [])
            except Exception:
                qs = []
            if isinstance(qs, list) and qs:
                try:
                    import uuid

                    existing = set()
                    for q in qs:
                        if not isinstance(q, dict):
                            continue
                        try:
                            qid0 = str(q.get("id") or "").strip()
                        except Exception:
                            qid0 = ""
                        if qid0:
                            if qid0 in existing:
                                qid0 = ""
                            else:
                                existing.add(qid0)
                                continue
                        if not qid0:
                            qid0 = f"q_{uuid.uuid4().hex[:10]}"
                            while qid0 in existing:
                                qid0 = f"q_{uuid.uuid4().hex[:10]}"
                            q["id"] = qid0
                            existing.add(qid0)
                            changed = True
                except Exception:
                    pass

            self.current_project = project_data
            if changed:
                try:
                    self.save_project(project_data)
                except Exception:
                    pass
            return project_data
            
        except Exception as e:
            print(f"Error loading project {project_id}: {e}")
            return None
    
    def save_project(self, project_data: Dict = None) -> bool:
        """Save current or provided project"""
        if project_data is None:
            project_data = self.current_project
        
        if project_data is None:
            return False
        
        try:
            project_id = project_data["id"]
            project_file = self.projects_dir / project_id / f"{project_id}.eduplay"
            
            # Update modified timestamp
            project_data["modified_at"] = datetime.now().isoformat()
            
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            self.current_project = project_data

            # Auto-save preview HTML into project folder (background, non-blocking)
            try:
                import copy as _copy
                import threading as _threading
                _proj_snap = _copy.deepcopy(project_data)
                _out_dir = str(self.projects_dir / project_id)
                def _save_preview():
                    try:
                        from eduplay.core.export_service import ExportService
                        _svc = ExportService()
                        _name = str(_proj_snap.get("name") or project_id)
                        # Sanitize name same way export_service does
                        _safe = ''.join([c for c in _name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_') or 'EduPlay_Game'
                        _preview_name = _safe + "_preview"
                        _svc.export_to_html(_proj_snap, _out_dir, bundle_resources=True, single_file=True, output_filename=_preview_name)
                    except Exception:
                        pass
                _t = _threading.Thread(target=_save_preview, daemon=True)
                _t.start()
            except Exception:
                pass

            return True
            
        except Exception as e:
            print(f"Error saving project: {e}")
            return False
    
    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        projects = []
        
        try:
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    project_file = project_dir / f"{project_dir.name}.eduplay"
                    
                    if project_file.exists():
                        try:
                            with open(project_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                            
                            # Add file metadata
                            stat = project_file.stat()
                            project_data["file_size"] = stat.st_size
                            project_data["file_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                            
                            projects.append(project_data)
                            
                        except Exception as e:
                            print(f"Error reading project {project_dir.name}: {e}")
                            continue
            
            # Sort by modification date (newest first)
            projects.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            
        except Exception as e:
            print(f"Error scanning projects directory: {e}")
        
        return projects

    def get_all_project_tags(self, projects: Optional[List[Dict]] = None) -> List[str]:
        source = projects if isinstance(projects, list) else self.get_all_projects()
        seen = set()
        out: List[str] = []
        for project in source:
            if not isinstance(project, dict):
                continue
            for tag in self._normalize_tags(project.get("tags")):
                lowered = tag.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                out.append(tag)
        out.sort(key=lambda item: item.lower())
        return out

    def filter_projects(
        self,
        projects: List[Dict],
        search_text: str = "",
        template_filter: str = "all",
        tag_filter: str = "all",
        recent_only: bool = False,
        recent_project_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        items = [p for p in (projects or []) if isinstance(p, dict)]
        query = str(search_text or "").strip().lower()
        wanted_template = str(template_filter or "all").strip().lower()
        wanted_tag = str(tag_filter or "all").strip().lower()
        recent_ids = [str(pid or "").strip() for pid in (recent_project_ids or []) if str(pid or "").strip()]
        recent_set = set(recent_ids)

        filtered: List[Dict] = []
        for project in items:
            if recent_only and str(project.get("id") or "").strip() not in recent_set:
                continue

            project_tags = self._normalize_tags(project.get("tags"))
            project["tags"] = project_tags

            if query:
                haystack = " ".join(
                    [
                        str(project.get("name") or ""),
                        str(project.get("description") or ""),
                        str(project.get("game_type") or ""),
                        " ".join(project_tags),
                    ]
                ).lower()
                if query not in haystack:
                    continue

            if wanted_template not in ("", "all"):
                project_game_type = self._normalize_game_type(project.get("game_type", "quiz_classic"))
                if project_game_type != self._normalize_game_type(wanted_template):
                    continue

            if wanted_tag not in ("", "all"):
                lowered_tags = {tag.lower() for tag in project_tags}
                if wanted_tag not in lowered_tags:
                    continue

            filtered.append(project)

        if recent_only and recent_ids:
            order = {pid: index for index, pid in enumerate(recent_ids)}
            filtered.sort(key=lambda project: order.get(str(project.get("id") or "").strip(), len(order)))
        return filtered

    def update_project_tags(self, project_id: str, tags: List[Any]) -> Optional[Dict]:
        project = self.load_project(project_id)
        if not isinstance(project, dict):
            return None
        project["tags"] = self._normalize_tags(tags)
        ok = self.save_project(project)
        return project if ok else None
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            project_dir = self.projects_dir / project_id
            
            if project_dir.exists():
                shutil.rmtree(project_dir)
                
                if self.current_project and self.current_project.get("id") == project_id:
                    self.current_project = None
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting project {project_id}: {e}")
            return False

    def duplicate_project(self, project_id: str) -> Optional[Dict]:
        try:
            src = self.load_project(project_id)
            if not isinstance(src, dict):
                return None
        except Exception:
            return None

        try:
            import copy
            import uuid

            out = copy.deepcopy(src)
            src_name = str(out.get("name") or project_id).strip() or project_id
            out["name"] = f"{src_name} (Copy)"
            new_id = self._generate_project_id(out["name"])
            out["id"] = new_id
            out["created_at"] = datetime.now().isoformat()
            out["modified_at"] = datetime.now().isoformat()

            tags = out.get("tags", [])
            if not isinstance(tags, list):
                out["tags"] = []
            else:
                out["tags"] = [str(t).strip() for t in tags if str(t or "").strip()]

            qs = out.get("questions", [])
            if not isinstance(qs, list):
                qs = []
            existing = set()
            new_qs = []
            for q in qs:
                if not isinstance(q, dict):
                    continue
                q2 = copy.deepcopy(q)
                qid = f"q_{uuid.uuid4().hex[:10]}"
                while qid in existing:
                    qid = f"q_{uuid.uuid4().hex[:10]}"
                q2["id"] = qid
                existing.add(qid)
                new_qs.append(q2)
            out["questions"] = new_qs

            proj_dir = self.projects_dir / new_id
            proj_dir.mkdir(parents=True, exist_ok=True)
            proj_file = proj_dir / f"{new_id}.eduplay"
            with open(proj_file, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)

            try:
                media_dir = proj_dir / "media"
                media_dir.mkdir(exist_ok=True)
            except Exception:
                pass

            return out
        except Exception:
            return None
    
    def add_question(self, question_data: Dict) -> bool:
        """Add a question to current project"""
        if not self.current_project:
            return False
        
        try:
            if "questions" not in self.current_project:
                self.current_project["questions"] = []

            questions = self.current_project.get("questions", []) or []
            existing_ids = set()
            try:
                for q in questions:
                    if isinstance(q, dict):
                        qid = str(q.get("id") or "").strip()
                        if qid:
                            existing_ids.add(qid)
            except Exception:
                existing_ids = set()

            qid = ""
            try:
                qid = str(question_data.get("id") or "").strip()
            except Exception:
                qid = ""

            if not qid or qid in existing_ids:
                import uuid

                qid = f"q_{uuid.uuid4().hex[:10]}"
                while qid in existing_ids:
                    qid = f"q_{uuid.uuid4().hex[:10]}"
                question_data["id"] = qid

            self.current_project["questions"].append(question_data)
            return self.save_project()
            
        except Exception as e:
            print(f"Error adding question: {e}")
            return False
    
    def update_question(self, question_id: str, question_data: Dict) -> bool:
        """Update a question in current project"""
        if not self.current_project:
            return False
        
        try:
            questions = self.current_project.get("questions", [])
            
            for i, question in enumerate(questions):
                if question.get("id") == question_id:
                    # Preserve ID
                    question_data["id"] = question_id
                    questions[i] = question_data
                    break
            
            return self.save_project()
            
        except Exception as e:
            print(f"Error updating question {question_id}: {e}")
            return False
    
    def delete_question(self, question_id: str) -> bool:
        """Delete a question from current project"""
        if not self.current_project:
            return False
        
        try:
            questions = self.current_project.get("questions", [])
            self.current_project["questions"] = [
                q for q in questions if q.get("id") != question_id
            ]
            
            return self.save_project()
            
        except Exception as e:
            print(f"Error deleting question {question_id}: {e}")
            return False

    def duplicate_question(self, question_id: str) -> str:
        if not self.current_project:
            return ""
        try:
            questions = self.current_project.get("questions", []) or []
        except Exception:
            questions = []
        if not isinstance(questions, list) or not question_id:
            return ""

        try:
            import copy
            import uuid

            idx = -1
            src = None
            for i, q in enumerate(questions):
                if isinstance(q, dict) and str(q.get("id") or "") == str(question_id):
                    idx = i
                    src = q
                    break
            if idx < 0 or not isinstance(src, dict):
                return ""

            existing = set()
            for q in questions:
                if isinstance(q, dict):
                    qid = str(q.get("id") or "").strip()
                    if qid:
                        existing.add(qid)
            new_id = f"q_{uuid.uuid4().hex[:10]}"
            while new_id in existing:
                new_id = f"q_{uuid.uuid4().hex[:10]}"

            dup = copy.deepcopy(src)
            dup["id"] = new_id
            questions.insert(idx + 1, dup)
            self.current_project["questions"] = questions
            ok = self.save_project(self.current_project)
            return new_id if ok else ""
        except Exception:
            return ""
    
    def add_media_file(self, file_path: str, file_name: str) -> Optional[str]:
        """Add a media file to current project"""
        if not self.current_project:
            return None
        
        try:
            project_id = self.current_project["id"]
            project_dir = self.projects_dir / project_id
            media_dir = project_dir / "media"
            
            # Copy file to project media directory
            dest_path = media_dir / file_name
            shutil.copy2(file_path, dest_path)
            
            # Add to project metadata
            if "media_files" not in self.current_project:
                self.current_project["media_files"] = []
            
            media_info = {
                "name": file_name,
                "path": str(dest_path.relative_to(project_dir)),
                "type": self._get_file_type(file_name),
                "added_at": datetime.now().isoformat()
            }
            
            self.current_project["media_files"].append(media_info)
            self.save_project()
            
            return str(dest_path)
            
        except Exception as e:
            print(f"Error adding media file: {e}")
            return None
    
    def update_game_config(self, config: Dict) -> bool:
        """Update game configuration"""
        if not self.current_project:
            return False
        
        try:
            self.current_project["game_config"] = config
            return self.save_project()
            
        except Exception as e:
            print(f"Error updating game config: {e}")
            return False
    
    def get_current_project(self) -> Optional[Dict]:
        """Get current project"""
        return self.current_project
    
    def set_current_project(self, project_data: Dict):
        """Set current project"""
        self.current_project = project_data
    
    def _generate_project_id(self, name: str) -> str:
        """Generate unique project ID"""
        import uuid
        safe_name = "".join(c for c in name if c.isalnum() or c in "_- ").replace(" ", "_")
        return f"{safe_name}_{uuid.uuid4().hex[:8]}"
    
    def _get_default_game_config(self, game_type: str) -> Dict:
        """Get default game configuration"""
        if game_type == "fishing":
            return {
                "background_music": "assets/sound/background.mp3",
                "correct_sound": "assets/sound/correct.wav",
                "wrong_sound": "assets/sound/wrong.wav",
                "fish_objects": [
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_blue.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_blue_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"},
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_green.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_green_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"},
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_orange.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_orange_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"}
                ],
                "speed": 5,
                "score_per_fish": 10,
                "time_limit": 60
            }
        else:  # quiz_classic
            return {
                "background_music": "assets/sound/background.mp3",
                "correct_sound": "assets/sound/correct.wav",
                "wrong_sound": "assets/sound/wrong.wav",
                "time_per_question": 30,
                "show_explanation": True,
                "randomize_questions": True
            }
    
    def _get_file_type(self, file_name: str) -> str:
        """Get file type based on extension"""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        image_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']
        audio_exts = ['mp3', 'wav', 'ogg', 'm4a']
        video_exts = ['mp4', 'avi', 'mov', 'wmv', 'flv']
        
        if ext in image_exts:
            return "image"
        elif ext in audio_exts:
            return "audio"
        elif ext in video_exts:
            return "video"
        else:
            return "other"
"""
Nguyen-Thanh-Tan ¬_¬
"""
