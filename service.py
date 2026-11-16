# Entry point for the xbmc.service extension. Kodi puts the add-on folder on
# sys.path, so the package under resources/lib is importable directly.
from resources.lib import startup

startup.run()
