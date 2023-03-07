# Copyright (c) 2014-2022 Hugo Osvaldo Barrera
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
from os.path import join

LOCALE_PATH = "@localedir@"
PKGDATADIR = "@pkgdatadir@"
IMAGE_PATH = join(PKGDATADIR, "caffeine/images")
ICON_PATH = join(PKGDATADIR, "icons")


xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
app_config_dir = join(xdg_config_home, "caffeine")


def get_glade_file(filename):
    return join(PKGDATADIR, "caffeine/glade", filename)


def get_whitelist_file():
    return join(app_config_dir, "whitelist.txt")


def get_blacklist_file_audio():
    return join(app_config_dir, "audio_blacklist.txt")
