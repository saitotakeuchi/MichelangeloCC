"""
MichelangeloCC - Claude Code-powered 3D model generator for STL files.

Generate 3D printable models from natural language descriptions using
build123d CAD operations.
"""

from michelangelocc.core.modeler import MichelangeloModel, ModelMetadata

__version__ = "0.1.0"
__all__ = ["MichelangeloModel", "ModelMetadata", "__version__"]
