import hashlib
import os
import tarfile
import zipfile

class ForensicUtils:
    
    @staticmethod
    def extract_and_verify_archive(archive_path, expected_hash):
        """Extract archive and verify its hash"""
        try:
            # Verify archive hash first
            archive_hash = ForensicUtils.calculate_file_hash(archive_path)
            if archive_hash != expected_hash:
                raise ValueError(f"Hash mismatch! Expected {expected_hash}, got {archive_hash}")
            
            # Extract the archive based on its format (tar.gz, zip, etc.)
            extracted_path = None
            if archive_path.endswith(".tar.gz"):
                extracted_path = ForensicUtils.extract_tar_gz(archive_path)
            elif archive_path.endswith(".zip"):
                extracted_path = ForensicUtils.extract_zip(archive_path)
            else:
                raise ValueError("Unsupported archive format")

            return {
                'success': True,
                'archive_hash': archive_hash,
                'extracted_path': extracted_path,
                'original_hash': expected_hash,
                'metadata': {
                    'extracted_files': os.listdir(extracted_path)
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def calculate_file_hash(file_path, hash_algorithm='sha256'):
        """Calculate the hash of a file"""
        hash_func = getattr(hashlib, hash_algorithm)()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def extract_tar_gz(archive_path):
        """Extract tar.gz archive"""
        extracted_path = f"{archive_path}_extracted"
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extracted_path)
        return extracted_path

    @staticmethod
    def extract_zip(archive_path):
        """Extract zip archive"""
        extracted_path = f"{archive_path}_extracted"
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extracted_path)
        return extracted_path
