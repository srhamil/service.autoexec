"""Start-up playback logic for service.autoexec."""
import random

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import m3u

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

# Must match the option values in resources/settings.xml
MODE_PLAYLIST = 0
MODE_PLAYLIST_SHUFFLED = 1
MODE_RANDOM_FROM_PLAYLIST = 2
MODE_RANDOM_FROM_FOLDER = 3

HOME_TIMEOUT = 60  # seconds to wait for the home window before going anyway


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)


def _supported(kind):
    return {e.lower() for e in xbmc.getSupportedMedia(kind).split("|") if e}


def wait_for_home(monitor):
    """Wait until the home window is up. Returns False if Kodi is shutting down."""
    waited = 0.0
    while not xbmc.getCondVisibility("Window.IsVisible(home)"):
        if monitor.waitForAbort(0.5):
            return False
        waited += 0.5
        if waited >= HOME_TIMEOUT:
            log("home window not seen after %ds, continuing anyway" % HOME_TIMEOUT,
                xbmc.LOGWARNING)
            break
    return True


def load_playlist(path):
    if not path:
        raise ValueError("no playlist set in add-on settings")
    if not xbmcvfs.exists(path):
        raise FileNotFoundError(f"playlist not found: {path}")
    with xbmcvfs.File(path) as f:
        text = f.read()
    entries = m3u.parse(text, m3u.dirname(path))
    log(f"loaded {len(entries)} entries from {path}")
    return entries


def list_folder(folder):
    if not folder:
        raise ValueError("no folder set in add-on settings")
    if not folder.endswith(("/", "\\")):
        folder += "/"
    exts = _supported("video") | _supported("music")
    _dirs, files = xbmcvfs.listdir(folder)
    media = sorted(f for f in files if m3u.ext(f) in exts)
    log(f"found {len(media)} media files in {folder}")
    return [(folder + f, None) for f in media]


def collect(mode):
    if mode == MODE_RANDOM_FROM_FOLDER:
        items = list_folder(ADDON.getSettingString("folder"))
        return [random.choice(items)] if items else []

    items = load_playlist(ADDON.getSettingString("playlist"))
    if mode == MODE_PLAYLIST_SHUFFLED:
        random.shuffle(items)
    elif mode == MODE_RANDOM_FROM_PLAYLIST:
        items = [random.choice(items)] if items else []
    return items


def play(items):
    music = _supported("music")
    # Video playlist unless every item is clearly audio (mirrors what users expect
    # from PlayMedia, but without relying on Kodi guessing from the first item).
    if all(m3u.ext(p) in music for p, _ in items):
        playlist_id = xbmc.PLAYLIST_MUSIC
    else:
        playlist_id = xbmc.PLAYLIST_VIDEO

    playlist = xbmc.PlayList(playlist_id)
    playlist.clear()
    # Order is decided here; stop Kodi's remembered shuffle state re-ordering it.
    playlist.unshuffle()
    for path, title in items:
        label = title or path.replace("\\", "/").rsplit("/", 1)[-1]
        playlist.add(path, xbmcgui.ListItem(label=label))

    kind = "music" if playlist_id == xbmc.PLAYLIST_MUSIC else "video"
    log(f"playing {len(items)} item(s) on the {kind} playlist; first: {items[0][0]}")
    xbmc.Player().play(playlist)


def run():
    log("service started")
    if not ADDON.getSettingBool("enabled"):
        log("disabled in settings, nothing to do")
        return

    monitor = xbmc.Monitor()
    if not wait_for_home(monitor):
        return
    if monitor.waitForAbort(ADDON.getSettingInt("delay")):
        return

    if ADDON.getSettingBool("skip_if_playing") and xbmc.Player().isPlaying():
        log("something is already playing, skipping")
        return

    try:
        items = collect(ADDON.getSettingInt("mode"))
    except Exception as e:  # report config problems in the log, never crash Kodi
        log(f"cannot start playback: {e}", xbmc.LOGERROR)
        return

    if not items:
        log("nothing to play", xbmc.LOGWARNING)
        return

    play(items)
    log("done")
