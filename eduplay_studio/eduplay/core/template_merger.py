"""
HTML Template Merger for Millionaire Game
Handles merging of HTML template with game data and assets
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from .asset_bundler import AssetBundler


class MillionaireTemplateMerger:
    """Handles merging of Millionaire game template with data and assets"""
    
    def __init__(self, assets_dir: Path):
        self.assets_dir = Path(assets_dir)
        self.bundler = AssetBundler(assets_dir)
        
        # Prize amounts for the game (in VND)
        self.prize_amounts = [
            "200,000", "400,000", "600,000", "1,000,000", "2,000,000",
            "3,000,000", "6,000,000", "10,000,000", "14,000,000", "20,000,000",
            "30,000,000", "40,000,000", "60,000,000", "85,000,000", "150,000,000"
        ]
    
    def normalize_questions(self, questions_data: List[Dict]) -> List[Dict]:
        """Normalize questions from various formats to standard format"""
        normalized_questions = []
        
        for q in questions_data:
            # Handle different question field names
            question_text = q.get('question') or q.get('text') or q.get('content') or ''
            
            # Handle different options field names
            options = q.get('options') or q.get('answers') or q.get('choices') or []
            
            # Handle different correct answer formats
            correct_answer = q.get('correct_answer') or q.get('correct') or q.get('answer') or 0
            
            # Convert correct answer to index if it's a letter (A, B, C, D)
            if isinstance(correct_answer, str) and correct_answer.upper() in ['A', 'B', 'C', 'D']:
                correct_answer = ord(correct_answer.upper()) - ord('A')
            elif isinstance(correct_answer, str) and correct_answer.isdigit():
                correct_answer = int(correct_answer)
            
            # Ensure correct_answer is within valid range
            if isinstance(correct_answer, int) and 0 <= correct_answer < len(options):
                pass  # Valid index
            else:
                correct_answer = 0  # Default to first option
            
            normalized_question = {
                'question': question_text,
                'options': options,
                'correct_answer': correct_answer,
                'explanation': q.get('explanation') or q.get('feedback') or '',
                'difficulty': q.get('difficulty', 'medium'),
                'category': q.get('category', 'general')
            }
            
            # Add lifeline hints if available
            if 'phone_hint' in q:
                normalized_question['phone_hint'] = q['phone_hint']
            if 'audience_hint' in q:
                normalized_question['audience_hint'] = q['audience_hint']
            
            normalized_questions.append(normalized_question)
        
        return normalized_questions
    
    def create_game_data(self, project_data: Dict, teacher_questions: List[Dict]) -> Dict:
        """Create game data structure from project and teacher questions"""
        
        # Normalize teacher questions
        questions = self.normalize_questions(teacher_questions)
        
        # If no teacher questions, use sample questions
        if not questions:
            questions = self.get_sample_questions()
        
        # Ensure we have exactly 15 questions
        while len(questions) < 15:
            questions.extend(self.get_sample_questions())
        
        questions = questions[:15]  # Take only first 15
        
        game_data = {
            'title': project_data.get('title', 'Ai Là Triệu Phú'),
            'description': project_data.get('description', 'Game show Ai là triệu phú'),
            'language': project_data.get('language', 'vi'),
            'difficulty': project_data.get('difficulty', 'medium'),
            'questions': questions,
            'prize_amounts': self.prize_amounts,
            'safe_levels': [4, 9, 14],  # Safe levels (5th, 10th, 15th questions)
            'lifelines': {
                'fifty_fifty': True,
                'phone_friend': True,
                'ask_audience': True
            },
            'settings': {
                'time_limit': project_data.get('time_limit', 45),
                'sound_enabled': project_data.get('sound_enabled', True),
                'animations_enabled': project_data.get('animations_enabled', True)
            }
        }
        
        return game_data
    
    def get_sample_questions(self) -> List[Dict]:
        """Get sample questions for fallback"""
        return [
            {
                'question': 'Câu hỏi mẫu: Việt Nam có bao nhiêu tỉnh thành?',
                'options': ['63', '64', '65', '66'],
                'correct_answer': 0,
                'explanation': 'Việt Nam có 63 tỉnh thành.',
                'difficulty': 'easy',
                'category': 'geography'
            },
            {
                'question': 'Câu hỏi mẫu: Thủ đô của Việt Nam là gì?',
                'options': ['Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng', 'Hải Phòng'],
                'correct_answer': 1,
                'explanation': 'Thủ đô của Việt Nam là Hà Nội.',
                'difficulty': 'easy',
                'category': 'geography'
            }
        ]
    
    def process_html_content(self, html_content: str, game_data: Dict) -> str:
        """Process HTML content to inject game data and replace assets"""
        
        # Process HTML to replace asset references
        processed_html = self.bundler.process_html_template(html_content)
        
        # Inject game data
        game_data_json = json.dumps(game_data, ensure_ascii=False, indent=2)
        
        # Replace or inject game data script
        if '<script id="game-data"' in processed_html:
            # Replace existing game data
            pattern = r'<script id="game-data"[^>]*>.*?</script>'
            replacement = f'<script id="game-data" type="application/json">\n{game_data_json}\n</script>'
            processed_html = re.sub(pattern, replacement, processed_html, flags=re.DOTALL)
        else:
            # Inject before closing body tag
            processed_html = processed_html.replace('</body>', 
                f'<script id="game-data" type="application/json">\n{game_data_json}\n</script>\n</body>')
        
        # Process CSS files (NGDAT template uses inline CSS; keep optional vendor CSS if present)
        css_files = ['bootstrap.min.css', 'font-awesome.min.css']
        bundled_css = []
        for css_file in css_files:
            css_path = self.assets_dir / css_file
            if css_path.exists():
                css_content = self.bundler.bundle_css_file(css_path)
                bundled_css.append(css_content)
        
        # Inject bundled CSS
        if bundled_css:
            css_content = '\n'.join(bundled_css)
            if '<style>' in processed_html:
                # Replace existing style tag
                pattern = r'<style[^>]*>.*?</style>'
                replacement = f'<style>\n{css_content}\n</style>'
                processed_html = re.sub(pattern, replacement, processed_html, flags=re.DOTALL)
            else:
                # Add to head
                processed_html = processed_html.replace('</head>', 
                    f'<style>\n{css_content}\n</style>\n</head>')
        
        # Process JavaScript files (bundle if present in assets folder)
        js_files = ['jquery.min.js.tải xuống', 'bootstrap.min.js.tải xuống', 'TweenMax.min.js.tải xuống', 'underscore-min.js.tải xuống']
        bundled_js = []
        for js_file in js_files:
            js_path = self.assets_dir / js_file
            if js_path.exists():
                js_content = self.bundler.bundle_javascript_file(js_path)
                bundled_js.append(js_content)
        
        # Inject bundled JavaScript
        if bundled_js:
            js_content = '\n'.join(bundled_js)
            processed_html = processed_html.replace('</body>', 
                f'<script>\n{js_content}\n</script>\n</body>')
        
        return processed_html
    
    def create_single_file_export(self, html_template: str, project_data: Dict, 
                                teacher_questions: List[Dict]) -> str:
        """Create complete single-file HTML export"""
        
        # Create game data
        game_data = self.create_game_data(project_data, teacher_questions)
        
        # Process HTML content
        processed_html = self.process_html_content(html_template, game_data)
        
        # Create asset manifest
        asset_manifest = self.bundler.create_asset_manifest()
        
        # Inject asset manifest
        manifest_json = json.dumps(asset_manifest, ensure_ascii=False, indent=2)
        processed_html = processed_html.replace('</body>', 
            f'<script id="asset-manifest" type="application/json">\n{manifest_json}\n</script>\n</body>')
        
        return processed_html
"""
Nguyen-Thanh-Tan ¬_¬
"""
