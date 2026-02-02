import csv
import logging
import os
from typing import List, Dict
import hashlib

logger = logging.getLogger(__name__)

class SheetSyncAgent:
    """
    Phase 81: Google Sheet Sync.
    Watches a local CSV (mounted from Drive) and ingests new Research topics.
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.known_hashes = set()
        self.new_items = []
        
    def sync(self) -> List[Dict]:
        """
        Reads the CSV and returns new items since last sync.
        """
        if not os.path.exists(self.filepath):
            logger.warning(f"Sheet not found at {self.filepath}")
            return []
            
        new_batch = []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Clean keys (remove BOM or spaces)
                    clean_row = {k.strip(): v for k, v in row.items() if k}
                    
                    link = clean_row.get("Link", "")
                    if not link: continue
                    
                    # Create unique ID
                    row_hash = hashlib.md5(link.encode()).hexdigest()
                    
                    if row_hash not in self.known_hashes:
                        self.known_hashes.add(row_hash)
                        
                        # Parse Physics Vector if present "12D [nov:0.95...]"
                        abstractions = clean_row.get("Key Abstractions", "")
                        
                        item = {
                            "id": row_hash,
                            "link": link,
                            "abstractions": abstractions,
                            "category": clean_row.get("Category", "Unknown"),
                            "integration": clean_row.get("Integration Point", "")
                        }
                        new_batch.append(item)
                        
            if new_batch:
                logger.info(f"📑 Sheet Sync: Found {len(new_batch)} new research items.")
                
            return new_batch
            
        except Exception as e:
            logger.error(f"Sheet Sync Failed: {e}")
            return []
