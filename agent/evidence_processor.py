import os
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from config import debug_print, log_error


class EvidenceProcessor:
    """
    Packages acquired evidence into your forensic archive format.
    IMPORTANT: All temp/staging is done under evidence_mount (NOT /tmp).
    """

    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode

    def process(self, evidence_path, case_id, evidence_type, agent_id, evidence_mount=None):
        """
        evidence_path: path to acquired file (e.g. /mnt/evidence/disk_image.dd.gz)
        evidence_mount: mounted evidence disk path (e.g. /mnt/evidence)
                       If not supplied, inferred from evidence_path.
        Returns: (archive_path, verification_data)
        """
        try:
            if not evidence_path or not os.path.exists(evidence_path):
                raise FileNotFoundError(f"Evidence file not found: {evidence_path}")

            # Infer mount if not provided
            if not evidence_mount:
                evidence_mount = str(Path(evidence_path).resolve().parent)

            # Hard guard: ensure evidence_mount is the same FS mount you intended
            self._verify_mount_is_real(evidence_mount)

            # Create temp processing dir ON evidence disk
            temp_dir = tempfile.mkdtemp(prefix="forensic_process_", dir=evidence_mount)
            debug_print(f"[PROCESS] Using temp dir on evidence disk: {temp_dir}")

            # Working folder inside temp
            evidence_id = f"EVD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}"
            work_dir = os.path.join(temp_dir, f"evidence_{evidence_id}")
            os.makedirs(work_dir, exist_ok=True)

            # Copy evidence file into work dir (still on evidence disk)
            evidence_filename = os.path.basename(evidence_path)
            staged_path = os.path.join(work_dir, evidence_filename)
            shutil.copy2(evidence_path, staged_path)

            # Create metadata
            metadata = {
                "evidence_id": evidence_id,
                "case_id": case_id,
                "evidence_type": evidence_type,
                "agent_id": agent_id,
                "original_filename": evidence_filename,
                "acquisition_time": datetime.now().isoformat(),
            }
            meta_path = os.path.join(work_dir, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            # Create forensic package (archive) ON evidence disk
            # You likely already have create_forensic_package() and want to reuse it:
            # If your ForensicUtils.create_forensic_package expects a source file path,
            # we can package staged_path + metadata.json by zipping the whole work_dir.
            archive_path = os.path.join(evidence_mount, f"{evidence_id}.zip")

            debug_print(f"[PROCESS] Creating forensic package: {archive_path}")
            ForensicUtils.create_zip_from_folder(work_dir, archive_path)  # implement or map to your existing function

            # Hashes (on evidence disk, no /tmp)
            original_hash = ForensicUtils.calculate_hash(staged_path)
            archive_hash = ForensicUtils.calculate_hash(archive_path)

            verification_data = {
                "evidence_id": evidence_id,
                "original_hash": original_hash,
                "archive_hash": archive_hash,
                "metadata": metadata,
            }

            debug_print(f"[PROCESS] ✅ Package complete: {archive_path}")
            return archive_path, verification_data

        except Exception as e:
            log_error("Evidence processing failed", e)
            return None, None

        finally:
            # Cleanup temp dir (on evidence disk)
            try:
                if "temp_dir" in locals() and temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _verify_mount_is_real(self, evidence_mount):
        # Simple guard that mount exists and is mountpoint
        import subprocess
        subprocess.run(["findmnt", evidence_mount], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cleanup(self):
        # Keep method to avoid your old AttributeError issues
        return
