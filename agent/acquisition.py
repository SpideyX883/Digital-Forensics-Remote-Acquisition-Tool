# agent/acquisition.py
#
# Disk acquisition (RAW) using dd for maximum speed.
# - No compression during dd
# - Strong guards: command dict, root check, real mountpoint, free-space check
# - Clear errors (never fails silently)
#
# Returns: (evidence_path, "disk") on success, (None, None) on failure.

import os
import re
import shutil
import subprocess
from datetime import datetime

from config import log_error, debug_print


class AcquisitionDispatcher:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode

    def acquire(self, action, command=None):
        action = (action or "").lower()
        if action == "disk":
            return self.acquire_disk(command)
        raise ValueError(f"Unsupported acquisition action: {action}")

    def acquire_disk(self, command):
        """Acquire disk as RAW dd image (fastest)."""
        if not isinstance(command, dict):
            raise ValueError(
                f"acquire_disk expected command dict, got: {type(command).__name__}"
            )

        try:
            # ----------------------------
            # Parameters (safe defaults)
            # ----------------------------
            src_disk = command.get("src_disk", "/dev/sda")
            evidence_mount = command.get("evidence_mount", "/mnt/evidence")
            prepare_evidence = command.get("prepare_evidence", True)

            # Optional tuning knobs
            bs = str(command.get("bs", "16M"))  # bigger is usually faster than 4M
            use_direct_io = bool(command.get("direct_io", False))  # iflag/oflag=direct
            case_id = str(command.get("case_id", "UNKNOWN"))
            filename_prefix = str(command.get("filename_prefix", "disk_image"))
            min_free_multiplier = float(command.get("min_free_multiplier", 1.05))  # 5% headroom

            # ----------------------------
            # Guards / preflight checks
            # ----------------------------
            self._require_root()

            if prepare_evidence:
                os.makedirs(evidence_mount, exist_ok=True)

            self._verify_mount_is_real(evidence_mount)
            self._validate_block_device(src_disk)

            # Ensure enough free space on evidence disk (approx >= src size)
            src_size = self._get_blockdev_size_bytes(src_disk)
            required = int(src_size * min_free_multiplier)
            free = shutil.disk_usage(evidence_mount).free
            if free < required:
                raise RuntimeError(
                    f"Not enough free space on {evidence_mount}. "
                    f"Need ~{self._fmt_bytes(required)} (source {self._fmt_bytes(src_size)} x {min_free_multiplier:.2f}), "
                    f"available {self._fmt_bytes(free)}. "
                    f"Mount a larger evidence disk (e.g., /dev/sdb1) or use compression AFTER acquisition."
                )

            # ----------------------------
            # Output path
            # ----------------------------
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_case = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id)[:64]
            out_path = os.path.join(
                evidence_mount, f"{filename_prefix}_{safe_case}_{ts}.dd"
            )

            # Prevent accidental overwrite
            if os.path.exists(out_path):
                raise FileExistsError(f"Output already exists: {out_path}")

            # ----------------------------
            # dd command (RAW, fastest)
            # ----------------------------
            dd_cmd = [
                "dd",
                f"if={src_disk}",
                f"of={out_path}",
                f"bs={bs}",
                "status=progress",
                "conv=sync,noerror",
            ]

            if use_direct_io:
                # direct I/O can improve throughput on some storage, but not always supported
                dd_cmd.extend(["iflag=direct", "oflag=direct"])

            debug_print(f"[DISK] Starting RAW acquisition: {src_disk} → {out_path}")
            debug_print(f"[DISK] CMD: {' '.join(dd_cmd)}")

            self._run_cmd(dd_cmd, "Disk acquisition failed (dd)")

            # ----------------------------
            # Post-checks
            # ----------------------------
            if not os.path.exists(out_path):
                raise RuntimeError("dd finished but output file does not exist")
            size_out = os.path.getsize(out_path)
            if size_out == 0:
                raise RuntimeError("dd produced empty output file")
            # We allow output smaller than src in edge cases (conv=noerror can skip),
            # but warn if it is way smaller.
            if size_out < int(src_size * 0.90):
                debug_print(
                    f"[WARN] Output file is significantly smaller than source. "
                    f"out={self._fmt_bytes(size_out)}, src={self._fmt_bytes(src_size)}"
                )

            debug_print(f"[DISK] ✅ Completed: {out_path} ({self._fmt_bytes(size_out)})")
            return out_path, "disk"

        except Exception as e:
            log_error("Disk acquisition failed", e)
            return None, None

    # ----------------------------
    # Helpers
    # ----------------------------
    def _require_root(self):
        if os.geteuid() != 0:
            raise PermissionError(
                "Disk acquisition requires root. Run the agent with sudo."
            )

    def _verify_mount_is_real(self, evidence_mount):
        """
        Safety: avoid writing to '/' (sda3) when evidence disk isn't mounted.
        """
        try:
            subprocess.run(
                ["findmnt", evidence_mount],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            raise RuntimeError(
                f"{evidence_mount} is NOT a mounted filesystem. "
                f"Mount your evidence disk (e.g., /dev/sdb1) to {evidence_mount} first."
            )

    def _validate_block_device(self, dev_path):
        if not os.path.exists(dev_path):
            raise FileNotFoundError(f"Source disk does not exist: {dev_path}")
        if not os.path.exists("/sys/class/block"):
            # Very minimal systems: skip strict check
            return
        base = os.path.basename(dev_path)
        # allow /dev/nvme0n1, /dev/sda, /dev/vda etc.
        if not os.path.exists(f"/sys/class/block/{base}"):
            raise ValueError(
                f"{dev_path} does not look like a valid block device. "
                f"Check src_disk in your task command."
            )

    def _get_blockdev_size_bytes(self, dev_path) -> int:
        """
        Uses blockdev if available, else reads /sys.
        """
        if shutil.which("blockdev"):
            try:
                out = subprocess.check_output(
                    ["blockdev", "--getsize64", dev_path], text=True
                ).strip()
                return int(out)
            except Exception:
                pass

        base = os.path.basename(dev_path)
        size_path = f"/sys/class/block/{base}/size"
        if os.path.exists(size_path):
            # number of 512-byte sectors
            with open(size_path, "r", encoding="utf-8") as f:
                sectors = int(f.read().strip())
            return sectors * 512

        raise RuntimeError(f"Unable to determine disk size for {dev_path}")

    def _run_cmd(self, cmd, err_msg):
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"{err_msg}: {e}") from e

    def _fmt_bytes(self, n: int) -> str:
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        v = float(n)
        i = 0
        while v >= 1024 and i < len(units) - 1:
            v /= 1024.0
            i += 1
        return f"{v:.2f} {units[i]}"
