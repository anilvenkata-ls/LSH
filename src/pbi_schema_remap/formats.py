"""Apply a :class:`Remapper` to Power BI files (PBIP/TMDL folders, model.bim, .pbit)."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .mcode import Remapper

_UTF16_BOM = b"\xff\xfe"


class UnsupportedFileError(ValueError):
    pass


def default_output_path(src: Path) -> Path:
    if src.is_dir():
        return src.with_name(f"{src.name}_redshift")
    return src.with_name(f"{src.stem}_redshift{src.suffix}")


def remap_path(src: Path, dst: Path | None, remapper: Remapper, dry_run: bool = False) -> Path:
    """Write a remapped copy of ``src`` to ``dst`` and return ``dst``; ``src`` is never modified."""
    src = src.resolve()
    if src.suffix.lower() == ".pbip":
        src = src.parent
    dst = (dst or default_output_path(src)).resolve()
    if dst == src:
        raise ValueError("output path must differ from the input path")

    suffix = src.suffix.lower()
    if src.is_dir():
        _remap_folder(src, dst, remapper, dry_run)
    elif suffix == ".pbit":
        _remap_pbit(src, dst, remapper, dry_run)
    elif suffix in {".bim", ".json"}:
        text = src.read_text(encoding="utf-8-sig")
        new = _remap_bim_text(text, remapper, src.name)
        if not dry_run:
            dst.write_text(new, encoding="utf-8")
    elif suffix == ".tmdl":
        new = remapper.rewrite_m(src.read_text(encoding="utf-8-sig"), src.name)
        if not dry_run:
            dst.write_text(new, encoding="utf-8")
    elif suffix == ".pbix":
        raise UnsupportedFileError(
            "A .pbix stores its model in a compressed binary format (XPress9) that cannot be "
            "edited safely. In Power BI Desktop use File > Save as > Power BI project (.pbip), "
            "or File > Export > Power BI template (.pbit), then run this tool on that output."
        )
    else:
        raise UnsupportedFileError(f"unsupported input: {src}")
    return dst


def _remap_folder(src: Path, dst: Path, remapper: Remapper, dry_run: bool) -> None:
    files = sorted(src.rglob("*.tmdl")) + sorted(src.rglob("model.bim"))
    if not files:
        raise UnsupportedFileError(
            f"no semantic model (*.tmdl or model.bim) found under {src}"
        )
    if not dry_run:
        if dst.exists():
            raise FileExistsError(f"output folder already exists: {dst}")
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("cache.abf"))
    for path in files:
        rel = path.relative_to(src)
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".bim":
            new = _remap_bim_text(text, remapper, str(rel))
        else:
            new = remapper.rewrite_m(text, str(rel))
        if not dry_run and new != text:
            (dst / rel).write_text(new, encoding="utf-8")


def _remap_pbit(src: Path, dst: Path, remapper: Remapper, dry_run: bool) -> None:
    with zipfile.ZipFile(src) as zin:
        if "DataModelSchema" not in zin.namelist():
            raise UnsupportedFileError(f"{src.name} has no DataModelSchema entry")
        raw = zin.read("DataModelSchema")
        bom = raw.startswith(_UTF16_BOM)
        text = raw.decode("utf-16-le").lstrip("\ufeff")
        new = _remap_bim_text(text, remapper, "DataModelSchema")
        if dry_run:
            return
        payload = (_UTF16_BOM if bom else b"") + new.encode("utf-16-le")
        with zipfile.ZipFile(dst, "w") as zout:
            for info in zin.infolist():
                data = payload if info.filename == "DataModelSchema" else zin.read(info)
                zout.writestr(info, data, compress_type=info.compress_type)


def _remap_bim_text(text: str, remapper: Remapper, origin: str) -> str:
    doc = json.loads(text)
    model = doc.get("model", doc)
    for table in model.get("tables", []):
        for partition in table.get("partitions", []):
            source = partition.get("source") or {}
            where = f"{origin}: table '{table.get('name')}' partition '{partition.get('name')}'"
            if "expression" in source:
                source["expression"] = _map_lines(source["expression"], remapper.rewrite_m, where)
            elif "query" in source:
                source["query"] = _map_lines(source["query"], remapper.rewrite_sql, where)
    for expr in model.get("expressions", []):
        if "expression" in expr:
            where = f"{origin}: expression '{expr.get('name')}'"
            expr["expression"] = _map_lines(expr["expression"], remapper.rewrite_m, where)
    return json.dumps(doc, indent=2, ensure_ascii=False)


def _map_lines(value: Any, fn, where: str) -> Any:
    """model.bim stores long expressions either as one string or as a list of lines."""
    if isinstance(value, list):
        return fn("\n".join(value), where).split("\n")
    return fn(value, where)
