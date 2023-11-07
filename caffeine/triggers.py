"""Triggers are different events or states that auto-activate caffeine."""
import logging
import os
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from typing import Dict
from typing import List

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from ewmh import EWMH
from gi.repository import GLib
from pulsectl import Pulse
from pulsectl.pulsectl import PulseIndexError

from caffeine import utils
from caffeine.procmanager import ProcManager  # noqa: E402

logger = logging.getLogger(__name__)


class DesiredState(Enum):
    UNINHIBITED = 0  # Don't inhibit anything.
    INHIBIT_SLEEP = 5  # Only inhibit sleeping (screen saver can go off).
    INHIBIT_ALL = 10  # Inhibit both screen saver and sleeping.

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented


class Trigger(ABC):
    """Sources that indicate that inhibition is desireable."""

    reason: str


class PollingTrigger(Trigger):
    """Triggers that need to be checked every once in a while in order"""

    @abstractmethod
    def run(self) -> DesiredState:
        """Return the desired state right now.

        This method will be called periodically, and the trigger should return the
        desired state at the time of the call.
        """


@dataclass
class WhiteListTrigger(PollingTrigger):
    def __init__(self, process_manager: ProcManager):
        self.process_manager = process_manager
        self.reason = ""

    def run(self) -> DesiredState:
        """Determine if one of the whitelisted processes is running."""

        for proc in self.process_manager.get_process_list():
            try:
                if utils.is_process_running(proc):
                    self.reason = f"Process '{proc}' detected"
                    logger.info(self.reason)
                    return DesiredState.INHIBIT_ALL
            except Exception:
                logger.warn(f"Error occured while polling for process '{proc}'.")
                continue

        self.reason = ""
        return DesiredState.UNINHIBITED


class FullscreenTrigger(PollingTrigger):
    def __init__(self):
        if os.environ.get("WAYLAND_DISPLAY") is None:
            self._ewmh = EWMH()
        else:
            logger.info("Running on Wayland; fullscreen trigger won't work.")
            self._ewmh = None
        self.reason = ""

    def run(self) -> DesiredState:
        """Determine if a fullscreen application is running."""
        inhibit = False

        if self._ewmh:
            window = self._ewmh.getActiveWindow()

            # ewmh.getWmState(window) returns None is scenarios where
            # ewmh.getWmState(window, str=True) throws an exception
            # (it's a bug in pyewmh):
            if window and self._ewmh.getWmState(window):
                wm_state = self._ewmh.getWmState(window, True)
                inhibit = "_NET_WM_STATE_FULLSCREEN" in wm_state

        if inhibit:
            self.reason = "Fullscreen window detected"
            logger.info(self.reason)
            return DesiredState.INHIBIT_ALL
        else:
            self.reason = ""
            return DesiredState.UNINHIBITED


class PulseAudioTrigger(PollingTrigger):
    def __init__(
        self,
        process_manager: ProcManager,
        audio_peak_filtering_active_getter: Callable[[], bool],
    ) -> None:
        self.__process_manager = process_manager
        self.__audio_peak_filtering_active_getter = audio_peak_filtering_active_getter
        self.reason = ""

    @property
    def __audio_peak_filtering_active(self) -> bool:
        return self.__audio_peak_filtering_active_getter()

    def run(self) -> DesiredState:
        # Let's look for playing audio:
        # Number of supposed audio only streams.  We can turn the screen off
        # for those:
        music_procs = 0
        # Number of all audio streams including videos. We keep the screen on
        # here:
        screen_relevant_procs = 0
        # Applications currently playing audio.
        active_applications = []
        # Applications whose audio activity is ignored
        ignored_applications = self.__process_manager.get_process_list()

        # Get all audio playback streams
        # Music players seem to use the music role. We can turn the screen
        # off there. Keep the screen on for audio without music role,
        # as they might be videos
        with Pulse() as pulseaudio:
            for application_output in pulseaudio.sink_input_list():
                if (
                    not application_output.mute  # application audio is not muted
                    and not application_output.corked  # application audio is not paused
                    and not pulseaudio.sink_info(
                        application_output.sink
                    ).mute  # system audio is not muted
                ):
                    application_name = application_output.proplist.get(
                        "application.process.binary", "no name"
                    )
                    if application_name in ignored_applications:
                        continue
                    if self.__audio_peak_filtering_active:
                        # ignore silent sinks
                        sink_source = pulseaudio.sink_info(
                            application_output.sink
                        ).monitor_source
                        sink_peak = pulseaudio.get_peak_sample(sink_source, 0.4)
                        if not sink_peak > 0:
                            continue
                    if application_output.proplist.get("media.role") == "music":
                        # seems to be audio only
                        music_procs += 1
                    else:
                        # Video or other audio source
                        screen_relevant_procs += 1
                    # Save the application's process name
                    active_applications.append(application_name)

            # Get all audio recording streams
            for application_input in pulseaudio.source_output_list():
                try:
                    system_input_muted = pulseaudio.source_info(
                        application_input.source
                    ).mute
                except PulseIndexError:
                    system_input_muted = False
                if (
                    not application_input.mute  # application input is not muted
                    # source_output_list() also returns the object used to peak
                    # for audio playback streams. Exclude it:
                    and application_input.name != "peak detect"
                    and not system_input_muted
                ):
                    application_name = application_input.proplist.get(
                        "application.process.binary", "no name"
                    )
                    if application_name in ignored_applications:
                        continue
                    if self.__audio_peak_filtering_active:
                        # ignore silent sources
                        source_peak = pulseaudio.get_peak_sample(
                            application_input.source, 0.1
                        )
                        if not (source_peak > 0):
                            continue
                    # Treat recordings as video because likely you don't
                    # want to turn the screen of while recording
                    screen_relevant_procs += 1
                    # Save the application's process name
                    active_applications.append(application_name)

        if screen_relevant_procs > 0:
            self.reason = f"Video playback detected: {', '.join(active_applications)}"
            logger.debug(self.reason)
            return DesiredState.INHIBIT_ALL
        elif music_procs > 0:
            self.reason = f"Audio playback detected: {', '.join(active_applications)}"
            logger.debug(self.reason)
            return DesiredState.INHIBIT_SLEEP
        else:
            self.reason = ""
            return DesiredState.UNINHIBITED


class EventTrigger(Trigger):
    """Sources that monitor for events that may trigger inhibition."""

    state: DesiredState


class ManualTrigger(EventTrigger):
    def __init__(self, on_trigger: Callable[[], None], init_state: bool = False):
        self.is_active = init_state
        self.state = DesiredState.UNINHIBITED
        self.on_trigger = on_trigger
        self.reason = ""

    def set(self, activated: bool) -> None:
        """Set manual activation to the provided value."""

        self.is_active = activated
        if self.is_active:
            self.state = DesiredState.INHIBIT_ALL
            self.reason = "Session manually inhibited"
            logger.debug(self.reason)
        else:
            self.state = DesiredState.UNINHIBITED
            self.reason = ""
            logger.debug("Session manually uninhibited")
        self.on_trigger()

    def toggle(self):
        self.set(not self.is_active)


class MPRISTrigger(EventTrigger):
    def __init__(
        self, on_trigger: Callable[[], None], process_manager: ProcManager, bus=None
    ):
        self.ignored_applications = process_manager.get_process_list()
        self.active_players: Dict[str, str] = {}  # dbus id -> player name
        self.reason = ""
        self.on_trigger = on_trigger

        DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus(GLib.MainLoop())
        self.xdg_bus = self.session_bus.get_object(
            bus_name="org.freedesktop.DBus", object_path="/org/freedesktop/DBus"
        )

        self.session_bus.add_signal_receiver(
            handler_function=self._playback_status_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            bus_name=None,
            path="/org/mpris/MediaPlayer2",
            sender_keyword="bus_name",
        )

        self.state = DesiredState.UNINHIBITED
        for service in self.session_bus.list_names():
            if not service.startswith("org.mpris.MediaPlayer2."):
                continue
            player = self.session_bus.get_object(service, "/org/mpris/MediaPlayer2")
            status = self.get_player_status(player)
            if status == "Playing":
                self._add_player(
                    str(player.bus_name), player, trigger=False
                )  # on_trigger() may not callable yet on MPRISTrigger construction

    def _playback_status_changed(
        self,
        interface_name: str,
        changed_properties: Dict[str, str],
        invalidated_properties: List[str],
        bus_name: str,
    ):
        if (
            interface_name != "org.mpris.MediaPlayer2.Player"
            or "PlaybackStatus" not in changed_properties
        ):
            return
        playback_status = str(changed_properties["PlaybackStatus"])
        match playback_status:
            case "Playing":
                self._add_player(bus_name)
            case ("Paused" | "Stopped"):
                if bus_name in self.active_players:
                    self._remove_player(bus_name)
            case _:
                raise Exception("That's not meant to happen...")

    def update(self, trigger):
        self.reason = self.get_reason()
        if len(self.active_players) > 0:
            self.state = DesiredState.INHIBIT_ALL
        else:
            self.state = DesiredState.UNINHIBITED
        if trigger:
            self.on_trigger()

    def _add_player(self, bus_name: str, player_proxy=None, trigger=True):
        if player_proxy is None:
            player_proxy = self.session_bus.get_object(
                bus_name, "/org/mpris/MediaPlayer2"
            )
        player_name = self.get_player_name(player_proxy)
        process_name = self.get_player_appid(player_proxy)
        if process_name in self.ignored_applications:
            logger.debug(
                f"Blacklisted media '{player_name}' detected playing"
                + f" (process: {process_name}). Skipping!"
            )
            return
        self.active_players[bus_name] = player_name
        self._remove_if_closed(bus_name)
        logger.debug(
            f"Media '{player_name}' detected playing"
            + f" (process: {self.get_player_appid(player_proxy)})."
        )
        logger.debug(self.active_players_str())
        self.update(trigger)

    def _remove_if_closed(self, bus_name: str):
        self.xdg_bus.connect_to_signal(
            signal_name="NameOwnerChanged",
            handler_function=lambda bus_name, old_owner, new_owner: self._remove_player(
                bus_name
            ),
            dbus_interface="org.freedesktop.DBus",
            arg0=bus_name,  # e.g. 'org.mpris.MediaPlayer2.spotify',
            arg2="",  # new_owner
        )

    def _remove_player(self, bus_name: str):
        if bus_name not in self.active_players:
            # sometimes, due to async calls, this method is called after
            # self.active_players was already updated
            return
        logger.debug(
            "Media '%s' playback stopped/paused/closed.", self.active_players[bus_name]
        )
        del self.active_players[bus_name]
        logger.debug(self.active_players_str())
        self.update(trigger=True)

    def get_player_status(self, player: dbus.proxies.ProxyObject):
        return str(
            player.Get(
                "org.mpris.MediaPlayer2.Player",
                "PlaybackStatus",
                dbus_interface="org.freedesktop.DBus.Properties",
            )
        )

    def get_player_name(self, player: dbus.proxies.ProxyObject):
        return str(
            player.Get(
                "org.mpris.MediaPlayer2",
                "Identity",
                dbus_interface="org.freedesktop.DBus.Properties",
            )
        )

    def get_player_appid(self, player: dbus.proxies.ProxyObject):
        return str(
            player.Get(
                "org.mpris.MediaPlayer2",
                "DesktopEntry",
                dbus_interface="org.freedesktop.DBus.Properties",
            )
        )

    def active_players_str(self):
        players = self.active_players.values()
        if len(players) == 0:
            return "No other active player detected."
        else:
            return f"Active players: [{', '.join(players)}]"

    def get_reason(self):
        players = self.active_players.values()
        if len(players) == 0:
            return ""
        return f"Media detected playing: {', '.join(players)}"
