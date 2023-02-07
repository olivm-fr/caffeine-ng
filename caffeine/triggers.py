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

from ewmh import EWMH
from pulsectl import Pulse
from pulsectl.pulsectl import PulseIndexError

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

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


class PollingTrigger(ABC):
    """PollingTriggers are "sources" that indicate that inhibition is desireable."""

    @abstractmethod
    def run(self) -> DesiredState:
        """Return the desired state right now.

        This method will be called periodically, and the trigger should return the
        desired state at the time of the call.
        """


class ManualTrigger(PollingTrigger):
    active = False

    def run(self) -> DesiredState:
        if self.active:
            return DesiredState.INHIBIT_ALL
        else:
            return DesiredState.UNINHIBITED


@dataclass
class WhiteListTrigger(PollingTrigger):
    process_manager: ProcManager

    def run(self) -> DesiredState:
        """Determine if one of the whitelisted processes is running."""

        for proc in self.process_manager.get_process_list():
            try:
                if utils.is_process_running(proc):
                    logger.info(f"Process '{proc}' detected. Inhibiting.")
                    return DesiredState.INHIBIT_ALL
            except Exception:
                logger.warn(f"Error occured while polling for process '{proc}'.")
                continue

        return DesiredState.UNINHIBITED


class FullscreenTrigger(PollingTrigger):
    def __init__(self):
        if os.environ.get("WAYLAND_DISPLAY") is None:
            self._ewmh = EWMH()
        else:
            logger.info("Running on Wayland; fullscreen trigger won't work.")
            self._ewmh = None

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
            logger.info("Fullscreen window detected.")
            return DesiredState.INHIBIT_ALL
        else:
            return DesiredState.UNINHIBITED


class PulseAudioTrigger(PollingTrigger):
    def __init__(
        self,
        process_manager: ProcManager,
        audio_peak_filtering_active_getter: Callable[[], bool],
    ) -> None:
        self.__process_manager = process_manager
        self.__audio_peak_filtering_active_getter = audio_peak_filtering_active_getter

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
            logger.debug(f"Video playback detected ({', '.join(active_applications)}).")
            return DesiredState.INHIBIT_ALL
        elif music_procs > 0:
            logger.debug(f"Audio playback detected ({', '.join(active_applications)}).")
            return DesiredState.INHIBIT_SLEEP
        else:
            return DesiredState.UNINHIBITED


class EventTrigger(ABC):
    """EventTriggers are "sources" that monitor for events that may trigger inhibition."""


class MPRISTrigger(EventTrigger):
    def __init__(self, on_trigger: Callable[[], None], bus=None):
        self.active_players: Dict[str, str] = {}  # dbus id -> player name
        obj_path = "/org/mpris/MediaPlayer2"
        prop_path = "org.freedesktop.DBus.Properties"
        DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus(GLib.MainLoop())

        def playback_status_changed(
            interface_name: str,
            changed_properties: Dict[str, str],
            invalidated_properties: List[str],
            bus_name: str,
        ):
            if interface_name != "org.mpris.MediaPlayer2.Player":
                return
            playback_changed = "PlaybackStatus" in changed_properties
            playback_status = (
                None
                if not playback_changed
                else str(changed_properties["PlaybackStatus"])
            )
            if not playback_changed:
                return
            match playback_status:
                case "Playing":
                    player_proxy = self.session_bus.get_object(
                        bus_name, "/org/mpris/MediaPlayer2"
                    )
                    player_name = self.get_player_name(player_proxy)
                    self.active_players[bus_name] = player_name
                    logger.debug(f"Media '{player_name}' detected playing.")
                    logger.debug(self.active_players_str())
                case ("Paused" | "Stopped"):
                    if bus_name in self.active_players:
                        logger.debug(
                            f"Media '{self.active_players[bus_name]}' playback stopped/paused."
                        )
                        del self.active_players[bus_name]
                        logger.debug(self.active_players_str())
                case _:
                    raise Exception("That's not meant to happen...")
            if len(self.active_players) > 0:
                self.state = DesiredState.INHIBIT_ALL
            else:
                self.state = DesiredState.UNINHIBITED
            on_trigger()

        self.session_bus.add_signal_receiver(
            handler_function=playback_status_changed,
            signal_name="PropertiesChanged",
            dbus_interface=prop_path,
            bus_name=None,
            path=obj_path,
            sender_keyword="bus_name",
        )
        self.init_state()

    def init_state(self):
        self.state = DesiredState.UNINHIBITED
        for service in self.session_bus.list_names():
            if not service.startswith("org.mpris.MediaPlayer2."):
                continue
            player = dbus.SessionBus().get_object(service, "/org/mpris/MediaPlayer2")
            status = self.get_player_status(player)
            if status == "Playing":
                player_name = self.get_player_name(player)
                self.active_players[str(player.bus_name)] = player_name
                self.state = DesiredState.INHIBIT_ALL
                logger.debug(f"Media '{player_name}' detected playing.")
                logger.debug(self.active_players_str())
                break

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
            return f"Active players: [{', '.join(players)}]."
