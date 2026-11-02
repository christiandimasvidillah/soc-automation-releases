from __future__ import annotations

import ast
from pathlib import Path

project = Path(__file__).resolve().parents[1]
source = (project / "main.py").read_text(encoding="utf-8")
tree = ast.parse(source)

functions = {
    node.name
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
assert "main" in functions, "main() tidak ditemukan"
assert "cli" not in functions, "cli() tidak seharusnya menjadi entrypoint"
assert 'raise SystemExit(main())' in source, "Entrypoint harus memanggil main()"
assert 'cli()' not in source, "Referensi cli() yang tidak terdefinisi masih tersisa"
print("Main entrypoint regression test: OK")
