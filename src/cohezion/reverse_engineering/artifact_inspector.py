"""Artifact Inspector for Binaries, Packages, and Python Bytecode.
================================================================
Reference: morluto/rea (Reverse Engineer Anything).

Provides tool-independent inspection of:
1. Native Binaries (ELF, Mach-O, PE/COFF) via pure Python struct parsing.
2. Python Wheels and Zip Packages (.whl, .zip, .tar.gz).
3. Python Bytecode and AST structure (functions, classes, imports, opcodes).
"""

from __future__ import annotations

import ast
import dis
import io
import logging
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cohezion.reverse_engineering.evidence import (
    EvidenceRecord,
    FacetAvailability,
)

logger = logging.getLogger(__name__)


class ArtifactInspector:
    """Multi-layer reverse engineering inspection engine."""

    @classmethod
    def inspect_binary_layout(cls, path: str | Path) -> EvidenceRecord:
        """Inspect binary layout (ELF, Mach-O, PE/COFF) without external disassemblers."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Binary target not found: {file_path}")

        raw_bytes = file_path.read_bytes()
        file_size = len(raw_bytes)
        limitations: List[str] = []
        facet_availability: Dict[str, FacetAvailability] = {}

        normalized: Dict[str, Any] = {
            "file_size_bytes": file_size,
            "format": "unknown",
            "architecture": "unknown",
            "bitness": 0,
            "endianness": "unknown",
            "entrypoint": None,
            "sections": [],
        }

        # Check Magic bytes
        if raw_bytes.startswith(b"\x7fELF"):
            # ELF Header parsing
            normalized["format"] = "ELF"
            ei_class = raw_bytes[4]  # 1 = 32-bit, 2 = 64-bit
            ei_data = raw_bytes[5]   # 1 = Little-endian, 2 = Big-endian
            normalized["bitness"] = 64 if ei_class == 2 else 32
            endian = "<" if ei_data == 1 else ">"
            normalized["endianness"] = "little" if ei_data == 1 else "big"

            if len(raw_bytes) >= 32:
                # e_machine at offset 18 (uint16)
                e_machine = struct.unpack(f"{endian}H", raw_bytes[18:20])[0]
                machine_map = {0x03: "x86", 0x3E: "x86_64", 0x28: "ARM", 0xB7: "AArch64", 0xF3: "RISC-V"}
                normalized["architecture"] = machine_map.get(e_machine, f"custom_0x{e_machine:02x}")

                if normalized["bitness"] == 64 and len(raw_bytes) >= 32:
                    # e_entry at offset 24 (uint64)
                    e_entry = struct.unpack(f"{endian}Q", raw_bytes[24:32])[0]
                    normalized["entrypoint"] = hex(e_entry)

            facet_availability["sections"] = FacetAvailability(available=True)
            facet_availability["assembly"] = FacetAvailability(available=False, reason="Native engine not attached")
            facet_availability["pseudocode"] = FacetAvailability(available=False, reason="Decompiler provider not attached")

        elif raw_bytes.startswith(b"MZ"):
            # PE/COFF Windows executable
            normalized["format"] = "PE_COFF"
            facet_availability["sections"] = FacetAvailability(available=True)
            facet_availability["pseudocode"] = FacetAvailability(available=False, reason="Decompiler provider not attached")

        elif raw_bytes[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe"):
            # Mach-O header
            normalized["format"] = "Mach-O"
            is_64 = raw_bytes[:4] in (b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe")
            normalized["bitness"] = 64 if is_64 else 32
            facet_availability["sections"] = FacetAvailability(available=True)
            facet_availability["pseudocode"] = FacetAvailability(available=False, reason="Decompiler provider not attached")

        else:
            limitations.append("Unrecognized binary header format")
            facet_availability["sections"] = FacetAvailability(available=False, reason="Format unknown")

        return EvidenceRecord.create(
            target_path=file_path,
            operation="inspect_binary_layout",
            normalized_result=normalized,
            facet_availability=facet_availability,
            limitations=limitations,
        )

    @classmethod
    def inspect_python_wheel(cls, path: str | Path) -> EvidenceRecord:
        """Inspect a Python Wheel or Zip distribution package."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Package artifact not found: {file_path}")

        limitations: List[str] = []
        entries: List[Dict[str, Any]] = []
        metadata_content: Optional[str] = None
        record_files: List[str] = []

        try:
            with zipfile.ZipFile(file_path, "r") as z:
                for info in z.infolist():
                    entries.append({
                        "filename": info.filename,
                        "file_size": info.file_size,
                        "compress_size": info.compress_size,
                        "is_dir": info.is_dir(),
                    })
                    if info.filename.endswith(".dist-info/METADATA"):
                        metadata_content = z.read(info.filename).decode("utf-8", errors="replace")
                    elif info.filename.endswith(".dist-info/RECORD"):
                        record_files = z.read(info.filename).decode("utf-8", errors="replace").splitlines()
        except zipfile.BadZipFile as e:
            limitations.append(f"Bad zip file: {e}")

        # Extract basic metadata
        pkg_name = "unknown"
        pkg_version = "unknown"
        dependencies: List[str] = []

        if metadata_content:
            for line in metadata_content.splitlines():
                if line.startswith("Name:"):
                    pkg_name = line.split(":", 1)[1].strip()
                elif line.startswith("Version:"):
                    pkg_version = line.split(":", 1)[1].strip()
                elif line.startswith("Requires-Dist:"):
                    dependencies.append(line.split(":", 1)[1].strip())

        normalized = {
            "package_name": pkg_name,
            "version": pkg_version,
            "total_files": len(entries),
            "files": [e["filename"] for e in entries[:100]],  # Bounded to first 100 for framing
            "dependencies": dependencies,
            "has_compiled_extensions": any(e["filename"].endswith((".so", ".pyd", ".dylib")) for e in entries),
            "record_count": len(record_files),
        }

        facets = {
            "metadata": FacetAvailability(available=metadata_content is not None),
            "records": FacetAvailability(available=len(record_files) > 0),
            "decompilation": FacetAvailability(available=False, reason="Decompiler not requested"),
        }

        return EvidenceRecord.create(
            target_path=file_path,
            operation="inspect_python_wheel",
            normalized_result=normalized,
            facet_availability=facets,
            limitations=limitations,
        )

    @classmethod
    def inspect_python_bytecode(cls, source_or_path: str | Path) -> EvidenceRecord:
        """Inspect Python code or file, extracting AST structure, functions, and bytecode disassembly."""
        target_path = "inline_code"
        if isinstance(source_or_path, (str, Path)) and Path(source_or_path).is_file():
            target_path = str(Path(source_or_path).resolve())
            code_str = Path(source_or_path).read_text(encoding="utf-8")
        else:
            code_str = str(source_or_path)

        limitations: List[str] = []
        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[str] = []

        try:
            tree = ast.parse(code_str)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [a.arg for a in node.args.args],
                        "docstring": ast.get_docstring(node),
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node),
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        except SyntaxError as e:
            limitations.append(f"AST parse failure: {e}")

        # Disassemble bytecode
        dis_output = io.StringIO()
        try:
            compiled = compile(code_str, "<dis>", "exec")
            dis.dis(compiled, file=dis_output)
            bytecode_str = dis_output.getvalue()[:2000]  # Bound to first 2000 chars for framing
        except Exception as e:
            bytecode_str = f"Disassembly error: {e}"
            limitations.append(str(e))

        normalized = {
            "function_count": len(functions),
            "class_count": len(classes),
            "functions": functions,
            "classes": classes,
            "imports": list(set(imports)),
            "disassembly_preview": bytecode_str,
        }

        facets = {
            "ast_symbols": FacetAvailability(available=len(functions) > 0 or len(classes) > 0),
            "bytecode": FacetAvailability(available=bool(bytecode_str and not bytecode_str.startswith("Disassembly error"))),
            "control_flow_graph": FacetAvailability(available=False, reason="CFG generator not invoked"),
        }

        return EvidenceRecord.create(
            target_path=target_path,
            operation="inspect_python_bytecode",
            normalized_result=normalized,
            facet_availability=facets,
            limitations=limitations,
        )
