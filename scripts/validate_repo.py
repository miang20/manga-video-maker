from pathlib import Path
import py_compile
import yaml

root = Path(".")
python_files = sorted(p for p in root.rglob("*.py") if ".git" not in p.parts and "__pycache__" not in p.parts)
for path in python_files:
    py_compile.compile(str(path), doraise=True)
print(f"PY_COMPILE=PASS; {len(python_files)} Python files")
yaml_files = sorted(set(root.rglob("*.yml")) | set(root.rglob("*.yaml")))
yaml_files = [p for p in yaml_files if ".git" not in p.parts]
for path in yaml_files:
    with path.open(encoding="utf-8") as stream:
        yaml.safe_load(stream)
print(f"YAML_PARSE=PASS; {len(yaml_files)} YAML files")
config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
if not isinstance(config, dict):
    raise SystemExit("config.yaml must be a YAML mapping")
for path in (Path(".github/workflows/render.yml"), Path(".github/workflows/acceptance.yml")):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        raise SystemExit(f"Invalid workflow: {path}")
print("WORKFLOW_VALIDATION=PASS; render.yml and acceptance.yml")
