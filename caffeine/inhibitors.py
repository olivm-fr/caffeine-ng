# Copyright (c) 2014-2023 Hugo Osvaldo Barrera and contributors
#
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import shutil
import subprocess
import threading
import time
from abc import ABC
from abc import abstractmethod

import dbus

logger = logging.getLogger(__name__)


class BaseInhibitor(ABC):
    running: bool

    def __init__(self):
        self.running = False

    def set(self, state: bool, reason: str) -> None:
        if state:
            if not self.running:
                self.inhibit(reason)
            else:
                self.update_reason(reason)
        elif self.running:
            self.uninhibit()

    def update_reason(self, reason: str) -> None:
        self.uninhibit()
        self.inhibit(reason)

    @property
    def is_screen_inhibitor(self) -> bool:
        """Return True if this instance is a screen saver inhibitor.

        Inhibitor which are sleep inhibitors should return False.
        """
        return False

    @property
    @abstractmethod
    def applicable(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def inhibit(self, reason: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def uninhibit(self) -> None:
        raise NotImplementedError()

    def __str__(self):
        return self.__class__.__name__


class GnomeInhibitor(BaseInhibitor):
    def __init__(self):
        super().__init__()
        self.bus = dbus.SessionBus()

        self.__proxy = None
        self.__cookie = None

    def inhibit(self, reason: str) -> None:
        if not self.__proxy:
            self.__proxy = self.bus.get_object(
                "org.gnome.SessionManager",
                "/org/gnome/SessionManager",
            )
            self.__proxy = dbus.Interface(
                self.__proxy,
                dbus_interface="org.gnome.SessionManager",
            )

        self.__cookie = self.__proxy.Inhibit(
            "Caffeine",
            dbus.UInt32(0),
            reason,
            dbus.UInt32(4),
        )
        self.running = True

    def uninhibit(self) -> None:
        if self.__cookie is not None:
            self.__proxy.Uninhibit(self.__cookie)
        self.running = False

    @property
    def applicable(self) -> bool:
        return "org.gnome.SessionManager" in self.bus.list_names()


class MateScreenSaverInhibitor(BaseInhibitor):
    def __init__(self):
        super().__init__()
        self.bus = dbus.SessionBus()

        self.__cookie = None

    def inhibit(self, reason: str) -> None:
        self.__proxy = self.bus.get_object(
            "org.mate.ScreenSaver",
            "/org/mate/ScreenSaver",
        )
        self.__proxy = dbus.Interface(
            self.__proxy,
            dbus_interface="org.mate.ScreenSaver",
        )
        self.__cookie = self.__proxy.Inhibit("Caffeine", reason)

        self.running = True

    def uninhibit(self) -> None:
        if self.__cookie:
            self.__proxy.UnInhibit(self.__cookie)
        self.running = False

    @property
    def is_screen_inhibitor(self) -> bool:
        return True

    @property
    def applicable(self) -> bool:
        return "org.mate.ScreenSaver" in self.bus.list_names()


class XdgScreenSaverInhibitor(BaseInhibitor):
    def __init__(self):
        super().__init__()
        self.bus = dbus.SessionBus()

        self.__cookie = None

    def inhibit(self, reason: str) -> None:
        self.__proxy = self.bus.get_object(
            "org.freedesktop.ScreenSaver",
            "/ScreenSaver",
        )
        self.__proxy = dbus.Interface(
            self.__proxy,
            dbus_interface="org.freedesktop.ScreenSaver",
        )
        self.__cookie = self.__proxy.Inhibit("Caffeine", reason)

        self.running = True

    def uninhibit(self) -> None:
        if self.__cookie:
            self.__proxy.UnInhibit(self.__cookie)
        self.running = False

    @property
    def is_screen_inhibitor(self) -> bool:
        return True

    @property
    def applicable(self) -> bool:
        return "org.freedesktop.ScreenSaver" in self.bus.list_names()


class XdgPowerManagmentInhibitor(BaseInhibitor):
    def __init__(self):
        super().__init__()
        self.bus = dbus.SessionBus()

        self.__cookie = None

    def inhibit(self, reason: str) -> None:
        self.__proxy = self.bus.get_object(
            "org.freedesktop.PowerManagement",
            "/org/freedesktop/PowerManagement/Inhibit",
        )
        self.__proxy = dbus.Interface(
            self.__proxy,
            dbus_interface="org.freedesktop.PowerManagement.Inhibit",
        )
        self.__cookie = self.__proxy.Inhibit("Caffeine", reason)
        self.running = True

    def uninhibit(self) -> None:
        if self.__cookie:
            self.__proxy.UnInhibit(self.__cookie)
        self.running = False

    @property
    def applicable(self) -> bool:
        return "org.freedesktop.PowerManagement" in self.bus.list_names()


class XssInhibitor(BaseInhibitor):
    class XssInhibitorThread(threading.Thread):
        keep_running = True
        daemon = True

        def run(self):
            logging.info("Running XSS inhibitor thread.")
            while self.keep_running:
                subprocess.run(["xscreensaver-command", "-deactivate"])
                time.sleep(50)
            logging.info("XSS inhibitor thread finishing.")

    def inhibit(self, reason: str) -> None:
        self.running = True
        self.thread = XssInhibitor.XssInhibitorThread()
        self.thread.start()

    def uninhibit(self) -> None:
        self.running = False
        self.thread.keep_running = False

    @property
    def applicable(self) -> bool:
        # TODO!
        return subprocess.run(["pgrep", "xscreensaver"]).returncode == 0


class DpmsInhibitor(BaseInhibitor):
    def inhibit(self, reason: str) -> None:
        self.running = True

        subprocess.run(["xset", "-dpms"])

    def uninhibit(self) -> None:
        self.running = False

        # FIXME: Aren't we enabling it if it was never online?
        # Grep `xset q` for "DPMS is Enabled"
        subprocess.run(["xset", "+dpms"])

    @property
    def is_screen_inhibitor(self) -> bool:
        return True

    @property
    def applicable(self) -> bool:
        # TODO: Condition is incomplete
        return os.environ.get("WAYLAND_DISPLAY") is None


class XorgInhibitor(BaseInhibitor):
    def inhibit(self, reason: str) -> None:
        self.running = True
        subprocess.run(["xset", "s", "off"])

    def uninhibit(self) -> None:
        self.running = False

        # FIXME: Aren't we enabling it if it was never online?
        # Scrensaver.*\n\s+timeout:  600
        subprocess.run(["xset", "s", "on"])

    @property
    def applicable(self) -> bool:
        # TODO: Condition is incomplete
        return os.environ.get("WAYLAND_DISPLAY") is None


class XautolockInhibitor(BaseInhibitor):
    def inhibit(self, reason: str) -> None:
        self.running = True
        subprocess.run(["xautolock", "-disable"])

    def uninhibit(self) -> None:
        self.running = False
        subprocess.run(["xautolock", "-enable"])

    @property
    def applicable(self) -> bool:
        return subprocess.run(["pgrep", "xautolock"]).returncode == 0


class XfceInhibitor(BaseInhibitor):
    def __init__(self):
        BaseInhibitor.__init__(self)

    def inhibit(self, reason=None):  # "Inhibited via libcaffeine"):
        self.running = True

        subprocess.run(
            [
                "xfconf-query",
                "-c",
                "xfce4-power-manager",
                "-p",
                "/xfce4-power-manager/presentation-mode",
                "-s",
                "true",
            ]
        )

    def uninhibit(self):
        self.running = False

        subprocess.run(
            [
                "xfconf-query",
                "-c",
                "xfce4-power-manager",
                "-p",
                "/xfce4-power-manager/presentation-mode",
                "-s",
                "false",
            ]
        )

    @property
    def applicable(self):
        # If `xfconf-query` is absent, this is not applicable.
        return shutil.which("xfconf-query") is not None


class XidlehookInhibitor(BaseInhibitor):
    def inhibit(self, reason: str) -> None:
        self.running = True
        subprocess.run(["pkill", "-SIGSTOP", "xidlehook"])

    def uninhibit(self) -> None:
        self.running = False
        subprocess.run(["pkill", "-SIGCONT", "xidlehook"])

    @property
    def applicable(self) -> bool:
        return subprocess.run(["pgrep", "xidlehook"]).returncode == 0
