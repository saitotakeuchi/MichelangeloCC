"""Core modules for model generation, validation, repair, and export."""

from michelangelocc.core.modeler import MichelangeloModel, ModelMetadata
from michelangelocc.core.validator import MeshValidator, ValidationResult
from michelangelocc.core.repairer import MeshRepairer, RepairResult
from michelangelocc.core.exporter import STLExporter, ExportSettings, ExportResult

__all__ = [
    "MichelangeloModel",
    "ModelMetadata",
    "MeshValidator",
    "ValidationResult",
    "MeshRepairer",
    "RepairResult",
    "STLExporter",
    "ExportSettings",
    "ExportResult",
]
