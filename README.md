# Caffeine-ng

[![build status](https://ci.codeberg.org/api/badges/WhyNotHugo/caffeine-ng/status.svg)](https://ci.codeberg.org/WhyNotHugo/caffeine-ng/branches/main)
[![licence](https://img.shields.io/pypi/l/caffeine-ng.svg)](https://codeberg.org/WhyNotHugo/caffeine-ng/src/branch/main/LICENCE)

Caffeine is a little daemon that sits in your systray, and prevents the
screensaver from showing up, or the system from going to sleep. It does so when
an application is fullscreened (eg: youtube), or when you click on the systray
icon (which you can do, when, eg: reading).

## History

Caffeing-ng (since 2014) started as a fork of [Caffeine 2.4], since the
original version dropped support for the systray icon in favour of only
automatic detection of fullscreen apps only, which turned to be a rather
[controversial] decision.

The intention of this fork is to also evolve on its own, not only fixing
issues, but also implemented missing features, when relevant.

Caffeine-ng was shortly know as Taurine, a play on its successor's name, since
taurine is a known stimulant, commonly found in energy drinks. However, this
name did not last, since the artwork would not match adequately, and changing
it was undesirable.

[caffeine 2.3]: http://launchpad.net/caffeine/
[controversial]: https://bugs.launchpad.net/caffeine/+bug/1321750

## Requirements

- Python 3.6 or later is required (as of November 2023, 3.11 is known to work).
- The following Python packages (the exact name will vary across distributions).
  - py3-click
  - py3-dbus
  - py3-ewmh
  - py3-gobject3
  - py3-pulsectl
  - py3-setproctitle
- Meson (only for building and installing)
- libayatana-appindicator
- libnotify
- GTK+3.0
- xdg-utils

## Compatibility

`caffeine-ng` works with the following screensavers / screenlockers:

- Anything that implements the `org.freedesktop.ScreenSaver` API (this
includes KDE, amongst others)
- gnome-screensaver
- XSS
- Xorg + DPMS
- xautolock
- xidlehook.

## Installation

### ArchLinux

On ArchLinux, caffeine-ng is available at the [AUR][aur].

[aur]: https://aur.archlinux.org/packages/caffeine-ng/

### Debian and derivatives

First install all the required packages:

      apt install meson \
        python-gi-dev \
        python-dbus-dev \
        libgtk-3-dev \
        libnotify-dev \
        libappindicator3-dev \
        python3-click \
        python3-ewmh \
        python3-setproctitle \
        python3-pulsectl \
        git \
        scdoc

And mark them auto if you wish:

      apt-mark auto meson \
        ...same list as above...

Then you need to build sources with:

      meson build
      ninja -C build

Create a package for your distribution:

      checkinstall \
        --pkgname=caffeine-ng \
        --pkgversion=4.1 \
        --requires="python3-gi,python3-dev,libgtk-3-0,libnotify4,libappindicator3-1,python3-click,python3-ewmh,python3-setproctitle," \
        --conflicts="caffeine" \
        --nodoc \
        meson install -C build

Replace version string with correct version and append this command with
`--install=no` should you wish to inspect created package before installing it.

`checkinstall` is available for various distributions, so you may follow these
steps adapting them to your distribution

For additional discussion on building DEB packages, see:

- https://codeberg.org/WhyNotHugo/caffeine-ng/issues/118
- https://codeberg.org/WhyNotHugo/caffeine-ng/issues/121

### Gentoo

Gentoo users may find [caffeine-ng][gentoo-caffeine-ng] in
[::pf4public][gentoo-overlay] Gentoo overlay.

[gentoo-caffeine-ng]: https://github.com/PF4Public/gentoo-overlay/tree/master/x11-misc/caffeine-ng
[gentoo-overlay]: https://github.com/PF4Public/gentoo-overlay

### Others / from source

To manually install caffeine-ng, run:

      meson build
      ninja -C build
      sudo meson install -C build
      sudo glib-compile-schemas /usr/share/glib-2.0/schemas

### Note for packagers

Generally, package manager handle running `glib-compile-schemas` themselves, so
this doesn't need to be triggered explicitly.

To install into `/usr/` rather than `/usr/local/`, instead of running `meson build`
run `meson --prefix /usr build`.

See https://mesonbuild.com/Builtin-options.html for details.

## Auto-start

To have Caffeine-ng run on startup, add it to your System Settings => Startup
Programs list.

## Translations

To generate the `pot` file use::

    find . -iname "*.py" -o -iname "*.glade" | \
    xargs xgettext --from-code utf-8 -o translations/caffeine.pot

## License

Copyright (C) 2014-2022 Hugo Osvaldo Barrera <hugo@whynothugo.nl>
Copyright (C) 2009 The Caffeine Developers

Caffeine-ng is distributed under the GNU General Public License, either version
3, or (at your option) any later version. See LICENCE for details.

The Caffeine-ng status icons are Copyright (C) 2014 mildmojo
(http://github.com/mildmojo), and distributed under the terms of the GNU Lesser
General Public License, either version 3, or (at your option) any later
version. See LGPL.

The Caffeien-ng SVG shortcut icons are Copyright (C) 2009 Tommy Brunn
(http://www.blastfromthepast.se/blabbermouth), and distributed under the
terms of the GNU Lesser General Public License, either version 3, or (at
your option) any later version. See LGPL.

## Contributing

- To run: `./bin/caffeine`
- To compile translations: `./update_translations`

If you want to test out a translation without changing the language for the
whole session: `LANG=ru_RU.UTF-8 ./bin/caffeine` (Replace ru_RU.UTF-8 with
whichever language you want to use. You will need to a language pack for the
specific language) Be aware that some stock items will not be translated unless
you log in with a given language.
