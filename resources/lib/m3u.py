"""Minimal M3U / M3U8 parser.

Deliberately has no Kodi imports so it can be unit-tested on any machine.
"""
import posixpath


def dirname(path):
    """Folder part of a playlist path (works for local, smb://, special:// ...)."""
    path = path.replace("\\", "/")
    return path.rsplit("/", 1)[0] if "/" in path else ""


def ext(path):
    """Lower-case extension including the dot, ignoring any ?query or |headers."""
    path = path.split("|", 1)[0].split("?", 1)[0]
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _is_absolute(entry):
    if "://" in entry or entry.startswith("/") or entry.startswith("\\\\"):
        return True
    # Windows drive path, e.g. C:\Videos\a.mkv or C:/Videos/a.mkv
    return len(entry) > 2 and entry[1] == ":" and entry[2] in "\\/"


def resolve(entry, base):
    """Resolve a playlist entry against the playlist's folder."""
    if _is_absolute(entry) or not base:
        return entry
    entry = entry.replace("\\", "/")
    scheme, sep, rest = base.partition("://")
    if not sep:
        rest = base
    joined = posixpath.normpath(posixpath.join(rest, entry))
    return f"{scheme}://{joined}" if sep else joined


def parse(text, base=""):
    """Return a list of (path, title_or_None) tuples, in file order."""
    entries = []
    title = None
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.upper().startswith("#EXTINF"):
            _, _, t = line.partition(",")
            title = t.strip() or None
            continue
        if line.startswith("#"):
            continue  # #EXTM3U and any other directives
        entries.append((resolve(line, base), title))
        title = None
    return entries
