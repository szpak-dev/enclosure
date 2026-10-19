import html
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VersionedDocumentationBuilder:
    root: Path

    tag_pattern = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

    def run(self) -> int:
        current = self.root / "docs" / "_build" / "html"
        if not current.is_dir():
            print("Current documentation build is missing; run make docs-check first.", file=sys.stderr)
            return 1
        destination = self.root / "docs" / "_build" / "site"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(current, destination / "dev")
        releases = self.release_tags()
        for tag in releases:
            self.build_release(tag, destination / tag)
        self.write_entrance(destination, releases)
        print(f"Versioned documentation: dev and {len(releases)} release builds.")
        return 0

    def release_tags(self) -> tuple[str, ...]:
        result = self.git("tag", "--list", "v*", "--sort=version:refname")
        tags = tuple(tag for tag in result.stdout.splitlines() if self.tag_pattern.fullmatch(tag))
        return tuple(tag for tag in tags if self.has_documentation(tag))

    def has_documentation(self, tag: str) -> bool:
        for path in ("docs/conf.py", "docs/requirements.lock"):
            if self.git("cat-file", "-e", f"{tag}:{path}", check=False).returncode != 0:
                return False
        return True

    def build_release(self, tag: str, destination: Path) -> None:
        with tempfile.TemporaryDirectory(prefix="enclosure-docs-") as temporary:
            checkout = Path(temporary) / "source"
            checkout.mkdir()
            archive = Path(temporary) / "source.tar"
            self.git("archive", "--format=tar", f"--output={archive}", tag)
            with tarfile.open(archive) as source:
                source.extractall(checkout, filter="data")
            subprocess.run(
                (
                    "uv",
                    "run",
                    "--isolated",
                    "--no-project",
                    "--python",
                    "3.14",
                    "--with-requirements",
                    str(checkout / "docs" / "requirements.lock"),
                    "sphinx-build",
                    "-W",
                    "--keep-going",
                    "-E",
                    "-a",
                    "-b",
                    "html",
                    str(checkout / "docs"),
                    str(destination),
                ),
                cwd=self.root,
                check=True,
            )

    def write_entrance(self, destination: Path, releases: tuple[str, ...]) -> None:
        release_items = "\n".join(
            f'        <li><a href="{html.escape(tag)}/">{html.escape(tag)}</a></li>' for tag in reversed(releases)
        )
        release_section = release_items or "        <li>No documentation-bearing release tag yet.</li>"
        document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Enclosure documentation versions</title>
  </head>
  <body>
    <main>
      <h1>Enclosure documentation</h1>
      <p>The faster code is written, the more important it becomes to remember who said yes.</p>
      <h2>Development</h2>
      <ul>
        <li><a href="dev/">dev</a> — current <code>main</code></li>
      </ul>
      <h2>Releases</h2>
      <ul>
{release_section}
      </ul>
    </main>
  </body>
</html>
"""
        (destination / "index.html").write_text(document, encoding="utf-8")

    def git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", *arguments),
            cwd=self.root,
            check=check,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    raise SystemExit(VersionedDocumentationBuilder(Path(__file__).resolve().parents[1]).run())
