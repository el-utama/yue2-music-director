"""Offline regression checks for repository documentation and launcher coverage."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import unicodedata
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\(([^)\s]+)\)")
ROUTE = re.compile(r'^if /I "%~1"=="(--[^"]+)" goto (\w+)$', re.M)
ROUTE_ROW = re.compile(r"^\| \x60(--[^| \x60]+)\x60 \| \[[^]]+\]\(([^)\s]+)\) \|$", re.M)


def headings(text):
    result = set()
    counts = {}
    fenced = False
    for line in text.splitlines():
        if re.match(r"^\s*(?:\x60{3,}|~{3,})", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        label = re.sub(r"[\x60*_~]", "", match[1]).lower()
        slug = "".join("-" if char.isspace() else char for char in label
                       if char.isspace() or char in "-_" or unicodedata.category(char)[0] in "LN")
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        result.add(slug if n == 0 else f"{slug}-{n}")
    return result


def resolve_relative(source, link):
    stack = []
    for part in (PurePosixPath(source).parent / unquote(link)).parts:
        if part == "..":
            if not stack:
                raise ValueError("Relative link escapes checkout")
            stack.pop()
        elif part not in ("", "."):
            stack.append(part)
    return "/".join(stack)


class DocumentationTests(unittest.TestCase):
    def test_tracked_markdown_relative_links_and_heading_fragments(self):
        # Only version-controlled documents, never private local/ or results/.
        output = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"])
        tracked = set(output.decode("utf-8").split("\0")) - {""}
        documents = {path: (ROOT / path).read_text(encoding="utf-8")
                     for path in tracked if path.lower().endswith(".md")}
        self.assertIn("README.md", documents)
        self.assertIn("docs/OPERATOR_GUIDE.md", documents)
        failures = []
        for path, text in sorted(documents.items()):
            for match in LINK.finditer(text):
                link, sep, fragment = match[1].partition("#")
                if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or link.startswith("//"):
                    continue
                target = resolve_relative(path, link) if link else path
                if target not in tracked and not any(p.startswith(target + "/") for p in tracked):
                    failures.append(f"{path}: missing {match[1]}")
                    continue
                if sep and fragment and target in documents:
                    anchor = unquote(fragment)
                    if anchor not in headings(documents[target]) and f'id="{anchor}"' not in documents[target]:
                        failures.append(f"{path}: missing heading {match[1]}")
        self.assertEqual(failures, [])

    def test_primary_launcher_routes_are_documented(self):
        launcher = (ROOT / "music.cmd").read_text(encoding="utf-8")
        routes = ROUTE.findall(launcher)
        docs = ROUTE_ROW.findall((ROOT / "docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8"))
        self.assertTrue(routes)
        self.assertEqual(len(routes), len(set(flag for flag, _ in routes)))
        self.assertEqual(len(docs), len(set(flag for flag, _ in docs)))
        self.assertEqual({flag for flag, _ in routes}, {flag for flag, _ in docs})
        labels = set(re.findall(r"^:(\w+)$", launcher, re.M))
        for flag, label in routes:
            self.assertIn(label, labels, flag)
        for flag, target in docs:
            self.assertTrue((ROOT / "docs" / target).is_file(), flag)

    def test_fresh_host_runbook_linked_and_workflow_boundaries(self):
        for name in ("README.md","AGENTS.md","DEVELOPMENT.md","docs/OPERATOR_GUIDE.md",
                     "docs/AUTONOMOUS_CLI.md","docs/LOCAL_STUDIO_CONFIGURATION.md",
                     "docs/RELEASE_EXPORT.md","docs/RESTRICTED_AUDIT_BRIDGE.md"):
            self.assertIn("FRESH_INSTALL.md",(ROOT/name).read_text(encoding="utf-8"),name)
        guide=(ROOT/"docs/FRESH_INSTALL.md").read_text(encoding="utf-8")
        for token in ("--list-songs","--list-collections","--setup","--check-provider",
                      "--ready --media-dir","--confirm-run","DPAPI","CrisperWhisper Turbo",
                      "No prior chat","not yet","empty Studio library"):
            self.assertIn(token,guide,token)
