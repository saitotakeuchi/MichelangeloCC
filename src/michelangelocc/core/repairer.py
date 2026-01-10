"""
Mesh repair module for fixing common mesh issues.

Uses PyMeshFix and trimesh utilities to automatically repair
mesh problems that could cause 3D printing failures.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum
from pathlib import Path
import tempfile

import trimesh
import numpy as np

try:
    import pymeshfix
    PYMESHFIX_AVAILABLE = True
except ImportError:
    PYMESHFIX_AVAILABLE = False


class RepairAction(Enum):
    """Types of repair actions that can be performed."""

    FILL_HOLES = "fill_holes"
    FIX_NORMALS = "fix_normals"
    REMOVE_DUPLICATES = "remove_duplicates"
    REMOVE_DEGENERATE = "remove_degenerate"
    MERGE_VERTICES = "merge_vertices"
    PYMESHFIX_REPAIR = "pymeshfix_repair"


@dataclass
class RepairLog:
    """Log entry for a repair action."""

    action: RepairAction
    description: str
    affected_elements: int
    success: bool


@dataclass
class RepairResult:
    """Result of mesh repair operation."""

    mesh: trimesh.Trimesh
    was_modified: bool
    log: List[RepairLog] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable repair summary."""
        lines = ["=== Mesh Repair Summary ==="]

        if not self.was_modified:
            lines.append("No repairs needed - mesh was already valid.")
            return "\n".join(lines)

        lines.append(f"Repairs performed: {len(self.log)}")
        lines.append("")

        for entry in self.log:
            status = "OK" if entry.success else "FAILED"
            lines.append(f"  [{status}] {entry.action.value}: {entry.description}")
            if entry.affected_elements > 0:
                lines.append(f"       Affected: {entry.affected_elements} elements")

        return "\n".join(lines)


class MeshRepairer:
    """
    Automatic mesh repair using PyMeshFix and trimesh utilities.

    Repair pipeline:
    1. Remove duplicate vertices
    2. Remove degenerate faces
    3. Fix face normals (consistent winding)
    4. Fill holes
    5. Fix with PyMeshFix (optional, for severe issues)
    """

    def __init__(
        self,
        max_hole_size: int = 1000,
        merge_threshold: float = 1e-8,
    ):
        """
        Initialize the repairer.

        Args:
            max_hole_size: Maximum hole size (in edges) to fill
            merge_threshold: Distance threshold for merging vertices
        """
        self.max_hole_size = max_hole_size
        self.merge_threshold = merge_threshold

    def repair(
        self,
        mesh: trimesh.Trimesh,
        actions: Optional[List[RepairAction]] = None,
    ) -> RepairResult:
        """
        Perform mesh repair with specified or all actions.

        If actions is None, performs all repairs in recommended order.

        Args:
            mesh: trimesh.Trimesh to repair
            actions: Optional list of specific repair actions

        Returns:
            RepairResult with repaired mesh and log
        """
        # Work on a copy
        mesh = mesh.copy()
        log: List[RepairLog] = []
        was_modified = False

        if actions is None:
            actions = [
                RepairAction.MERGE_VERTICES,
                RepairAction.REMOVE_DEGENERATE,
                RepairAction.FIX_NORMALS,
                RepairAction.FILL_HOLES,
            ]

        for action in actions:
            result_mesh, entry = self._perform_action(mesh, action)
            if entry.success and entry.affected_elements > 0:
                mesh = result_mesh
                was_modified = True
            log.append(entry)

        return RepairResult(mesh=mesh, was_modified=was_modified, log=log)

    def repair_aggressive(self, mesh: trimesh.Trimesh) -> RepairResult:
        """
        Use PyMeshFix for comprehensive repair.

        Best for severely damaged meshes. More aggressive but very effective.

        Args:
            mesh: trimesh.Trimesh to repair

        Returns:
            RepairResult with repaired mesh
        """
        if not PYMESHFIX_AVAILABLE:
            return RepairResult(
                mesh=mesh,
                was_modified=False,
                log=[
                    RepairLog(
                        action=RepairAction.PYMESHFIX_REPAIR,
                        description="PyMeshFix not available (install with pip install pymeshfix)",
                        affected_elements=0,
                        success=False,
                    )
                ],
            )

        mesh_copy = mesh.copy()
        log: List[RepairLog] = []

        try:
            # Convert to PyMeshFix format
            meshfix = pymeshfix.MeshFix(mesh_copy.vertices, mesh_copy.faces)

            # Repair
            meshfix.repair(verbose=False)

            # Get repaired mesh
            repaired_vertices = meshfix.v
            repaired_faces = meshfix.f

            # Create new trimesh
            repaired_mesh = trimesh.Trimesh(
                vertices=repaired_vertices,
                faces=repaired_faces,
            )

            # Calculate changes
            vertex_diff = abs(len(repaired_vertices) - len(mesh_copy.vertices))
            face_diff = abs(len(repaired_faces) - len(mesh_copy.faces))

            log.append(
                RepairLog(
                    action=RepairAction.PYMESHFIX_REPAIR,
                    description="PyMeshFix comprehensive repair",
                    affected_elements=vertex_diff + face_diff,
                    success=True,
                )
            )

            return RepairResult(
                mesh=repaired_mesh,
                was_modified=True,
                log=log,
            )

        except Exception as e:
            log.append(
                RepairLog(
                    action=RepairAction.PYMESHFIX_REPAIR,
                    description=f"PyMeshFix repair failed: {str(e)}",
                    affected_elements=0,
                    success=False,
                )
            )
            return RepairResult(mesh=mesh, was_modified=False, log=log)

    def _perform_action(
        self, mesh: trimesh.Trimesh, action: RepairAction
    ) -> tuple[trimesh.Trimesh, RepairLog]:
        """Perform a single repair action."""
        handlers: dict[RepairAction, Callable] = {
            RepairAction.MERGE_VERTICES: self._merge_vertices,
            RepairAction.REMOVE_DEGENERATE: self._remove_degenerate_faces,
            RepairAction.FIX_NORMALS: self._fix_normals,
            RepairAction.FILL_HOLES: self._fill_holes,
            RepairAction.PYMESHFIX_REPAIR: lambda m: self.repair_aggressive(m),
        }

        if action in handlers:
            return handlers[action](mesh)

        return mesh, RepairLog(
            action=action,
            description=f"Unknown action: {action}",
            affected_elements=0,
            success=False,
        )

    def _merge_vertices(
        self, mesh: trimesh.Trimesh
    ) -> tuple[trimesh.Trimesh, RepairLog]:
        """Merge vertices within merge threshold distance."""
        original_count = len(mesh.vertices)

        # Use trimesh's merge_vertices
        mesh.merge_vertices(merge_tex=True, merge_norm=True)

        new_count = len(mesh.vertices)
        merged = original_count - new_count

        return mesh, RepairLog(
            action=RepairAction.MERGE_VERTICES,
            description=f"Merged {merged} duplicate vertices",
            affected_elements=merged,
            success=True,
        )

    def _remove_degenerate_faces(
        self, mesh: trimesh.Trimesh
    ) -> tuple[trimesh.Trimesh, RepairLog]:
        """Remove zero-area and invalid triangles."""
        original_count = len(mesh.faces)

        # Remove degenerate faces
        mesh.remove_degenerate_faces()
        # Also remove unreferenced vertices
        mesh.remove_unreferenced_vertices()

        new_count = len(mesh.faces)
        removed = original_count - new_count

        return mesh, RepairLog(
            action=RepairAction.REMOVE_DEGENERATE,
            description=f"Removed {removed} degenerate faces",
            affected_elements=removed,
            success=True,
        )

    def _fix_normals(
        self, mesh: trimesh.Trimesh
    ) -> tuple[trimesh.Trimesh, RepairLog]:
        """Fix face normals for consistent outward orientation."""
        try:
            # Fix winding
            mesh.fix_normals()

            return mesh, RepairLog(
                action=RepairAction.FIX_NORMALS,
                description="Fixed face normal orientation",
                affected_elements=len(mesh.faces),
                success=True,
            )
        except Exception as e:
            return mesh, RepairLog(
                action=RepairAction.FIX_NORMALS,
                description=f"Failed to fix normals: {str(e)}",
                affected_elements=0,
                success=False,
            )

    def _fill_holes(
        self, mesh: trimesh.Trimesh
    ) -> tuple[trimesh.Trimesh, RepairLog]:
        """Fill holes in the mesh."""
        try:
            # Get initial watertight status
            was_watertight = mesh.is_watertight

            if was_watertight:
                return mesh, RepairLog(
                    action=RepairAction.FILL_HOLES,
                    description="Mesh already watertight, no holes to fill",
                    affected_elements=0,
                    success=True,
                )

            # trimesh's fill_holes method
            mesh.fill_holes()

            is_now_watertight = mesh.is_watertight

            return mesh, RepairLog(
                action=RepairAction.FILL_HOLES,
                description=f"Filled holes (now watertight: {is_now_watertight})",
                affected_elements=1 if is_now_watertight else 0,
                success=is_now_watertight,
            )
        except Exception as e:
            return mesh, RepairLog(
                action=RepairAction.FILL_HOLES,
                description=f"Failed to fill holes: {str(e)}",
                affected_elements=0,
                success=False,
            )

    def repair_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        aggressive: bool = False,
    ) -> RepairResult:
        """
        Repair a mesh from a file.

        Args:
            input_path: Path to input STL file
            output_path: Optional path to save repaired mesh
            aggressive: Use PyMeshFix for aggressive repair

        Returns:
            RepairResult
        """
        mesh = trimesh.load(str(input_path))

        if aggressive:
            result = self.repair_aggressive(mesh)
        else:
            result = self.repair(mesh)

        if output_path and result.was_modified:
            result.mesh.export(str(output_path))

        return result
