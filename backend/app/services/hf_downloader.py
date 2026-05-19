import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from huggingface_hub import HfApi, hf_hub_download, scan_cache_dir
from backend.app.config import settings

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    """
    Service client for interacting with the Hugging Face Hub.
    Checks cache, lists repository files, and downloads quantized models.
    """
    def __init__(self):
        self.api = HfApi(token=settings.HF_TOKEN)
        self.cache_dir = settings.hf_cache_path
        os.makedirs(self.cache_dir, exist_ok=True)

    def verify_model_exists(self, model_id: str) -> bool:
        """Checks if a model repository exists on Hugging Face Hub."""
        try:
            self.api.model_info(repo_id=model_id)
            return True
        except Exception as e:
            logger.error(f"Failed to find model '{model_id}' on HF Hub: {str(e)}")
            return False

    def list_gguf_files(self, model_id: str) -> List[str]:
        """Lists all GGUF files in a repository, if any."""
        try:
            repo_info = self.api.model_info(repo_id=model_id)
            files = [f.rfilename for f in repo_info.siblings]
            return [f for f in files if f.endswith(".gguf")]
        except Exception as e:
            logger.error(f"Error listing files for '{model_id}': {str(e)}")
            return []

    def is_model_cached_locally(self, model_id: str, filename: Optional[str] = None) -> bool:
        """
        Scans the local HF cache to check if the repository or a specific file
        is already cached.
        """
        try:
            cache_info = scan_cache_dir(cache_dir=self.cache_dir)
            for repo in cache_info.repos:
                if repo.repo_id == model_id:
                    if filename:
                        # Check if specific file exists within cache commits
                        for revision in repo.revisions:
                            for file in revision.files:
                                if file.file_name == filename:
                                    return True
                    else:
                        # If no file specified, just checking if repo cache exists
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error scanning local HF cache: {str(e)}")
            # Fallback path checking
            if filename:
                # Basic check in standard cache structures
                fallback_path = Path(self.cache_dir) / f"models--{model_id.replace('/', '--')}"
                return fallback_path.exists()
            return False

    def download_model_file(self, model_id: str, filename: str, progress_callback=None) -> str:
        """
        Downloads a specific file (e.g. a GGUF) from the HF Hub.
        Returns the absolute path to the downloaded file.
        """
        try:
            logger.info(f"Downloading '{filename}' from repo '{model_id}'...")
            downloaded_path = hf_hub_download(
                repo_id=model_id,
                filename=filename,
                cache_dir=self.cache_dir,
                token=settings.HF_TOKEN,
                local_files_only=False
            )
            logger.info(f"Successfully downloaded '{filename}' to: {downloaded_path}")
            return downloaded_path
        except Exception as e:
            logger.error(f"Failed to download model file '{filename}' from '{model_id}': {str(e)}")
            raise e

    def resolve_and_download_gguf(self, model_id: str, preferred_quant: str = "q4_k_m") -> str:
        """
        Intelligently resolves the best GGUF file in a repository and downloads it.
        Defaults to 'q4_k_m' or the first available GGUF.
        """
        gguf_files = self.list_gguf_files(model_id)
        if not gguf_files:
            raise ValueError(f"No GGUF files found in Hugging Face repository '{model_id}'.")

        # Attempt to find preferred quant (case-insensitive check)
        selected_file = None
        for f in gguf_files:
            if preferred_quant.lower() in f.lower():
                selected_file = f
                break

        # Fallback to any Q4 or first GGUF
        if not selected_file:
            for f in gguf_files:
                if "q4" in f.lower():
                    selected_file = f
                    break
            if not selected_file:
                selected_file = gguf_files[0]

        return self.download_model_file(model_id, selected_file)

hf_client = HuggingFaceClient()
