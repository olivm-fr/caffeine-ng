caffeine(1)

# NAME

caffeine - utility to temporarily disable (inhibit) screensavers

# SYNOPSIS

*caffeine*++
*caffeine* _start_ Starts caffeine++

# DESCRIPTION

caffeine shows an icon on the system tray. When activated, screensavers, screen
dimming, and sceenlockers will be temporarily disabled (also referred to as
"inhibiting").

# COMMANDS

*start*
	Runs caffeine and shows a tray icon. This is the default when no command
	is specified.

# INTEGRATIONS

*caffeine-ng* works with the following screensavers / screenlockers:

- Anything that implements the ``org.freedesktop.ScreenSaver`` API (this
  includes KDE, amongst others)
- gnome-screensaver
- XSS
- Xorg + DPMS
- xautolock
- xidlehook.

On Xorg, caffeine will automatically detect fullscreen applications, and disable
the screensaver while they are active.

# CONFIGURATION

Caffeine will auto-detect which screensaver is being used at runtime.

Caffeine includes a GTK3+ preferences interface. It is not, as of yet,
configurable via the command line.

# ENVIRONMENT

The following environment variables may optionally be defined:

_CAFFEINE_LEGACY_TRAY_
	This will use legacy APIs rather than AppIndicator APIs. This may fail
	on Wayland, and *may* allow left-clicking on some Xorg status tray
	implementations.

# PRIVACY

Caffine does not require any network connectivity.

When the pulseaudio peak detection feature is enabled, caffeine will detect
peaks in volume to determine if audio is being used.

# DEVELOPMENT

For issues and general development inquiries, see the project home currently
hosted at Codeberg:

	https://codeberg.org/WhyNotHugo/caffeine-ng

# SEE ALSO

- http://launchpad.net/caffeine/
- https://bugs.launchpad.net/caffeine/+bug/1321750

# AUTHORS

Developed by Hugo O. Barrera <hugo@whynothugo.nl>, with invaluable contributions
from the community.

caffeine-ng is an open source project licensed under the GPLv3+ licence and
developed for anyone to use freely. If you would like to sponsor this project,
see:

	https://liberapay.com/WhyNotHugo/
