# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
# 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU General Public License for more details. 
# 
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import curses
from curses import textpad

class Textbox(textpad.Textbox):
    def __init__(self, win, poll, insert_mode=False):
        try:
            textpad.Textbox.__init__(self, win, insert_mode)
        except TypeError:  # python 2.5 didn't support insert_mode
            textpad.Textbox.__init__(self, win)
        self.poll_function = poll

    def edit(self, initial_input=""):
        for char in list(initial_input):
            self.do_command(char)
        if initial_input != "":
            self.poll_function(self.count())

        abort = False
        while 1:
            ch = self.win.getch()

            if ch == 127:
                self.do_command(263)
            elif ch == curses.KEY_ENTER or ch == 10:
                break
            elif ch == 9 or ch == 27:
                abort = True
                break
            elif ch == curses.KEY_DC:
                self.win.delch()
            elif not ch:
                continue
            elif not self.do_command(ch):
                break

            self.poll_function(self.count())
            self.win.refresh()

        if abort == False:
            return self.gather()
        else:
            return None

    def count(self):
        cursor_position = self.win.getyx()
        count = 0
        for y in range(self.maxy+1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            if stop != 0:
                count -= 1
            for x in range(self.maxx+1):
                if self.stripspaces and x > stop:
                    break
                count += 1
        self.win.move(cursor_position[0], cursor_position[1])
        return count
