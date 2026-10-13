from __future__ import annotations
import json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load_config(path=None):
 import yaml
 with open(path or ROOT/"config.yaml",encoding="utf-8") as f:return yaml.safe_load(f) or {}
def require_binary(name):
 p=shutil.which(name)
 if not p:raise RuntimeError(f"Required program not found: {name}. Install FFmpeg and ensure {name} is on PATH.")
 return p
def run(cmd):
 p=subprocess.run([str(x) for x in cmd],text=True,capture_output=True)
 if p.returncode:raise RuntimeError(f"Command failed: {' '.join(map(str,cmd[:7]))}\n{(p.stderr or p.stdout)[-4500:]}")
def ensure_dirs(*paths):
 for p in paths:Path(p).mkdir(parents=True,exist_ok=True)
def ffprobe(path):
 require_binary("ffprobe"); p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(f"ffprobe failed for {path}: {p.stderr[-1000:]}")
 return json.loads(p.stdout)
