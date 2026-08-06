"""
Asset Manager - Manages game assets and resources
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from eduplay.core.path_resolver import PathResolver

DB_PATH = str(PathResolver.resolve_asset_db_path())

class AssetManager:
    """Manages game assets and resources"""
    
    def __init__(self, db_path: str = None):
        """Initialize asset manager"""
        if db_path is None:
            self.db_path = DB_PATH
        else:
            self.db_path = db_path
        
        # Ensure the directory for the database exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize the assets database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create assets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default categories
        default_categories = [
            ("fish", "Fish sprites for fishing games"),
            ("background", "Background images and textures"),
            ("ui", "User interface elements"),
            ("sound", "Sound effects and music"),
            ("effects", "Visual effects and particles")
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)
        ''', default_categories)
        
        # Insert default tags
        default_tags = [
            "fish", "blue", "green", "orange", "red", "pink",
            "skeleton", "outline", "platformer", "kenney"
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO tags (name) VALUES (?)
        ''', [(tag,) for tag in default_tags])
        
        conn.commit()
        conn.close()
    
    def scan_bundled_assets(self):
        """Scan and register bundled assets"""
        assets_bundle_dir = Path(__file__).parent.parent / "assets_bundle"
        
        if not assets_bundle_dir.exists():
            return
        
        # Scan Kenney platformer kit
        kenney_dir = assets_bundle_dir / "kenney_platformer-kit"
        if kenney_dir.exists():
            self._scan_kenney_assets(kenney_dir)
        
        # Scan sound assets
        sound_dir = assets_bundle_dir / "sound"
        if sound_dir.exists():
            self._scan_sound_assets(sound_dir)
    
    def _scan_kenney_assets(self, kenney_dir: Path):
        """Scan Kenney platformer kit assets"""
        categories = {
            "fish": ["fish"],
            "background": ["background", "terrain"],
            "effects": ["bubble", "hud"]
        }
        
        for png_dir in kenney_dir.glob("PNG/*"):
            if png_dir.is_dir():
                for file_path in png_dir.glob("*.png"):
                    relative_path = file_path.relative_to(Path(__file__).parent.parent)
                    
                    # Determine category and tags
                    category = "other"
                    tags = []
                    
                    filename = file_path.stem.lower()
                    
                    # Determine category
                    for cat, keywords in categories.items():
                        if any(keyword in filename for keyword in keywords):
                            category = cat
                            break
                    
                    # Extract tags from filename
                    if "fish" in filename:
                        tags.append("fish")
                        if "blue" in filename:
                            tags.append("blue")
                        elif "green" in filename:
                            tags.append("green")
                        elif "orange" in filename:
                            tags.append("orange")
                        elif "red" in filename:
                            tags.append("red")
                        elif "pink" in filename:
                            tags.append("pink")
                        
                        if "skeleton" in filename:
                            tags.append("skeleton")
                        if "outline" in filename:
                            tags.append("outline")
                    
                    # Add asset to database
                    self.add_asset(
                        name=file_path.stem,
                        path=str(relative_path),
                        type="image",
                        category=category,
                        tags=tags,
                        metadata={
                            "width": 64,  # Default size, can be updated
                            "height": 64,
                            "format": "PNG",
                            "source": "kenney_platformer-kit"
                        }
                    )
    
    def _scan_sound_assets(self, sound_dir: Path):
        """Scan sound assets"""
        sound_files = list(sound_dir.glob("*.mp3")) + list(sound_dir.glob("*.wav"))
        
        for file_path in sound_files:
            relative_path = file_path.relative_to(Path(__file__).parent.parent)
            
            # Determine category based on filename
            filename = file_path.stem.lower()
            category = "sound"
            tags = ["sound"]
            
            if "background" in filename or "music" in filename:
                category = "music"
                tags.append("background")
            elif "correct" in filename:
                category = "effect"
                tags.extend(["correct", "positive"])
            elif "wrong" in filename:
                category = "effect"
                tags.extend(["wrong", "negative"])
            elif "click" in filename:
                category = "effect"
                tags.append("click")
            
            self.add_asset(
                name=file_path.stem,
                path=str(relative_path),
                type="audio",
                category=category,
                tags=tags,
                metadata={
                    "format": file_path.suffix[1:].upper(),
                    "duration": 1.0,  # Default duration
                    "source": "bundled"
                }
            )
    
    def add_asset(self, name: str, path: str, type: str, 
                  category: str = None, tags: List[str] = None, 
                  metadata: Dict = None) -> bool:
        """Add a new asset to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if asset already exists
            cursor.execute('SELECT id FROM assets WHERE path = ?', (path,))
            if cursor.fetchone():
                # Update existing asset
                cursor.execute('''
                    UPDATE assets 
                    SET name = ?, type = ?, category = ?, tags = ?, metadata = ?, modified_at = ?
                    WHERE path = ?
                ''', (name, type, category, json.dumps(tags or []), 
                      json.dumps(metadata or {}), datetime.now(), path))
            else:
                # Insert new asset
                cursor.execute('''
                    INSERT INTO assets (name, path, type, category, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, path, type, category, json.dumps(tags or []), 
                      json.dumps(metadata or {})))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding asset: {e}")
            return False
    
    def get_asset(self, asset_id: int) -> Optional[Dict]:
        """Get asset by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, path, type, category, tags, metadata, created_at, modified_at
                FROM assets WHERE id = ?
            ''', (asset_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "type": row[3],
                    "category": row[4],
                    "tags": json.loads(row[5]) if row[5] else [],
                    "metadata": json.loads(row[6]) if row[6] else {},
                    "created_at": row[7],
                    "modified_at": row[8]
                }
            
        except Exception as e:
            print(f"Error getting asset: {e}")
        
        return None
    
    def get_assets_by_type(self, asset_type: str) -> List[Dict]:
        """Get all assets of a specific type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, path, type, category, tags, metadata, created_at, modified_at
                FROM assets WHERE type = ? ORDER BY name
            ''', (asset_type,))
            
            rows = cursor.fetchall()
            conn.close()
            
            assets = []
            for row in rows:
                assets.append({
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "type": row[3],
                    "category": row[4],
                    "tags": json.loads(row[5]) if row[5] else [],
                    "metadata": json.loads(row[6]) if row[6] else {},
                    "created_at": row[7],
                    "modified_at": row[8]
                })
            
            return assets
            
        except Exception as e:
            print(f"Error getting assets by type: {e}")
            return []
    
    def get_assets_by_category(self, category: str) -> List[Dict]:
        """Get all assets in a specific category"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, path, type, category, tags, metadata, created_at, modified_at
                FROM assets WHERE category = ? ORDER BY name
            ''', (category,))
            
            rows = cursor.fetchall()
            conn.close()
            
            assets = []
            for row in rows:
                assets.append({
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "type": row[3],
                    "category": row[4],
                    "tags": json.loads(row[5]) if row[5] else [],
                    "metadata": json.loads(row[6]) if row[6] else {},
                    "created_at": row[7],
                    "modified_at": row[8]
                })
            
            return assets
            
        except Exception as e:
            print(f"Error getting assets by category: {e}")
            return []
    
    def search_assets(self, query: str) -> List[Dict]:
        """Search assets by name or tags"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search in name and tags
            cursor.execute('''
                SELECT id, name, path, type, category, tags, metadata, created_at, modified_at
                FROM assets 
                WHERE name LIKE ? OR tags LIKE ? OR category LIKE ?
                ORDER BY name
            ''', (f"%{query}%", f"%{query}%", f"%{query}%"))
            
            rows = cursor.fetchall()
            conn.close()
            
            assets = []
            for row in rows:
                assets.append({
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "type": row[3],
                    "category": row[4],
                    "tags": json.loads(row[5]) if row[5] else [],
                    "metadata": json.loads(row[6]) if row[6] else {},
                    "created_at": row[7],
                    "modified_at": row[8]
                })
            
            return assets
            
        except Exception as e:
            print(f"Error searching assets: {e}")
            return []
    
    def delete_asset(self, asset_id: int) -> bool:
        """Delete an asset"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Error deleting asset: {e}")
            return False
    
    def get_categories(self) -> List[Dict]:
        """Get all categories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, description, created_at FROM categories ORDER BY name')
            
            rows = cursor.fetchall()
            conn.close()
            
            categories = []
            for row in rows:
                categories.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3]
                })
            
            return categories
            
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def get_tags(self) -> List[str]:
        """Get all tags"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT name FROM tags ORDER BY name')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
            
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []
