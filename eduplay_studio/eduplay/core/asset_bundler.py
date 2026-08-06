"""
Asset Bundler Utility for Single-File Export
Handles base64 encoding of assets and merging into single HTML file
"""

import base64
import mimetypes
import json
from pathlib import Path
from typing import Dict, List, Optional
import re


class AssetBundler:
    """Utility class for bundling assets into base64 format for single-file export"""
    
    def __init__(self, assets_dir: Path):
        self.assets_dir = Path(assets_dir)
        self.asset_cache: Dict[str, str] = {}
    
    def encode_file_to_base64(self, file_path: Path) -> Optional[str]:
        """Encode a file to base64 string with proper data URI format"""
        try:
            if not file_path.exists():
                return None
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                # Default MIME types for common extensions
                ext = file_path.suffix.lower()
                mime_types = {
                    '.js': 'application/javascript',
                    '.css': 'text/css',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                    '.woff': 'font/woff',
                    '.woff2': 'font/woff2',
                    '.ttf': 'font/ttf',
                    '.mp3': 'audio/mpeg',
                    '.wav': 'audio/wav',
                    '.ogg': 'audio/ogg'
                }
                mime_type = mime_types.get(ext, 'application/octet-stream')
            
            # Read file and encode
            with open(file_path, 'rb') as f:
                file_data = f.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')
            
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            print(f"Error encoding file {file_path}: {e}")
            return None
    
    def bundle_css_file(self, css_path: Path) -> str:
        """Bundle CSS file with embedded assets"""
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Find and replace url() references
            url_pattern = r'url\([\'"]?([^\'"\)]+)[\'"]?\)'
            
            def replace_url(match):
                url = match.group(1)
                # Skip external URLs and data URLs
                if url.startswith(('http://', 'https://', 'data:')):
                    return match.group(0)
                
                # Resolve relative path
                asset_path = css_path.parent / url
                if asset_path.exists():
                    base64_data = self.encode_file_to_base64(asset_path)
                    if base64_data:
                        return f'url({base64_data})'
                
                return match.group(0)
            
            # Replace all URL references
            bundled_css = re.sub(url_pattern, replace_url, css_content)
            return bundled_css
            
        except Exception as e:
            print(f"Error bundling CSS {css_path}: {e}")
            return ""
    
    def bundle_javascript_file(self, js_path: Path) -> str:
        """Bundle JavaScript file (mainly for reference, usually no assets to embed)"""
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error bundling JS {js_path}: {e}")
            return ""
    
    def create_asset_manifest(self) -> Dict[str, str]:
        """Create manifest of all bundled assets"""
        manifest = {}
        
        # Process all asset files
        for file_path in self.assets_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                relative_path = file_path.relative_to(self.assets_dir)
                base64_data = self.encode_file_to_base64(file_path)
                if base64_data:
                    manifest[str(relative_path).replace('\\', '/')] = base64_data
        
        return manifest
    
    def create_single_file_html(self, html_template: str, game_data: Dict, 
                              css_files: List[str], js_files: List[str]) -> str:
        """Create single HTML file with all assets embedded"""
        
        # Bundle CSS files
        bundled_css = []
        for css_file in css_files:
            css_path = self.assets_dir / css_file
            if css_path.exists():
                css_content = self.bundle_css_file(css_path)
                bundled_css.append(css_content)
        bundled_css.append("""
.progressBar{background:#020617 !important;border:1px solid rgba(227,171,40,0.75) !important;border-radius:10px !important;overflow:hidden !important;}
.progressLevel{background:#E3AB28 !important;min-height:24px !important;border-radius:9px !important;}
""")
        
        # Bundle JS files
        bundled_js = []
        for js_file in js_files:
            js_path = self.assets_dir / js_file
            if js_path.exists():
                js_content = self.bundle_javascript_file(js_path)
                bundled_js.append(js_content)
        
        # Create asset manifest
        asset_manifest = self.create_asset_manifest()
        
        # Embed game data
        game_data_json = json.dumps(game_data, ensure_ascii=False, indent=2)
        
        # Create final HTML
        single_file_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{game_data.get('title', 'Ai Là Triệu Phú')}</title>
    <style>
{chr(10).join(bundled_css)}
    </style>
</head>
<body>
    <!-- Game Data -->
    <script id="game-data" type="application/json">
{game_data_json}
    </script>
    
    <!-- Asset Manifest -->
    <script id="asset-manifest" type="application/json">
{json.dumps(asset_manifest, ensure_ascii=False, indent=2)}
    </script>
    
    <!-- Game HTML Content -->
    {html_template}
    
    <!-- Bundled JavaScript -->
    <script>
{chr(10).join(bundled_js)}
    </script>
</body>
</html>"""
        
        return single_file_html
    
    def process_html_template(self, html_content: str) -> str:
        """Process HTML template to replace asset references with base64 data"""
        
        # Replace image src attributes
        img_pattern = r'<img[^>]+src=[\'"]([^\'"]+)[\'"][^>]*>'
        
        def replace_img_src(match):
            full_tag = match.group(0)
            src = match.group(1)
            
            # Skip external URLs and data URLs
            if src.startswith(('http://', 'https://', 'data:')):
                return full_tag
            
            # Resolve relative path
            asset_path = self.assets_dir / src
            if asset_path.exists():
                base64_data = self.encode_file_to_base64(asset_path)
                if base64_data:
                    return full_tag.replace(src, base64_data)
            
            return full_tag
        
        # Replace all image references
        processed_html = re.sub(img_pattern, replace_img_src, html_content)
        
        return processed_html
"""
Nguyen-Thanh-Tan ¬_¬
"""
