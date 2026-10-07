"""Build the self-contained HTML. Use --check in CI to detect stale output."""
from __future__ import annotations
import argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def render() -> str:
    text = (ROOT / "index.template.html").read_text(encoding="utf-8")
    for marker, name in (("/*APP_CSS*/", "app.css"), ("/*APP_JS*/", "app.js")):
        if text.count(marker) != 1:
            raise ValueError(f"Expected exactly one {marker} in index.template.html")
        text = text.replace(marker, (ROOT / name).read_text(encoding="utf-8"))
    return text

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Orellana Atlas")
    parser.add_argument("--check", action="store_true", help="Fail if index.html is out of date")
    args = parser.parse_args()
    text, output = render(), ROOT / "index.html"
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != text:
            raise SystemExit("index.html desactualizado. Ejecuta: python build.py")
        print("OK: index.html coincide con sus fuentes")
    else:
        output.write_text(text, encoding="utf-8")
        print("index.html actualizado")

if __name__ == "__main__":
    main()
