from pathlib import Path
from urllib.request import urlopen
root=Path(__file__).resolve().parent;folder=root/"assets"/"fonts";folder.mkdir(parents=True,exist_ok=True);target=folder/"Nunito-Bold.ttf"
if target.exists() and target.stat().st_size>10000:print("Nunito font already installed")
else:
 try:
  with urlopen("https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf",timeout=25) as r:data=r.read()
  if len(data)<10000:raise ValueError("downloaded font is too small")
  target.write_bytes(data);print(f"Installed Nunito font: {target}")
 except Exception as e:print(f"Nunito download unavailable ({e}); using system DejaVu Sans fallback.")
