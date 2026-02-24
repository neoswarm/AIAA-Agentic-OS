from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / ".claude" / "agents"

EXPECTED_ALLOWED_TOOLS = {
    "research": {"WebSearch", "WebFetch", "Read", "Write", "Bash"},
    "reviewer": {"Read", "Grep", "Glob", "Write"},
    "qa": {"Read", "Write", "Bash", "Grep", "Glob"},
    "content-writer": {"Read", "Write", "WebSearch", "WebFetch"},
    "deployer": {"Read", "Write", "Bash", "Grep", "Glob"},
}


def _read_frontmatter(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert match, f"Missing frontmatter: {path}"
    return match.group(1)


def _extract_profile_name(frontmatter: str, path: Path) -> str:
    match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    assert match, f"Missing name in frontmatter: {path}"
    return match.group(1).strip()


def _extract_allowed_tools(frontmatter: str, path: Path) -> set[str]:
    assert "allowedTools:" not in frontmatter, (
        f"Legacy key allowedTools found in {path}; use allowed_tools."
    )

    match = re.search(
        r"^allowed_tools:\s*\n((?:\s*-\s*[^\n]+\n?)*)",
        frontmatter,
        re.MULTILINE,
    )
    assert match, f"Missing allowed_tools in frontmatter: {path}"

    tools = set()
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            tools.add(stripped[2:].strip())
    assert tools, f"allowed_tools is empty: {path}"
    return tools


def test_profile_allowed_tools_are_explicit_and_complete() -> None:
    observed: dict[str, set[str]] = {}

    for profile_file in sorted(AGENTS_DIR.glob("*.md")):
        frontmatter = _read_frontmatter(profile_file)
        profile_name = _extract_profile_name(frontmatter, profile_file)
        observed[profile_name] = _extract_allowed_tools(frontmatter, profile_file)

    assert set(observed) == set(EXPECTED_ALLOWED_TOOLS)
    for profile_name, expected_tools in EXPECTED_ALLOWED_TOOLS.items():
        assert observed[profile_name] == expected_tools
