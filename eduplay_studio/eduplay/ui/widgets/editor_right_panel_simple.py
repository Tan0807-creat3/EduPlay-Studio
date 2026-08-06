from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QGroupBox)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
from eduplay.core.export_service import ExportService
from eduplay.core.settings_manager import SettingsManager
from eduplay.core.i18n import I18n


class EditorRightPanel(QWidget):
    preview_requested = Signal()
    export_html_requested = Signal()
    export_native_requested = Signal()
    export_exe_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self.current_question = None
        self._last_html = None
        self._load_base_url = None
        self._refresh_in_progress = False
        self._refresh_pending = False
        try:
            from PySide6.QtCore import QTimer
            self._refresh_timer = QTimer(self)
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.timeout.connect(self._do_refresh_preview)
        except Exception:
            self._refresh_timer = None
        try:
            self.language = SettingsManager().get_language()
        except Exception:
            self.language = 'en'
        try:
            self._zoom_mode = 'auto'
        except Exception:
            self._zoom_mode = 'auto'
        try:
            self._preview_portrait = True
        except Exception:
            self._preview_portrait = True
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (hidden)
        header = self.create_header()
        try:
            header.setVisible(False)
        except Exception:
            pass
        layout.addWidget(header)
        
        # Preview area
        self.preview_area = self.create_preview_area()
        layout.addWidget(self.preview_area, 1)
        
        # Control buttons (hidden)
        controls = self.create_control_buttons()
        try:
            controls.setVisible(False)
        except Exception:
            pass
            
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme()
            self.apply_theme(theme)
        except Exception:
            pass
        
    def create_header(self):
        header = QWidget()
        self.header = header
        header.setStyleSheet("""
            QWidget {
                background-color: #25252B;
                border-bottom: 1px solid #3A3A40;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        title = QLabel(I18n.t('editor.live_preview', self.language))
        self.title_label = title
        title.setStyleSheet("""
            QLabel {
                color: #E0E0E0;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton(I18n.t('editor.refresh', self.language))
        self.refresh_btn = refresh_btn
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6A48C0;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_preview)
        try:
            refresh_btn.setVisible(False)
        except Exception:
            pass
        layout.addWidget(refresh_btn)
        try:
            self._zoom_btn = QPushButton("100%")
            self._zoom_btn.setStyleSheet(
                """
                QPushButton { background-color: #3A3A40; color: #E0E0E0; border: 1px solid #4A4A50; padding: 4px 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #4A4A50; }
                """
            )
            def _cycle_mode():
                order = ['auto','fit_width','fit_height','actual']
                try:
                    i = order.index(getattr(self, '_zoom_mode', 'auto'))
                except Exception:
                    i = 0
                m = order[(i+1)%len(order)]
                self._zoom_mode = m
                try:
                    self._update_zoom()
                except Exception:
                    pass
                try:
                    self._update_zoom_btn_label()
                except Exception:
                    pass
            self._update_zoom_btn_label()
            self._zoom_btn.clicked.connect(_cycle_mode)
            layout.addWidget(self._zoom_btn)
            try:
                self._zoom_btn.setVisible(False)
            except Exception:
                pass
        except Exception:
            pass
        
        return header
        
    def apply_theme(self, theme: str):
        """Apply theme to the panel"""
        self.theme = 'dark' if str(theme).lower() == 'dark' else 'light'
        t = self.theme
        
        if t == 'dark':
            header_bg = "#25252B"
            header_border = "#3A3A40"
            text_color = "#E0E0E0"
            panel_bg = "#1E1E24"
            panel_border = "#3A3A40"
            web_bg = "#25252B"
            web_border = "#3A3A40"
            status_color = "#888888"
            controls_bg = "#25252B"
            controls_border = "#3A3A40"
            zoom_bg = "#3A3A40"
            zoom_fg = "#E0E0E0"
            zoom_border = "#4A4A50"
            zoom_hover = "#4A4A50"
        else:
            header_bg = "#FFFFFF"
            header_border = "#E2E8F0"
            text_color = "#1A1A1A"
            panel_bg = "#FFFFFF"
            panel_border = "#E2E8F0"
            web_bg = "#F9FAFF"
            web_border = "#CBD5E1"
            status_color = "#667085"
            controls_bg = "#F9FAFF"
            controls_border = "#E2E8F0"
            zoom_bg = "#FFFFFF"
            zoom_fg = "#1A1A1A"
            zoom_border = "#CBD5E1"
            zoom_hover = "#F1F5F9"
            
        if hasattr(self, 'header'):
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {header_bg};
                    border-bottom: 1px solid {header_border};
                    padding: 10px;
                }}
            """)
            
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    color: {text_color};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
            
        if hasattr(self, 'preview_area'):
             self.preview_area.setStyleSheet(f"""
                QWidget {{
                    background-color: {panel_bg};
                    border: 1px solid {panel_border};
                    border-radius: 6px;
                    margin: 10px;
                }}
            """)
            
        if hasattr(self, 'web_view'):
            self.web_view.setStyleSheet(f"""
                QWebEngineView {{
                    background-color: {web_bg};
                    border: 1px solid {web_border};
                    border-radius: 4px;
                }}
            """)
            
        if hasattr(self, 'preview_status'):
            self.preview_status.setStyleSheet(f"""
                QLabel {{
                    color: {status_color};
                    font-size: 12px;
                    padding: 6px 8px;
                }}
            """)

        if hasattr(self, '_zoom_btn'):
             self._zoom_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {zoom_bg}; color: {zoom_fg}; border: 1px solid {zoom_border}; padding: 4px 8px; border-radius: 4px; }}
                QPushButton:hover {{ background-color: {zoom_hover}; }}
             """)
        
    def create_preview_area(self):
        preview = QWidget()
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        if theme == 'dark':
            panel_bg = "#1E1E24"
            panel_border = "#3A3A40"
            web_bg = "#25252B"
            web_border = "#3A3A40"
            status_color = "#888888"
        else:
            panel_bg = "#FFFFFF"
            panel_border = "#E2E8F0"
            web_bg = "#F9FAFF"
            web_border = "#CBD5E1"
            status_color = "#667085"
        preview.setStyleSheet(
            f"""
            QWidget {{
                background-color: {panel_bg};
                border: 1px solid {panel_border};
                border-radius: 6px;
                margin: 10px;
            }}
        """
        )
        
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet(
            f"""
            QWebEngineView {{
                background-color: {web_bg};
                border: 1px solid {web_border};
                border-radius: 4px;
            }}
        """
        )
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineSettings
            s = self.web_view.settings()
            s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
            s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
            s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
            s.setAttribute(QWebEngineSettings.Accelerated2DCanvasEnabled, True)
            try:
                self.web_view.page().setAudioMuted(False)
            except Exception:
                pass
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QSizePolicy
            self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        layout.addWidget(self.web_view)
        try:
            self.web_view.loadFinished.connect(self._on_web_load_finished)
        except Exception:
            pass
        
        # Status label
        self.preview_status = QLabel(I18n.t('editor.preview_ready', self.language))
        self.preview_status.setStyleSheet(
            f"""
            QLabel {{
                color: {status_color};
                font-size: 12px;
                padding: 6px 8px;
            }}
        """
        )
        layout.addWidget(self.preview_status)
        try:
            self.preview_status.setVisible(False)
        except Exception:
            pass
        
        return preview
        
    def create_control_buttons(self):
        controls = QWidget()
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        if theme == 'dark':
            controls_bg = "#25252B"
            controls_border = "#3A3A40"
        else:
            controls_bg = "#F9FAFF"
            controls_border = "#E2E8F0"
        controls.setStyleSheet(
            f"""
            QWidget {{
                background-color: {controls_bg};
                border-top: 1px solid {controls_border};
                padding: 10px;
            }}
        """
        )
        
        layout = QHBoxLayout(controls)
        
        # Default export button
        lang = SettingsManager().get_language()
        fmt = 'html'
        label_map = {
            'html': I18n.t('editor.export_html', lang),
            'python': I18n.t('editor.export_native', lang),
            'exe': I18n.t('editor.export_exe', lang)
        }
        self.export_default_btn = QPushButton(label_map.get(fmt, I18n.t('editor.export_html', lang)))
        self.export_default_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #6A48C0;
            }
        """)
        def _do_default_export():
            try:
                f = 'html'
                if self.current_project:
                    cfg = self.current_project.get('game_config', {})
                    proj_fmt = (self.current_project.get('export_default_format') or cfg.get('export_default_format'))
                    if proj_fmt:
                        f = proj_fmt
            except Exception:
                f = 'html'
            if f == 'html':
                self.export_html()
            elif f == 'python':
                self.export_native()
            elif f == 'exe':
                self.export_exe()
            else:
                self.export_html()
        self.export_default_btn.clicked.connect(_do_default_export)
        layout.addWidget(self.export_default_btn)
        
        # Spacer
        layout.addStretch()
        
        # Test game button
        lang = SettingsManager().get_language()
        self.test_btn = QPushButton(I18n.t('editor.test_game', lang))
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #12B76A;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0F9C5A;
            }
        """)
        self.test_btn.clicked.connect(self.test_game)
        layout.addWidget(self.test_btn)
        
        layout.addStretch()
        
        # Export buttons
        self.export_html_btn = QPushButton(I18n.t('editor.export_html', lang))
        self.export_html_btn.setStyleSheet("""
            QPushButton {
                background-color: #F79009;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E68008;
            }
        """)
        self.export_html_btn.clicked.connect(self.export_html)
        layout.addWidget(self.export_html_btn)
        
        self.export_native_btn = QPushButton(I18n.t('editor.export_native', lang))
        self.export_native_btn.setStyleSheet("""
            QPushButton {
                background-color: #F79009;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E68008;
            }
        """)
        self.export_native_btn.clicked.connect(self.export_native)
        layout.addWidget(self.export_native_btn)

        self.export_exe_btn = QPushButton(I18n.t('editor.export_exe', lang))
        self.export_exe_btn.setStyleSheet("""
            QPushButton {
                background-color: #F79009;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E68008;
            }
        """)
        self.export_exe_btn.clicked.connect(self.export_exe)
        layout.addWidget(self.export_exe_btn)
        
        return controls
        
    def set_project(self, project):
        """Set the current project for preview"""
        self.current_project = project
        try:
            fmt = 'html'
            cfg = (self.current_project or {}).get('game_config', {})
            proj_fmt = (self.current_project or {}).get('export_default_format') or cfg.get('export_default_format')
            if proj_fmt:
                fmt = proj_fmt
            lang = SettingsManager().get_language()
            label_map = {
                'html': I18n.t('editor.export_html', lang),
                'python': I18n.t('editor.export_native', lang),
                'exe': I18n.t('editor.export_exe', lang)
            }
            if hasattr(self, 'export_default_btn') and self.export_default_btn:
                self.export_default_btn.setText(label_map.get(fmt, I18n.t('editor.export_html', lang)))
        except Exception:
            pass
        self._schedule_refresh_preview()
        
    def set_question(self, question):
        """Set the current question for preview"""
        self.current_question = question
        self._schedule_refresh_preview()

    def _schedule_refresh_preview(self):
        try:
            self._refresh_pending = True
            if self._refresh_timer:
                self._refresh_timer.start(400)
            else:
                self._do_refresh_preview()
        except Exception:
            self._do_refresh_preview()

    def _do_refresh_preview(self):
        if self._refresh_in_progress:
            return
        self._refresh_in_progress = True
        self._refresh_pending = False
        try:
            self.refresh_preview()
        finally:
            self._refresh_in_progress = False
        
    def refresh_preview(self):
        if not self.current_project:
            self.web_view.setHtml("<html><body style='background:#1E1E24;color:#E0E0E0;padding:20px;'>No project loaded for preview.</body></html>")
            self.preview_status.setText(I18n.t('editor.no_project', self.language))
            return
        try:
            import importlib
            import eduplay.core.export_service as _es
            try:
                importlib.reload(_es)
            except Exception:
                pass
            svc = ExportService()
            bundled = svc._bundle_media_files(self.current_project or {})
            bundled['language'] = self.language or 'en'
            try:
                if not bundled.get('game_type'):
                    project_gt = (self.current_project or {}).get('game_type') or 'quiz_classic'
                    bundled['game_type'] = project_gt
            except Exception:
                if not bundled.get('game_type'):
                    bundled['game_type'] = 'quiz_classic'
            html = svc._generate_html_content(bundled)
            try:
                base_dir = svc.assets_dir
                # Use millionaire/altp_vn subfolder as base when previewing variants that rely on relative asset paths
                try:
                    fv = (bundled.get('force_variant') or '').lower()
                    if fv in ('millionaire','wwbm'):
                        base_dir = base_dir / 'millionaire'
                    elif fv == 'altp_vn':
                        base_dir = base_dir / 'altp_vn'
                    else:
                        # Content-based detection when force_variant not set
                        h = html or ''
                        if ('images/Logo.png' in h) or ('js/app.js' in h) or ('Who Wants to Be a Millionaire' in h):
                            base_dir = base_dir / 'millionaire'
                        elif ('altp_vn/' in h) or ('Ai là triệu phú' in h and 'altp_vn' in h):
                            base_dir = base_dir / 'altp_vn'
                except Exception:
                    pass
                base_url = QUrl.fromLocalFile(str(base_dir))
                self._last_html = html
                self._load_base_url = base_url
                self.web_view.setHtml(html, base_url)
            except Exception:
                self._last_html = html
                self._load_base_url = None
                self.web_view.setHtml(html)
            try:
                if not html or len(html) < 100 or ("id=\"game-data\"" not in html and 'game_type' not in html):
                    diag = f"<html><body style='background:#1E1E24;color:#E0E0E0;padding:20px;'><h3>Preview Diagnostic</h3><p>HTML trống hoặc không hợp lệ.</p><pre>game_type={repr(bundled.get('game_type'))}; questions={len(bundled.get('questions', []))}</pre></body></html>"
                    self.web_view.setHtml(diag)
            except Exception:
                pass
            self.preview_status.setText(I18n.t('editor.preview_updated', self.language))
            try:
                self._update_zoom()
            except Exception:
                pass
            try:
                self._apply_no_scrollbars()
            except Exception:
                pass
        except Exception as e:
            err = f"<html><body style='background:#1E1E24;color:#E0E0E0;padding:20px;'>Preview error: {str(e)}</body></html>"
            self.web_view.setHtml(err)
            self.preview_status.setText(I18n.t('editor.preview_failed', self.language))

    def _on_web_load_finished(self, ok: bool):
        try:
            if ok:
                self.preview_status.setText(I18n.t('editor.preview_updated', self.language))
                try:
                    self._apply_no_scrollbars()
                except Exception:
                    pass
            else:
                # Fallback: write HTML to a temp file and load via file:// URL
                import tempfile, os
                from pathlib import Path
                tmpdir = tempfile.gettempdir()
                fp = Path(tmpdir) / "eduplay_preview_fishing.html"
                try:
                    content = self._last_html or "<html><body>Empty</body></html>"
                    try:
                        from PySide6.QtCore import QUrl
                        if self._load_base_url and hasattr(self._load_base_url, 'toString'):
                            base = self._load_base_url.toString()
                            if '<head>' in content:
                                content = content.replace('<head>', f'<head><base href="{base}">')
                            elif '</head>' in content:
                                content = content.replace('</head>', f'<base href="{base}"></head>')
                    except Exception:
                        pass
                    with open(fp, 'w', encoding='utf-8') as f:
                        f.write(content)
                    from PySide6.QtCore import QUrl
                    self.web_view.setUrl(QUrl.fromLocalFile(str(fp)))
                    self.preview_status.setText("Reload via file URL")
                    try:
                        self._apply_no_scrollbars()
                    except Exception:
                        pass
                except Exception:
                    diag = "<html><body style='background:#1E1E24;color:#E0E0E0;padding:20px;'>Tải HTML thất bại. Kiểm tra quyền WebEngine và assets.</body></html>"
                    self.web_view.setHtml(diag)
        except Exception:
            pass
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            h = max(30, min(56, int(self.height()*0.045)))
            for btn in [self.export_default_btn, self.test_btn, self.export_html_btn, self.export_native_btn, self.export_exe_btn]:
                if btn:
                    btn.setFixedHeight(h)
            try:
                self._update_zoom()
            except Exception:
                pass
        except Exception:
            pass
            
    def generate_preview(self):
        """Generate preview content based on current project/question"""
        if not self.current_project:
            return "No project data available for preview."
            
        # Get game configuration
        game_config = self.current_project.get('game_config', {})
        project_gt = self.current_project.get('game_type', None)
        game_type = project_gt if project_gt else game_config.get('game_type', 'Quiz Classic')
        difficulty = game_config.get('difficulty', 'Medium')
        
        # Get questions
        questions = self.current_project.get('questions', [])
        
        preview = []
        preview.append("=" * 50)
        preview.append(f"GAME PREVIEW: {game_type.upper()}")
        preview.append("=" * 50)
        preview.append("")
        preview.append(f"Difficulty: {difficulty}")
        preview.append(f"Total Questions: {len(questions)}")
        preview.append(f"Question Time: {game_config.get('question_time', 30)} seconds")
        auto_points = bool(game_config.get('auto_points_enabled', False))
        if auto_points:
            total_points = 10
            q_count = len(questions)
            if q_count > 0:
                try:
                    per_q = int(round(total_points / q_count))
                except Exception:
                    per_q = total_points // q_count if q_count > 0 else 0
            else:
                per_q = 0
            preview.append(f"Points per Question (auto from {total_points}): {per_q}")
        else:
            preview.append(f"Points per Question: {game_config.get('points_per_question', 10)}")
        preview.append("")
        
        if self.current_question:
            preview.append("CURRENT QUESTION PREVIEW:")
            preview.append("-" * 30)
            preview.append("")
            preview.append(f"Type: {self.current_question.get('type', 'unknown').replace('_', ' ').title()}")
            preview.append(f"Question: {self.current_question.get('question', 'No question text')}")
            
            q_type = self.current_question.get('type', 'multiple_choice')
            
            if q_type == 'multiple_choice':
                options = self.current_question.get('options', [])
                correct = self.current_question.get('correct_answer', 0)
                preview.append("")
                preview.append("Options:")
                for i, option in enumerate(options):
                    marker = "✓" if i == correct else "○"
                    preview.append(f"  {marker} {option}")
                    
            elif q_type == 'true_false':
                correct = self.current_question.get('correct_answer', True)
                preview.append(f"Correct Answer: {'True' if correct else 'False'}")
                
            elif q_type == 'fill_blank':
                answers = self.current_question.get('correct_answers', [])
                case_sensitive = self.current_question.get('case_sensitive', False)
                preview.append(f"Acceptable Answers: {', '.join(answers)}")
                preview.append(f"Case Sensitive: {'Yes' if case_sensitive else 'No'}")
                
            elif q_type == 'matching':
                pairs = self.current_question.get('pairs', [])
                preview.append("")
                preview.append("Matching Pairs:")
                for pair in pairs:
                    preview.append(f"  {pair['left']} → {pair['right']}")
                    
            elif q_type == 'short_answer':
                expected = self.current_question.get('expected_answer', '')
                keywords = self.current_question.get('keywords', [])
                preview.append(f"Expected Answer: {expected}")
                if keywords:
                    preview.append(f"Keywords: {', '.join(keywords)}")
                    
            elif q_type == 'essay':
                max_points = self.current_question.get('max_points', 10)
                preview.append(f"Maximum Points: {max_points}")
                
            explanation = self.current_question.get('explanation', '')
            if explanation:
                preview.append("")
                preview.append(f"Explanation: {explanation}")
                
        else:
            preview.append("No question selected for preview.")
            
        preview.append("")
        preview.append("=" * 50)
        
        # Add sample game flow for the selected game type
        if game_type in ["Quiz Classic", "quiz_classic"]:
            preview.append("SAMPLE GAME FLOW:")
            preview.append("1. Question appears with multiple choice options")
            preview.append("2. Player selects an answer")
            preview.append("3. Immediate feedback shows if correct")
            preview.append("4. Score is updated")
            preview.append("5. Next question loads")
            
        elif game_type in ["Fishing Game", "fishing"]:
            preview.append("SAMPLE GAME FLOW:")
            preview.append("1. Question appears at top of screen")
            preview.append("2. Fish with answers swim across screen")
            preview.append("3. Player clicks on fish with correct answer")
            preview.append("4. Correct fish is caught, wrong ones swim away")
            preview.append("5. Score and timer update")
        elif game_type in ["Millionaire", "quiz_millionaire", "millionaire"]:
            preview.append("SAMPLE GAME FLOW:")
            preview.append("1. Multiple choice question appears")
            preview.append("2. Player can use lifelines (50:50, Phone, Audience)")
            preview.append("3. Player selects an answer, feedback displayed")
            preview.append("4. Score increases by points per question")
            preview.append("5. Next question loads until completion")
        elif game_type in ["Ai là triệu phú", "quiz_millionaire", "Millionaire"]:
            preview.append("SAMPLE GAME FLOW:")
            preview.append("1. Hiển thị 1 câu hỏi với 4 lựa chọn")
            preview.append("2. Có cứu trợ 50:50 để loại 2 phương án sai")
            preview.append("3. Người chơi chọn đáp án, hệ thống đánh dấu đúng/sai")
            preview.append("4. Cộng điểm theo bậc, tiếp tục câu kế tiếp")
            
        preview.append("=" * 50)
        
        return "\n".join(preview)
        
    def test_game(self):
        if not self.current_project:
            self.preview_status.setText(I18n.t('editor.no_project', SettingsManager().get_language()))
            return
        self.refresh_preview()

    def export_html(self):
        """Trigger HTML export"""
        self.export_html_requested.emit()
        try:
            gt = (self.current_project or {}).get('game_type', '')
            if str(gt).lower() == 'fishing':
                self.preview_status.setText("HTML export requested (Fishing)")
            else:
                self.preview_status.setText("HTML export requested")
        except Exception:
            self.preview_status.setText("HTML export requested")
        
    def export_native(self):
        """Trigger native export"""
        self.export_native_requested.emit()
        self.preview_status.setText("Native export requested")

    def export_exe(self):
        self.export_exe_requested.emit()
        self.preview_status.setText("Executable export requested")

    def _update_zoom(self):
        try:
            view_w = max(1, int(self.web_view.width()))
            view_h = max(1, int(self.web_view.height()))

            def _fallback():
                try:
                    base = 800
                    factor = max(0.6, min(2.0, view_w/float(base)))
                    self.web_view.setZoomFactor(factor)
                except Exception:
                    pass

            js = """
                (function(){
                    var didAuto = false;
                    try{
                        if (window.__setManualZoom) window.__setManualZoom(false);
                        window.__EDUPLAY_SCALE_MODE = 'fit';
                        window.__EDUPLAY_NO_UPSCALE = true;
                        window.__EDUPLAY_SCALE_BIAS = 1.0;
                        if (window.autoScale) { window.autoScale(); didAuto = true; }
                    }catch(e){}
                    var gc = document.getElementById('game-wrapper') || document.getElementById('game-container') || document.querySelector('.game-container');
                    if (gc) {
                        var rect = null;
                        try{ rect = gc.getBoundingClientRect(); }catch(e){ rect = null; }
                        var cw = (rect && rect.width) ? rect.width : (gc.scrollWidth || gc.offsetWidth || 0);
                        var ch = (rect && rect.height) ? rect.height : (gc.scrollHeight || gc.offsetHeight || 0);
                        return { w: cw || 0, h: ch || 0, didAuto: didAuto };
                    }
                    var de = document.documentElement;
                    var db = document.body || de;
                    var cw = Math.max(de.scrollWidth || 0, db.scrollWidth || 0, de.clientWidth || 0);
                    var ch = Math.max(de.scrollHeight || 0, db.scrollHeight || 0, de.clientHeight || 0);
                    return { w: cw || 0, h: ch || 0, didAuto: didAuto };
                })();
            """
            try:
                self.web_view.page().runJavaScript(js, lambda res: self._apply_zoom_result(res, view_w, view_h, _fallback))
            except Exception:
                _fallback()
        except Exception:
            pass

    def _apply_zoom_result(self, res, view_w, view_h, fallback):
        try:
            cw = int((res or {}).get('w') or 0)
            ch = int((res or {}).get('h') or 0)
            if bool((res or {}).get('didAuto')):
                try:
                    self.web_view.setZoomFactor(1.0)
                except Exception:
                    pass
                return
            if cw <= 0 or ch <= 0:
                fallback()
                return
            mode = getattr(self, '_zoom_mode', 'auto')
            if bool(getattr(self, '_preview_portrait', False)) and mode in ['auto','fit_width']:
                ar_target = 9.0/16.0
                new_h = int(view_w/float(ar_target))
                new_h = max(180, new_h)
                self.web_view.setFixedHeight(new_h)
                fw = view_w / float(cw)
                fh = new_h / float(ch)
            else:
                fw = view_w / float(cw)
                fh = view_h / float(ch)
            if mode == 'fit_width':
                factor = fw
            elif mode == 'fit_height':
                factor = fh
            elif mode == 'actual':
                factor = 1.0
            else:
                factor = min(fw, fh)
            factor = max(0.5, min(2.5, factor))
            self.web_view.setZoomFactor(factor)
            try:
                if not bool(getattr(self, '_preview_portrait', False)):
                    ar = cw/float(ch)
                    if ar > 0 and mode in ['auto','fit_width']:
                        new_h2 = int(view_w/float(ar))
                        new_h2 = max(180, new_h2)
                        self.web_view.setFixedHeight(new_h2)
                    else:
                        self.web_view.setFixedHeight(view_h)
            except Exception:
                pass
            try:
                self.web_view.page().runJavaScript(
                    "try{"
                    "var st=document.createElement('style');"
                    "st.innerHTML='html,body{overflow:hidden!important;}*::-webkit-scrollbar{display:none!important}';"
                    "document.head.appendChild(st);"
                    "document.documentElement.style.overflow='hidden';"
                    "document.body.style.overflow='hidden';"
                    "}catch(e){}"
                )
            except Exception:
                pass
        except Exception:
            fallback()

    def _update_zoom_btn_label(self):
        try:
            m = getattr(self, '_zoom_mode', 'auto')
            label = {
                'auto': 'Auto',
                'fit_width': '↔',
                'fit_height': '↕',
                'actual': '100%'
            }.get(m, 'Auto')
            if hasattr(self, '_zoom_btn') and self._zoom_btn:
                self._zoom_btn.setText(label)
        except Exception:
            pass

    def _apply_no_scrollbars(self):
        try:
            self.web_view.page().runJavaScript(
                "try{"
                "var st=document.createElement('style');"
                "st.innerHTML='html,body{overflow:auto!important;height:auto}';"
                "document.head.appendChild(st);"
                "document.documentElement.style.overflow='auto';"
                "document.body.style.overflow='auto';"
                "}catch(e){}"
            )
        except Exception:
            pass


"""
Nguyen-Thanh-Tan ¬_¬
"""
