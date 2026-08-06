from eduplay.ui.screens.editor_screen import EditorScreen


class EditorFishingScreen(EditorScreen):
    def load_project(self, project):
        p = dict(project or {})
        p['game_type'] = 'fishing'
        cfg = dict(p.get('game_config', {}) or {})
        cfg['game_type'] = 'Fishing Game'
        if 'fish_objects' not in cfg:
            base = 'assets/kenney_platformer-kit/PNG/Default'
            cfg['fish_objects'] = [
                {'sprite': f'{base}/fish_blue.png', 'wrong_sprite': f'{base}/fish_blue_skeleton.png', 'sound': ''},
                {'sprite': f'{base}/fish_green.png', 'wrong_sprite': f'{base}/fish_green_skeleton.png', 'sound': ''},
                {'sprite': f'{base}/fish_orange.png', 'wrong_sprite': f'{base}/fish_orange_skeleton.png', 'sound': ''},
                {'sprite': f'{base}/fish_pink.png', 'wrong_sprite': f'{base}/fish_pink_skeleton.png', 'sound': ''},
                {'sprite': f'{base}/fish_red.png', 'wrong_sprite': f'{base}/fish_red_skeleton.png', 'sound': ''},
            ]
        cfg.setdefault('fish_speed', 5)
        p['game_config'] = cfg
        super().load_project(p)

