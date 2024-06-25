
Changelog
=========

v4.3.0
------

- An MPRIS-based trigger is now available. This will set caffeine to inhibit
  based on the state of a currently running media player.
- The pulseaudio integration is now disabled by default. It is deprecated and
  will be removed in the 5.0.0 release. The MPRIS integration yields more
  consistent results and should be used instead.
- ``caffeine kill`` and `caffeine start --kill`` been removed. You can Quit
  caffeine via the tray icon menu. These commands are redundant, there's plenty
  of ways to find and kill a process (e.g.: ``ps aux | grep caffeine`` and
  ``kill``). Your service manager likely offers some mechanism to stop and
  restart the service too.
- The "single instance" logic has been dropped. It adds needless complexity and
  adds no real value. Service managers can ensure that only one instance is
  running at any given time. Normal usages just run caffeine once at session
  start up. For the uncommon scenario where a user might have multiple sessions
  at once, this allows running one caffeine session for each session.

v4.2.0
------

- Release tarballs are now available with a ``version`` file inside of them. This
  means that it's not longer necessary to git-clone the source repositories to
  build a release.
- When using release tarballs, ``git`` is not longer required.

v4.1.0
------

- The build system has switched to ``meson``. For more details on why this is
  happening, see `Meson for Python applications`_
- The ``wheel``, ``build`` and ``install`` python packages is no longer
  required (neither at build time nor runtime).
- ``ayatana-appindicator3`` will be used if present. In such scenarios,
  ``appindicator3`` is no longer required. Either one may be present. If both
  are present then ``ayatana-appindicator3`` is used.
- ``indicator3`` is no longer marked as a dependency. It was not actually
  used in the past either; only ``appindicator3`` was used.
- ``scdoc`` is required to build man pages.
- The ``xdg``  python is no longer required. Our usage of it was trivial, and
  has been replaced with three very simple lines of code.

.. _Meson for Python applications: https://whynothugo.nl/journal/2022/07/26/meson-for-python-applications/

v4.0.1
------

- Fixed an issue which prevents caffeine-ng from sometimes triggering properly.

v4.0.0
------

Command line usage changes
..........................

This release rewrites the CLI portion of caffeine-ng into ``click``. ``click``
is the standard library in python for writing CLI apps, and is better
maintained. This is part of an initiative to bring caffeine to a more modern
stack and facilitate future development on it.

This rewrite also allowed for cleaning up some skeletons in the closet.

``caffeine-ng`` now depends on ``click``, and no longer depends on ``docopt``.

The CLI interface has changed slightly, but should now be more easy to
navigate. See ``caffeine --help``, ``caffeine start --help``, etc.

The way the PID file is handled has been hardened and simplified, but this will
result in caffeine 4.0 not killing older versions. Exit any older versions that
may be running before upgrading (or simply don't restart it until your next
reboot).

Status icon changes
...................

The `libappindicator` dependency is now mandatory.

Previously, we'd determine whether to use StatusIcon vs AppIndicator based on
the presence of this dependency. This was problematic for users who had the
library installed as a dependency for another program, but wanted StatusIcons.
If you want a StatusIcon, please set the `CAFFEINE_LEGACY_TRAY` to any value.

This also reduces confusion for users of desktops that _only_ support
AppIndicator, but were unaware of the difference or unaware of the optional
dependency.

If your desktop *does not* support AppIndicator, fallback to using a StatusIcon
should be automatic. If you get *no* icon out-of-the-box, please report the
issue.


Other changes
.............

 - Xorg-based inhibitors are now disabled on Wayland.

 - Python 3.6 or later is required. Python 3.6 and 3.7 are deprecated and will
   soon be dropped. This will be the last release with support for these
   versions.

 - Added support for xfce "presentation mode".

 - **Breaking**: python-docopt is no longer required. python-click is now
   required.

 - Pulseaudio support has been reworked, and should have less false positives,
   but it's still imperfect. In future, an MPRIS alternative might be a
   suitable replacement.

 - Various translations have been updated.

 - Desktop entries no longer have absolute paths, which should ease writing
   wrapper scripts or using tools like Firejail.

 - The "preferences" desktop entry has been dropped.

 - This project has moved to Codeberg, an open source, community maintained
   code forge. The official home is now https://codeberg.org/WhyNotHugo/caffeine-ng
