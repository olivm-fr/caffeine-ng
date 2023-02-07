# Copyright (c) 2014-2015 Hugo Osvaldo Barrera
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
import logging
import os.path
from gettext import gettext as _
from threading import Timer
from typing import List
from typing import Literal
from typing import Optional
from typing import Callable

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Notify

from caffeine.icons import empty_cup_icon
from caffeine.icons import full_cup_icon
from caffeine.inhibitors import DpmsInhibitor
from caffeine.inhibitors import GnomeInhibitor
from caffeine.inhibitors import XautolockInhibitor
from caffeine.inhibitors import XdgPowerManagmentInhibitor
from caffeine.inhibitors import XdgScreenSaverInhibitor
from caffeine.inhibitors import XfceInhibitor
from caffeine.inhibitors import XidlehookInhibitor
from caffeine.inhibitors import XorgInhibitor
from caffeine.inhibitors import XssInhibitor
from caffeine.procmanager import ProcManager
from caffeine.triggers import DesiredState
from caffeine.triggers import EventTrigger
from caffeine.triggers import FullscreenTrigger
from caffeine.triggers import ManualTrigger
from caffeine.triggers import PollingTrigger
from caffeine.triggers import PulseAudioTrigger
from caffeine.triggers import WhiteListTrigger
from caffeine.triggers import MPRISTrigger

os.chdir(os.path.abspath(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


class Caffeine(GObject.GObject):
    """Implements the main caffeine service itself."""

    timer: Optional[Timer]

    def __init__(
        self,
        process_manager: ProcManager,
        process_manager_audio: ProcManager,
        on_toggle: Callable[[], None],
        pulseaudio: bool,
        whitelist: bool,
        fullscreen: bool,
    ):
        """Main caffeine worker.

        :param pulseaudio: Whether pulseaudio support should be enabled.
        :param whitelist: Whether whitelist support should be enabled.
        """
        GObject.GObject.__init__(self)
        self.connect("activation-toggled", on_toggle)

        self.__inhibitors = [
            GnomeInhibitor(),
            XdgPowerManagmentInhibitor(),
            XssInhibitor(),
            XorgInhibitor(),
            XautolockInhibitor(),
            XfceInhibitor(),
            XidlehookInhibitor(),
            XdgScreenSaverInhibitor(),
            DpmsInhibitor(),
        ]

        self.__process_manager = process_manager
        self.__process_manager_audio = process_manager_audio

        self.__audio_peak_filtering_active = True

        self._manual_trigger = ManualTrigger()
        self.polling_triggers: List[PollingTrigger] = [self._manual_trigger]
        if whitelist:
            self.polling_triggers.append(WhiteListTrigger(self.__process_manager))
        if fullscreen:
            self.polling_triggers.append(FullscreenTrigger())
        if pulseaudio:
            self.polling_triggers.append(
                PulseAudioTrigger(
                    process_manager=self.__process_manager_audio,
                    audio_peak_filtering_active_getter=self.get_audio_peak_filtering_active,
                )
            )

        logger.info("Running with polling triggers: %r.", self.polling_triggers)

        # The initial state is uninhibited.
        self.desired_state = DesiredState.UNINHIBITED

        # Status string (XXX: Let's double check how well this is working).
        self.status_string = "Caffeine is starting up..."

        # Number of procs playing audio but nothing visual. This is a special
        # case where we want the screen to turn off while still preventing
        # the computer from suspending
        self.music_procs = 0

        self.timer = None
        self.notification = None

        self.polling_state = DesiredState.UNINHIBITED
        self.event_triggers: List[EventTrigger] = [
            MPRISTrigger(lambda: self.apply_desired_state())
        ]
        self.apply_desired_state()

        # FIXME: add capability to xdg-screensaver to report timeout.
        if len(self.polling_triggers) > 0:
            GLib.timeout_add(10000, self.run_polling_triggers)

        logger.info(self.status_string)

    def run_polling_triggers(self, show_notification=False) -> Literal[True]:
        """Runs all polling triggers to determine the currently desired status."""
        polling_state = DesiredState.UNINHIBITED

        for trigger in self.polling_triggers:
            polling_state = max(polling_state, trigger.run())

            if polling_state == DesiredState.INHIBIT_ALL:
                logger.debug("%s requested %s.", trigger, polling_state)
                break

        self.polling_state = polling_state
        self.apply_desired_state(show_notification)

        # Timeout will repeat indefinitely while this returns True.
        return True

    def apply_desired_state(self, show_notification=False) -> None:
        desired_state = max(
            self.polling_state, *[trigger.state for trigger in self.event_triggers]
        )
        if self.desired_state != desired_state:
            self.desired_state = desired_state
            logger.info(f"Desired state is: {self.desired_state}")
            self.apply_desired_status(show_notification)

    def quit(self) -> None:
        """
        Cancels any timer thread running so the program can quit right away.
        """
        if self.timer:
            self.timer.cancel()

    def _notify(self, message: str, icon: str, title: str = "Caffeine") -> None:
        """Easy way to use pynotify."""

        Notify.init("Caffeine")
        if self.notification:
            self.notification.update(title, message, icon)
        else:
            self.notification = Notify.Notification.new(title, message, icon)

        if self.notification:
            self.notification.show()

    def timed_activation(self, time: int, show_notification=True) -> None:
        """Toggle inhibition after a given amount of seconds."""
        message = (
            _("Timed activation set; ")
            + _("Caffeine will prevent powersaving for the next ")
            + str(time)
        )

        logger.info("Timed activation set for " + str(time))

        if self.status_string == "":
            self.status_string = _("Activated for ") + str(time)

        self.set_activated(True)
        self.run_polling_triggers()

        if show_notification:
            self._notify(message, full_cup_icon)

        # and deactivate after time has passed.
        # Stop already running timer
        if self.timer:
            interval = self.timer.interval  # type: ignore
            logger.info(
                "Previous timed activation cancelled due to a "
                "second timed activation request "
                f"(was set for {interval} or {time} seconds )"
            )
            self.timer.cancel()

        self.timer = Timer(time, self._deactivate, args=[show_notification])
        self.timer.name = "Active"
        self.timer.start()

    def _deactivate(self, show_notification: bool) -> None:
        """Called when the timer finished running."""

        self._manual_trigger.active = False
        interval = self.timer.interval  # type: ignore
        message = str(interval) + _(" have elapsed; powersaving is re-enabled")

        logger.info(
            "Timed activation period ("
            + str(self.timer.interval)  # type: ignore
            + ") has elapsed"
        )

        if show_notification:
            self._notify(message, empty_cup_icon)

        self.timer = None
        self.run_polling_triggers()

    def set_activated(self, activated: bool) -> None:
        """Set manual activation to the provided value."""

        if not activated and self.timer:
            # If manually deactivating, cancel timers.
            self.cancel_timer()

        # Update actual status:
        self._manual_trigger.active = activated

        # Emit signal so the UI updates.
        self.emit(
            "activation-toggled",
            self.desired_state != DesiredState.UNINHIBITED,
            self.status_string,
        )

    def get_activated(self) -> bool:
        """Returns True if inhibition was manually activated."""
        return self._manual_trigger.active

    def toggle_activated(self, show_notification=True):
        """Toggle manual inhibition."""

        self.set_activated(not self.get_activated())
        self.run_polling_triggers(show_notification)

    def cancel_timer(self, note=True):
        """Cancel a running timer.

        This cancellation is due to user interaction, generally, toggling a
        timed activation.

        :param note: Whether a notification should be shown.
        """

        # If the user manually disables caffeine, we should also
        # cancel the timer for timed activation.

        if self.timer is not None:
            interval: int = self.timer.interval  # type: ignore
            message = _("Timed activation cancelled (was set for ") + f"{interval})"

            logger.info("Timed cancelled (was set for %d).", interval)

            if note:
                self._notify(message, empty_cup_icon)

            self.timer.cancel()
            self.timer = None

        # Re run all triggers...
        self.run_polling_triggers()

    def apply_desired_status(self, show_notification=False) -> None:
        """Applies the currently desired status."""

        inhibit_sleep = self.desired_state in (
            DesiredState.INHIBIT_SLEEP,
            DesiredState.INHIBIT_ALL,
        )
        inhibit_screen = self.desired_state == DesiredState.INHIBIT_ALL

        for inhibitor in self.__inhibitors:
            if inhibitor.applicable:
                if inhibitor.is_screen_inhibitor:
                    inhibitor.set(inhibit_screen)
                else:
                    inhibitor.set(inhibit_sleep)

                logger.info(f"{inhibitor} is applicable, state: {inhibitor.running}")

        if self.desired_state != DesiredState.UNINHIBITED:
            self.status_string = _("Caffeine is dormant; powersaving is enabled.")
        if self.desired_state != DesiredState.INHIBIT_SLEEP:
            self.status_string = _("Caffeine is preventing sleep only.")
        else:
            self.status_string = _("Caffeine is preventing all powersaving.")

        # Emit signal so the UI updates.
        self.emit(
            "activation-toggled",
            self.desired_state != DesiredState.UNINHIBITED,
            self.status_string,
        )

    def get_audio_peak_filtering_active(self) -> bool:
        return self.__audio_peak_filtering_active

    def set_audio_peak_filtering_active(self, active: bool):
        self.__audio_peak_filtering_active = active


# register a signal
GObject.signal_new(
    "activation-toggled", Caffeine, GObject.SignalFlags.RUN_FIRST, None, [bool, str]
)
