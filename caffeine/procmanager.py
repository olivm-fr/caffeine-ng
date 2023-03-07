# Copyright (c) 2014 Hugo Osvaldo Barrera
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
import os
from typing import List


class ProcManager:
    def __init__(self, persistence_file: str):
        """Handles a list of process names backed by a file.

        A missing file is treated the same as an empty file. If the file is missing, it
        will only be created when necessary.

        :param persistence_file: Path to file with list of processes.
        """
        self.persistence_file = persistence_file
        self.proc_list: List[str] = []

        if os.path.exists(self.persistence_file):
            self.import_proc(self.persistence_file)

    def get_process_list(self) -> List[str]:
        return self.proc_list[:]

    def add_proc(self, name: str) -> None:
        if name not in self.proc_list:
            self.proc_list.append(name)
        self.save()

    def remove_proc(self, name: str) -> None:
        self.proc_list.remove(name)
        self.save()

    def import_proc(self, filename: str) -> None:
        with open(filename) as file:
            for line in file:
                line = line.strip()
                if line not in self.proc_list:
                    self.proc_list.append(line)
        self.save()

    def save(self) -> None:
        self.proc_list.sort()

        os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
        with open(self.persistence_file, "w") as f:
            f.write("\n".join(self.proc_list))
