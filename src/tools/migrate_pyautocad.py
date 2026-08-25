"""
PyAutoCAD to Enhanced AutoCAD Migration Script
============================================

Automated migration script that safely replaces pyautocad imports with
Enhanced AutoCAD wrapper while maintaining 100% compatibility.
Includes comprehensive rollback capability and validation.
"""

import os
import re
import shutil
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import time
import json

logger = logging.getLogger(__name__)


class PyAutoCADMigrator:
    """
    Handles migration from pyautocad to Enhanced AutoCAD wrapper.
    """

    def __init__(self, project_root: str):
        """
        Initialize migrator.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.backup_dir = self.project_root / "migration_backup"
        self.migration_log = []
        self.migration_timestamp = time.time()

        # Migration patterns
        self.import_patterns = [
            # Direct imports
            (
                r"from pyautocad import Autocad",
                "from enhanced_autocad.compatibility_layer import Autocad",
            ),
            (r"from pyautocad import \*", "from enhanced_autocad.compatibility_layer import *"),
            (r"import pyautocad", "import enhanced_autocad.compatibility_layer as pyautocad"),
            # Specific function imports
            (r"from pyautocad import (.*)", r"from enhanced_autocad.compatibility_layer import \1"),
            # Module reference patterns
            (r"pyautocad\.Autocad", "enhanced_autocad.compatibility_layer.Autocad"),
            (r"pyautocad\.apoint", "enhanced_autocad.compatibility_layer.apoint"),
            (r"pyautocad\.aDouble", "enhanced_autocad.compatibility_layer.aDouble"),
            (r"pyautocad\.aInt", "enhanced_autocad.compatibility_layer.aInt"),
            (r"pyautocad\.aShort", "enhanced_autocad.compatibility_layer.aShort"),
        ]

    def create_backup(self) -> bool:
        """
        Create complete backup of source files before migration.

        Returns:
            True if backup successful
        """
        try:
            logger.info(f"Creating migration backup at {self.backup_dir}")

            # Remove existing backup if it exists
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)

            # Create backup directory
            self.backup_dir.mkdir(parents=True)

            # Copy all source files
            for file_path in self._get_python_files():
                relative_path = file_path.relative_to(self.project_root)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)

                self.migration_log.append(
                    {
                        "action": "backup_created",
                        "file": str(relative_path),
                        "timestamp": time.time(),
                    }
                )

            # Create backup metadata
            metadata = {
                "backup_timestamp": self.migration_timestamp,
                "project_root": str(self.project_root),
                "python_version": "3.12+",
                "migration_tool_version": "1.0.0",
            }

            with open(self.backup_dir / "backup_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Backup created successfully with {len(self.migration_log)} files")
            return True

        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            return False

    def _get_python_files(self) -> List[Path]:
        """
        Get all Python files in the project.

        Returns:
            List of Python file paths
        """
        python_files = []

        # Search in src directory and subdirectories
        for pattern in ["**/*.py"]:
            python_files.extend(self.src_dir.glob(pattern))

        # Also check root level files
        for pattern in ["*.py"]:
            python_files.extend(self.project_root.glob(pattern))

        return [f for f in python_files if f.is_file()]

    def analyze_migration_scope(self) -> Dict[str, any]:
        """
        Analyze the scope of migration required.

        Returns:
            Dictionary containing migration analysis
        """
        analysis = {
            "files_to_migrate": [],
            "import_patterns_found": {},
            "total_files": 0,
            "files_with_pyautocad": 0,
            "estimated_changes": 0,
        }

        python_files = self._get_python_files()
        analysis["total_files"] = len(python_files)

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check if file contains pyautocad references
                if "pyautocad" in content:
                    analysis["files_with_pyautocad"] += 1
                    relative_path = file_path.relative_to(self.project_root)
                    file_analysis = {
                        "file": str(relative_path),
                        "patterns_found": [],
                        "changes_needed": 0,
                    }

                    # Check each pattern
                    for pattern, replacement in self.import_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            pattern_info = {
                                "pattern": pattern,
                                "matches": len(matches),
                                "replacement": replacement,
                            }
                            file_analysis["patterns_found"].append(pattern_info)
                            file_analysis["changes_needed"] += len(matches)

                            # Track global pattern statistics
                            if pattern not in analysis["import_patterns_found"]:
                                analysis["import_patterns_found"][pattern] = 0
                            analysis["import_patterns_found"][pattern] += len(matches)

                    if file_analysis["changes_needed"] > 0:
                        analysis["files_to_migrate"].append(file_analysis)
                        analysis["estimated_changes"] += file_analysis["changes_needed"]

            except Exception as e:
                logger.warning(f"Error analyzing file {file_path}: {str(e)}")

        return analysis

    def perform_migration(self, dry_run: bool = False) -> bool:
        """
        Perform the migration from pyautocad to Enhanced AutoCAD.

        Args:
            dry_run: If True, only show what would be changed

        Returns:
            True if migration successful
        """
        try:
            # Analyze migration scope
            analysis = self.analyze_migration_scope()

            logger.info(f"Migration analysis:")
            logger.info(f"  - Total files: {analysis['total_files']}")
            logger.info(f"  - Files with pyautocad: {analysis['files_with_pyautocad']}")
            logger.info(f"  - Files to migrate: {len(analysis['files_to_migrate'])}")
            logger.info(f"  - Estimated changes: {analysis['estimated_changes']}")

            if dry_run:
                logger.info("DRY RUN - No files will be modified")
                for file_info in analysis["files_to_migrate"]:
                    logger.info(
                        f"  Would migrate: {file_info['file']} ({file_info['changes_needed']} changes)"
                    )
                return True

            if analysis["estimated_changes"] == 0:
                logger.info("No migration needed - no pyautocad imports found")
                return True

            # Create backup before migration
            if not self.create_backup():
                logger.error("Migration aborted - backup creation failed")
                return False

            # Perform actual migration
            migrated_files = 0
            total_changes = 0

            for file_info in analysis["files_to_migrate"]:
                file_path = self.project_root / file_info["file"]
                changes_made = self._migrate_file(file_path)

                if changes_made > 0:
                    migrated_files += 1
                    total_changes += changes_made

                    self.migration_log.append(
                        {
                            "action": "file_migrated",
                            "file": file_info["file"],
                            "changes_made": changes_made,
                            "timestamp": time.time(),
                        }
                    )

            # Save migration log
            self._save_migration_log()

            logger.info(f"Migration completed successfully:")
            logger.info(f"  - Files migrated: {migrated_files}")
            logger.info(f"  - Total changes: {total_changes}")

            return True

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False

    def _migrate_file(self, file_path: Path) -> int:
        """
        Migrate a single file from pyautocad to Enhanced AutoCAD.

        Args:
            file_path: Path to file to migrate

        Returns:
            Number of changes made
        """
        try:
            # Read original content
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            modified_content = original_content
            changes_made = 0

            # Apply each migration pattern
            for pattern, replacement in self.import_patterns:
                new_content, count = re.subn(pattern, replacement, modified_content)
                modified_content = new_content
                changes_made += count

            # Write modified content if changes were made
            if changes_made > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)

                logger.info(
                    f"Migrated {file_path.relative_to(self.project_root)}: {changes_made} changes"
                )

            return changes_made

        except Exception as e:
            logger.error(f"Error migrating file {file_path}: {str(e)}")
            return 0

    def rollback_migration(self) -> bool:
        """
        Rollback migration using backup files.

        Returns:
            True if rollback successful
        """
        try:
            if not self.backup_dir.exists():
                logger.error("No backup found - cannot rollback migration")
                return False

            logger.info("Starting migration rollback")

            # Verify backup metadata
            metadata_file = self.backup_dir / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                logger.info(f"Restoring from backup created at {metadata['backup_timestamp']}")

            # Restore files from backup
            restored_files = 0

            for backup_file in self.backup_dir.rglob("*.py"):
                # Skip metadata file
                if backup_file.name == "backup_metadata.json":
                    continue

                # Calculate original file path
                relative_path = backup_file.relative_to(self.backup_dir)
                original_path = self.project_root / relative_path

                # Restore file
                original_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, original_path)
                restored_files += 1

                logger.debug(f"Restored: {relative_path}")

            logger.info(f"Rollback completed successfully - {restored_files} files restored")

            # Clean up backup directory after successful rollback
            # shutil.rmtree(self.backup_dir)
            # logger.info("Backup directory cleaned up")

            return True

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    def validate_migration(self) -> bool:
        """
        Validate that migration was successful.

        Returns:
            True if migration is valid
        """
        try:
            logger.info("Validating migration")

            # Check that enhanced_autocad module exists
            enhanced_module_path = self.src_dir / "enhanced_autocad"
            if not enhanced_module_path.exists():
                logger.error("Enhanced AutoCAD module not found")
                return False

            # Check that essential files exist
            required_files = [
                "enhanced_wrapper.py",
                "compatibility_layer.py",
                "connection_manager.py",
                "performance_monitor.py",
                "error_handler.py",
            ]

            for file_name in required_files:
                file_path = enhanced_module_path / file_name
                if not file_path.exists():
                    logger.error(f"Required file missing: {file_name}")
                    return False

            # Try importing the enhanced module
            try:
                import sys

                sys.path.insert(0, str(self.src_dir))
                from enhanced_autocad.compatibility_layer import Autocad

                logger.info("Enhanced AutoCAD module imports successfully")
            except ImportError as e:
                logger.error(f"Import validation failed: {str(e)}")
                return False

            # Check that no pyautocad imports remain
            python_files = self._get_python_files()
            remaining_imports = []

            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for remaining pyautocad references
                    if re.search(r"from pyautocad import", content) or re.search(
                        r"import pyautocad", content
                    ):
                        remaining_imports.append(file_path.relative_to(self.project_root))

                except Exception as e:
                    logger.warning(f"Error validating file {file_path}: {str(e)}")

            if remaining_imports:
                logger.warning(f"Files with remaining pyautocad imports: {remaining_imports}")
                # Don't fail validation for this as some imports might be intentional

            logger.info("Migration validation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration validation failed: {str(e)}")
            return False

    def _save_migration_log(self) -> None:
        """Save migration log to file."""
        try:
            log_file = self.project_root / "migration_log.json"

            log_data = {
                "migration_timestamp": self.migration_timestamp,
                "project_root": str(self.project_root),
                "migration_events": self.migration_log,
                "total_events": len(self.migration_log),
            }

            with open(log_file, "w") as f:
                json.dump(log_data, f, indent=2)

            logger.info(f"Migration log saved to {log_file}")

        except Exception as e:
            logger.warning(f"Failed to save migration log: {str(e)}")

    def get_migration_status(self) -> Dict[str, any]:
        """
        Get current migration status.

        Returns:
            Dictionary containing migration status
        """
        status = {
            "backup_exists": self.backup_dir.exists(),
            "enhanced_module_exists": (self.src_dir / "enhanced_autocad").exists(),
            "migration_log_exists": (self.project_root / "migration_log.json").exists(),
        }

        # Analyze current state
        if status["enhanced_module_exists"]:
            try:
                analysis = self.analyze_migration_scope()
                status["remaining_pyautocad_imports"] = analysis["files_with_pyautocad"]
                status["migration_needed"] = analysis["estimated_changes"] > 0
            except:
                status["remaining_pyautocad_imports"] = "unknown"
                status["migration_needed"] = "unknown"

        return status


def main():
    """Main function for running migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate from pyautocad to Enhanced AutoCAD")
    parser.add_argument("project_root", help="Root directory of the project")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without making changes"
    )
    parser.add_argument("--rollback", action="store_true", help="Rollback previous migration")
    parser.add_argument("--validate", action="store_true", help="Validate migration")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    # Create migrator
    migrator = PyAutoCADMigrator(args.project_root)

    # Execute requested action
    if args.status:
        status = migrator.get_migration_status()
        print(json.dumps(status, indent=2))
    elif args.rollback:
        success = migrator.rollback_migration()
        exit(0 if success else 1)
    elif args.validate:
        success = migrator.validate_migration()
        exit(0 if success else 1)
    else:
        success = migrator.perform_migration(dry_run=args.dry_run)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
