from pathlib import Path
import ast
source=Path(__file__).parents[1]/"worker_manager.py"
text=source.read_text(encoding="utf-8")
tree=ast.parse(text)
imports={(n.module,a.name) for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) for a in n.names}
assert ("runtime_events","emit_ticket_event") in imports
assert "emit_ticket_event(" in text
print("PASS test_worker_runtime_event_import")
