import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime

# Project root is two levels up from this file (apps/api/storage.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_storage_dir() -> Path:
    """
    Resolve storage directory path
    
    Returns:
        Absolute Path to storage directory
    """
    # Read from environment or use default
    storage_dir_str = os.getenv("STORAGE_DIR", "./data")
    storage_path = Path(storage_dir_str)
    
    # If relative path, resolve from project root
    if not storage_path.is_absolute():
        storage_path = PROJECT_ROOT / storage_path
    
    # Create directory if it doesn't exist
    storage_path.mkdir(parents=True, exist_ok=True)
    
    return storage_path.resolve()


class StorageManager:
    """Utility class for file storage operations"""
    
    def __init__(self):
        self.base_dir = resolve_storage_dir()
        self.jobs_dir = self.base_dir / "jobs"
        self._ensure_storage_directories()
    
    def _ensure_storage_directories(self):
        """Create storage directories if they don't exist"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
    
    def ensure_job_dir(self, job_id: str) -> Path:
        """Create job directory if it doesn't exist"""
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def save_uploadfile(self, job_id: str, upload_file, filename: str = "input.pdf") -> Path:
        """
        Save uploaded file to job directory with guaranteed persistence
        
        Args:
            job_id: Job identifier
            upload_file: FastAPI UploadFile object
            filename: Target filename
            
        Returns:
            Path: Path to saved file
        """
        job_dir = self.ensure_job_dir(job_id)
        file_path = job_dir / filename
        
        # Stream file content with copyfileobj for memory efficiency
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
            # Force write to disk
            f.flush()
            os.fsync(f.fileno())
        
        # Reset file pointer for potential reuse
        upload_file.file.seek(0)
        
        return file_path
    
    def load_job(self, job_id: str) -> Dict[str, Any]:
        """Load job data from job.json"""
        job_file = self.jobs_dir / job_id / "job.json"
        if not job_file.exists():
            raise FileNotFoundError(f"Job {job_id} not found")
        
        with open(job_file, "r") as f:
            return json.load(f)
    
    def save_job(self, job_id: str, job_dict: Dict[str, Any]) -> None:
        """Save job data to job.json atomically"""
        job_dir = self.ensure_job_dir(job_id)
        job_file = job_dir / "job.json"
        temp_file = job_dir / "job.json.tmp"
        
        # Write to temporary file first
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(job_dict, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(job_file)
    
    def save_ocr_translations(self, job_id: str, translations: Dict[str, Any]) -> None:
        """Save OCR translations to ocr_translations.json"""
        job_dir = self.ensure_job_dir(job_id)
        translations_file = job_dir / "ocr_translations.json"
        temp_file = job_dir / "ocr_translations.json.tmp"
        
        # Write to temporary file first
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(translations, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(translations_file)
    
    def load_ocr_translations(self, job_id: str) -> Dict[str, Any]:
        """Load OCR translations from ocr_translations.json"""
        translations_file = self.jobs_dir / job_id / "ocr_translations.json"
        if not translations_file.exists():
            return {}
        
        with open(translations_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def job_exists(self, job_id: str) -> bool:
        """Check if job exists"""
        job_file = self.jobs_dir / job_id / "job.json"
        return job_file.exists()
    
    # Legacy methods for backward compatibility
    def save_file(self, file_content: bytes, filename: str = None) -> str:
        """Legacy method - save file to storage directory"""
        if filename is None:
            filename = f"{uuid.uuid4()}.tmp"
        
        file_path = self.storage_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return str(file_path)
    
    def get_file_path(self, filename: str) -> Path:
        """Legacy method - get full path for a filename"""
        return self.storage_dir / filename
    
    def file_exists(self, filename: str) -> bool:
        """Legacy method - check if file exists"""
        return (self.storage_dir / filename).exists()
    
    def delete_file(self, filename: str) -> bool:
        """Legacy method - delete file if exists"""
        file_path = self.storage_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False

# Global storage manager instance
storage_manager = StorageManager()