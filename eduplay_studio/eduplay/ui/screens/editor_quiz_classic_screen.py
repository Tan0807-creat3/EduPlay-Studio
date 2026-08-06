from eduplay.ui.screens.editor_screen import EditorScreen


class EditorQuizClassicScreen(EditorScreen):
    def load_project(self, project):
        p = dict(project or {})
        cfg = dict(p.get('game_config', {}) or {})
        if 'question_time' not in cfg:
            cfg['question_time'] = 30
        p['game_config'] = cfg
        super().load_project(p)

"""
Nguyen-Thanh-Tan ¬_¬
"""
