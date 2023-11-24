# Copyright (c) 2014-2023 Hugo Osvaldo Barrera and contributors
# Copyright © 2009 The Caffeine Developers
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
import gettext
import locale

from caffeine.paths import LOCALE_PATH
from caffeine.version import version

__version__ = version


def init_translations() -> None:
    """Initialise translations. Should be called just once at startup."""

    gettext_domain = "caffeine-ng"
    locale.setlocale(locale.LC_ALL, "")

    for module in locale, gettext:
        module.bindtextdomain(gettext_domain, LOCALE_PATH)
        module.textdomain(gettext_domain)


init_translations()
