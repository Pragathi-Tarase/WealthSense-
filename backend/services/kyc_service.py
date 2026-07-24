import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class KYCService:
    def __init__(self):
        # We now use the local standalone Vault instead of Digio
        self.vault_path = Path(__file__).parent.parent / "database" / "identity_vault.json"

    def _load_vault(self):
        try:
            if self.vault_path.exists():
                with open(self.vault_path, "r") as f:
                    return json.load(f)
            return {"verified_users": []}
        except Exception as e:
            logger.error(f"Error loading Identity Vault: {e}")
            return {"verified_users": []}

    def verify_pan_demat(self, pan: str, demat: str) -> bool:
        """
        Verifies identity against the local Standalone Vault.
        No API keys or internet connection required.
        """
        vault = self._load_vault()
        verified_users = vault.get("verified_users", [])

        # Strict check: PAN must exist AND match the specific Demat ID
        for user in verified_users:
            if user.get("pan") == pan:
                if user.get("demat") == demat:
                    logger.info(f"[Identity Vault] Verified identity for PAN: {pan}")
                    return True
                else:
                    logger.warning(f"[Identity Vault] PAN {pan} found, but Demat mismatch.")
                    return False
        
        logger.warning(f"[Identity Vault] PAN {pan} not found in verified records.")
        return False

kyc_service = KYCService()
