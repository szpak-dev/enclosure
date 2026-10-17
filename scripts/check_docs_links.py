import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class MarkdownLink:
    source: Path
    target: str


@dataclass(frozen=True)
class DocumentationCrawler:
    root: Path

    link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    heading_pattern = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
    explicit_anchor_pattern = re.compile(r"^\(([^)]+)\)=\s*$")

    def crawl(self, entrance: Path) -> tuple[Path, ...]:
        pending = deque((entrance.resolve(),))
        visited: set[Path] = set()
        failures: list[str] = []
        while pending:
            source = pending.popleft()
            if source in visited:
                continue
            visited.add(source)
            for link in self.links(source):
                target = self.resolve(link)
                if target is None:
                    continue
                path, fragment = target
                if not path.is_file():
                    failures.append(f"{self.relative(source)}: missing target {link.target!r}")
                    continue
                if fragment and fragment not in self.anchors(path):
                    failures.append(f"{self.relative(source)}: missing fragment #{fragment} in {self.relative(path)}")
                if path.suffix.lower() == ".md" and path not in visited:
                    pending.append(path)
        expected = {path.resolve() for path in (self.root / "docs").rglob("*.md")}
        unreachable = sorted(expected - visited)
        failures.extend(f"README.md: unreachable documentation page {self.relative(path)}" for path in unreachable)
        if failures:
            raise ValueError("\n".join(failures))
        return tuple(sorted(visited))

    def links(self, source: Path) -> tuple[MarkdownLink, ...]:
        content = source.read_text(encoding="utf-8")
        return tuple(
            MarkdownLink(source=source, target=self.destination(match.group(1)))
            for match in self.link_pattern.finditer(content)
        )

    def destination(self, value: str) -> str:
        stripped = value.strip()
        if stripped.startswith("<") and ">" in stripped:
            return stripped[1 : stripped.index(">")]
        return stripped.split(maxsplit=1)[0]

    def resolve(self, link: MarkdownLink) -> tuple[Path, str] | None:
        parsed = urlsplit(link.target)
        if parsed.scheme or parsed.netloc:
            return None
        decoded_path = unquote(parsed.path)
        path = link.source if not decoded_path else self.local_path(link.source.parent, decoded_path)
        return path.resolve(), unquote(parsed.fragment)

    def local_path(self, parent: Path, value: str) -> Path:
        candidate = self.root / value.lstrip("/") if value.startswith("/") else parent / value
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Documentation link escapes the repository: {value!r}")
        return resolved

    def anchors(self, source: Path) -> frozenset[str]:
        anchors: set[str] = set()
        counts: dict[str, int] = {}
        for line in source.read_text(encoding="utf-8").splitlines():
            if explicit := self.explicit_anchor_pattern.fullmatch(line.strip()):
                anchors.add(explicit.group(1))
            if heading := self.heading_pattern.fullmatch(line):
                base = self.slug(heading.group(1))
                count = counts.get(base, 0)
                counts[base] = count + 1
                anchors.add(base if count == 0 else f"{base}-{count}")
        return frozenset(anchors)

    def slug(self, heading: str) -> str:
        without_markup = re.sub(r"[`*_~]", "", heading).lower()
        without_punctuation = re.sub(r"[^\w\s-]", "", without_markup)
        return re.sub(r"-+", "-", re.sub(r"\s+", "-", without_punctuation)).strip("-")

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()


@dataclass(frozen=True)
class DocumentationCheckCommand:
    root: Path

    def run(self) -> int:
        try:
            pages = DocumentationCrawler(self.root).crawl(self.root / "README.md")
        except (OSError, UnicodeError, ValueError) as error:
            print(error, file=sys.stderr)
            return 1
        print(f"Documentation graph: {len(pages)} Markdown pages reachable from README.md.")
        return 0


if __name__ == "__main__":
    raise SystemExit(DocumentationCheckCommand(Path(__file__).resolve().parents[1]).run())
