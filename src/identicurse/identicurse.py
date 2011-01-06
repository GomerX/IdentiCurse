# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
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

import os, sys, curses, locale, re, subprocess
try:
    import json
except ImportError:
    import simplejson as json
from threading import Timer
from textbox import Textbox
import urllib2

from statusnet import StatusNet, StatusNetError
from tabbage import *
from statusbar import StatusBar

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

colour_fields = {
    "none": 0,
    "statusbar": 1,
    "timelines": 2,
    "selector": 4,
    "username": 5,
    "time": 6,
    "source": 7,
    "notice_count": 8,
    "notice": 9,
    "profile_title": 10,
    "profile_fields": 11,
    "profile_values": 12,
    "group": 13,
    "tag": 14,
    "search_highlight": 15
}

colours = {
    "none": -1,
    "black": 0,
    "red": 1,
    "green": 2,
    "brown": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "grey": 8,
    "light_red": 9,
    "light_green": 10,
    "yellow": 11,
    "light_blue": 12,
    "light_magenta": 13,
    "light_cyan": 14,
    "light_white": 15
}

base_colours = {}

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self, additional_config={}):
        self.path = os.path.dirname(os.path.realpath( __file__ ))
        self.qreply = False
        
        if "config_filename" in additional_config:
            self.config_file = os.path.expanduser(additional_config['config_filename'])
        else:
            self.config_file = os.path.join(os.path.expanduser("~") ,".identicurse")

        try:
            if os.path.exists(self.config_file):
                self.config = json.loads(open(self.config_file).read())
            else:
                self.config = json.loads(open(os.path.join("/etc", "identicurse.conf")).read())
        except ValueError:
            sys.exit("ERROR: Your config file could not be succesfully loaded due to JSON syntax error(s). Please fix it.")
        except IOError:
            import getpass, time
            # no config yet, so let's build one
            self.config = json.loads(open(os.path.join(self.path, "config.json"), "r").read())  # get the base config
            print "No config was found, so we will now run through a few quick questions to set up a basic config for you (which will be saved as %s so you can manually edit it later). If the default (where defaults are available, they're stated in []) is already fine for any question, just press Enter without typing anything, and the default will be used." % (self.config_file)
            self.config['username'] = raw_input("Username: ")
            self.config['password'] = getpass.getpass("Password: ")
            api_path = raw_input("API path [%s]: " % (self.config['api_path']))
            if api_path != "":
                self.config['api_path'] = api_path
            update_interval = raw_input("Auto-refresh interval (in whole seconds) [%d]: " % (self.config['update_interval']))
            if update_interval != "":
                try:
                    self.config['update_interval'] = int(update_interval)
                except ValueError:
                    print "Sorry, you entered an invalid interval. The default of %d will be used instead." % (self.config['update_interval'])
            notice_limit = raw_input("Number of notices to fetch per timeline page [%d]: " % (self.config['notice_limit']))
            if notice_limit != "":
                try:
                    self.config['notice_limit'] = int(notice_limit)
                except ValueError:
                    print "Sorry, you entered an invalid number of notices. The default of %d will be used instead." % (self.config['notice_limit'])
            try:
                temp_conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])
            except Exception, (errmsg):
                sys.exit("Couldn't establish connection with provided credentials: %s" % (errmsg))
            print "Okay! Everything seems good! Your new config will now be saved, then IdentiCurse will start properly."
            open(self.config_file, "w").write(json.dumps(self.config, indent=4))
            time.sleep(1)

        self.last_page_search = {'query':"", 'occurs':[], 'viewing':0, 'tab':-1}

        # prepare the known commands list
        self.known_commands = [
            "/reply",
            "/favourite",
            "/repeat",
            "/direct",
            "/delete",
            "/profile",
            "/spamreport",
            "/block",
            "/unblock",
            "/user",
            "/context",
            "/subscribe",
            "/unsubscribe",
            "/group",
            "/groupjoin",
            "/groupleave",
            "/groupmember",
            "/tag",
            "/sentdirects",
            "/favourites",
            "/search",
            "/home",
            "/mentions",
            "/directs",
            "/public",
            "/config",
            "/alias",
            "/link",
            "/bugreport",
            "/featurerequest"
        ]
        
        # Set some defaults for configs that we will always need to use, but that are optional
        if not "enable_colours" in self.config:
            self.config["enable_colours"] = False
        else:
            default_colour_scheme = {
                "timelines": ("none", "none"),
                "statusbar": ("black", "white"),
                "selector": ("brown", "none"),
                "time": ("brown", "none"),
                "source": ("green", "none"),
                "notice": ("none", "none"),
                "notice_count": ("blue", "none"),
                "username": ("cyan", "none"),
                "group": ("cyan", "none"),
                "tag": ("cyan", "none"),
                "profile_title": ("cyan", "none"),
                "profile_fields": ("blue", "none"),
                "profile_values": ("none", "none"),
                "search_highlight": ("white", "blue"),
                "none": ("none", "none")
            }

            # Default colour scheme
            if not "colours" in self.config:
                self.config["colours"] = default_colour_scheme
            else:
                for part in colour_fields:
                    if not part in self.config["colours"]:
                        self.config["colours"][part] = default_colour_scheme[part]

        if not "search_case_sensitive" in self.config:
            self.config['search_case_sensitive'] = "sensitive"
        if not "long_dent" in self.config:
            self.config['long_dent'] = "split"
        if not "filters" in self.config:
            self.config['filters'] = []
        if not "notice_limit" in self.config:
            self.config['notice_limit'] = 25
        if not "browser" in self.config:
            self.config['browser'] = "xdg-open '%s'"
        if not "border" in self.config:
            self.config['border'] = True
        if not "compact_notices" in self.config:
            self.config['compact_notices'] = True
        if not "user_rainbow" in self.config:
            self.config["user_rainbow"] = False
        if not "group_rainbow" in self.config:
            self.config["group_rainbow"] = False
        if not "tag_rainbow" in self.config:
            self.config["tag_rainbow"] = False
        if not "expand_remote" in self.config:
            self.config["expand_remote"] = False
        if not "keys" in self.config:
            self.config['keys'] = {}
        if not "scrollup" in self.config['keys']:
            self.config['keys']['scrollup'] = ['k']
        if not "scrolltop" in self.config['keys']:
            self.config['keys']['scrolltop'] = ['g']
        if not "pageup" in self.config['keys']:
            self.config['keys']['pageup'] = ['b']
        if not "scrolldown" in self.config['keys']:
            self.config['keys']['scrolldown'] = ['j']
        if not "scrollbottom" in self.config['keys']:
            self.config['keys']['scrollbottom'] = ['G']
        if not "pagedown" in self.config['keys']:
            self.config['keys']['pagedown'] = [' ']

        empty_default_keys = ("firstpage", "newerpage", "olderpage", "refresh",
            "input", "search", "quit", "closetab", "help", "nexttab", "prevtab",
            "qreply", "creply", "cfav", "ccontext", "crepeat", "cnext", "cprev",
            "cfirst", "nextmatch", "prevmatch")

        for k in empty_default_keys:
            self.config['keys'][k] = []
        
        self.url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

        try:
            self.conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])
        except Exception, (errmsg):
            sys.exit("ERROR: Couldn't establish connection: %s" % (errmsg))

        self.insert_mode = False
        self.search_mode = False
        curses.wrapper(self.initialise)

    def redraw(self):
        self.screen.clear()
        self.screen.refresh()
        self.y, self.x = self.screen.getmaxyx()

        if self.config['border']:
            self.main_window = self.screen.subwin(self.y-3, self.x-3, 2, 2)
            self.main_window.box(0, 0)
        else:
            self.main_window = self.screen.subwin(self.y-1, self.x-1, 1, 1)
        self.main_window.keypad(1)

        y, x = self.main_window.getmaxyx()

        if self.conn.length_limit == 0:
            entry_lines = 3
        else:
            entry_lines = (self.conn.length_limit / x) + 1

        if self.config['border']:
            self.entry_window = self.main_window.subwin(entry_lines, x-6, 4, 5)
        else:
            self.entry_window = self.main_window.subwin(entry_lines, x-2, 1, 1)

        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)

        self.text_entry.stripspaces = 1
        if self.config['border']:
            self.notice_window = self.main_window.subwin(y-6, x-4, 5 + entry_lines, 5)
        else:
            self.notice_window = self.main_window.subwin(y-5, x, 2 + entry_lines, 1)
        self.notice_window.bkgd(" ", curses.color_pair(colour_fields["timelines"]))

        # I don't like this, but it looks like it has to be done
        if hasattr(self, 'tabs'):
            for tab in self.tabs:
                tab.window = self.notice_window

        if self.config['border']:
            self.status_window = self.main_window.subwin(1, x-5, y, 5)
        else:
            self.status_window = self.main_window.subwin(1, x, y-1, 1)
        if hasattr(self, 'status_bar'):
            self.status_bar.window = self.status_window
        self.status_window.bkgd(" ", curses.color_pair(colour_fields["statusbar"]))

    def initialise(self, screen):
        self.screen = screen

        curses.noecho()
        curses.cbreak()
        curses.use_default_colors()

        if curses.has_colors() and self.config['enable_colours'] == True:
            curses.start_color()

            for field, (fg, bg) in self.config['colours'].items():
                try:
                    curses.init_pair(colour_fields[field], colours[fg], colours[bg])
                except:
                    continue
            c = 50
            for (key, value) in colours.items():
                if (value + 1) > curses.COLORS:
                    continue

                if not key in ("black", "white", "none") and key != self.config['colours']['notice']:
                    base_colours[colours[key]] = c
                    curses.init_pair(c, value, colours["none"])
                    c += 1
        else:
            for field in colour_fields:
                curses.init_pair(colour_fields[field], -1, -1)

            c = 50
            for (key, value) in colours.items():
                if key != "black":
                    base_colours[colours[key]] = c
                    curses.init_pair(c, -1, -1)
                    c += 1

        self.redraw()

        self.status_bar = StatusBar(self.status_window)
        self.status_bar.update_left("Welcome to IdentiCurse")
        
        self.tabs = []
        for tabspec in self.config['initial_tabs'].split("|"):
            tab = tabspec.split(':')
            if tab[0] in ("home", "mentions", "direct", "public", "sentdirect"):
                self.tabs.append(Timeline(self.conn, self.notice_window, tab[0], notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            elif tab[0] == "profile":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                self.tabs.append(Profile(self.conn, self.notice_window, screen_name))
            elif tab[0] == "user":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                user_id = self.conn.users_show(screen_name=screen_name)['id']
                self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'screen_name':screen_name, 'user_id':user_id}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            elif tab[0] == "group":
                nickname = tab[1]
                if nickname[0] == "!":
                    nickname = nickname[1:]
                group_id = int(self.conn.statusnet_groups_show(nickname=nickname)['id'])
                self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'nickname':nickname, 'group_id':group_id}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            if tab[0] == "tag":
                tag = tab[1]
                if tag[0] == "#":
                    tag = tag[1:]
                self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            if tab[0] == "search":
                self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':tab[1]}, filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            #not too sure why anyone would need to auto-open these last two, but it couldn't hurt to add them
            if tab[0] == "context":
                notice_id = int(tab[1])
                self.tabs.append(Context(self.conn, self.notice_window, notice_id, compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
            if tab[0] == "help":
                self.tabs.append(Help(self.notice_window, self.path))

        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

        self.current_tab = 0
        self.tabs[self.current_tab].active = True
        self.tab_order = range(len(self.tabs))

        self.update_tabs()
        self.display_current_tab()

        self.loop()

    def update_tabs(self):
        self.update_timer.cancel()
        if self.insert_mode == False:
            self.status_bar.update_left("Updating Timelines...")
            TabUpdater(self.tabs, self, 'end_update_tabs').start()
        else:
            self.update_timer = Timer(self.config['update_interval'], self.update_tabs)

    def end_update_tabs(self):
        self.display_current_tab()
        self.status_bar.update_left("Doing nothing.")
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def update_tab_buffers(self):
        for tab in self.tabs:
            tab.update_buffer()

    def display_current_tab(self):
        self.tabs[self.current_tab].display()
        self.status_bar.update_right("Tab " + str(self.current_tab + 1) + ": " + self.tabs[self.current_tab].name)

    def close_current_tab(self):
        if len(self.tabs) == 1:
            pass
        else:
            del self.tabs[self.current_tab]
            del self.tab_order[0]
            for index in range(len(self.tab_order)):
                if self.tab_order[index] > self.current_tab:
                    self.tab_order[index] -= 1
            self.current_tab = self.tab_order[0]
            self.tabs[self.current_tab].active = True
            
            self.display_current_tab()

    def loop(self):
        running = True

        while running:
            input = self.main_window.getch()
           
            if self.qreply == False:
                switch_to_tab = None
                for x in range(0, len(self.tabs)):
                    if input == ord(str(x+1)):
                        switch_to_tab = x
                if input == ord(">") or input in [ord(key) for key in self.config['keys']['nexttab']]:
                    if self.current_tab < (len(self.tabs) - 1):
                        switch_to_tab = self.current_tab + 1
                elif input == ord("<") or input in [ord(key) for key in self.config['keys']['prevtab']]:
                    if self.current_tab >= 1:
                        switch_to_tab = self.current_tab - 1

                if switch_to_tab is not None:
                    self.tab_order.insert(0, self.tab_order.pop(self.tab_order.index(switch_to_tab)))
                    self.tabs[self.current_tab].active = False
                    self.current_tab = switch_to_tab
                    self.tabs[self.current_tab].active = True
            else:
                for x in range(1, 9):
                    if input == ord(str(x)):
                        self.update_timer.cancel()
                        self.insert_mode = True
                        self.parse_input(self.text_entry.edit("/r " + str(x) + " "))
                self.qreply = False
            
            if input == curses.KEY_UP or input in [ord(key) for key in self.config['keys']['scrollup']]:
                self.tabs[self.current_tab].scrollup(1)
                self.display_current_tab()
            elif input == curses.KEY_HOME or input in [ord(key) for key in self.config['keys']['scrolltop']]:
                self.tabs[self.current_tab].scrollup(0)
                self.display_current_tab()
            elif input == curses.KEY_PPAGE or input in [ord(key) for key in self.config['keys']['pageup']]:
                self.tabs[self.current_tab].scrollup(self.main_window.getmaxyx()[0] - 11) # the 11 offset gives 2 lines of overlap between the pre-scroll view and post-scroll view
                self.display_current_tab()
            elif input == curses.KEY_DOWN or input in [ord(key) for key in self.config['keys']['scrolldown']]:
                self.tabs[self.current_tab].scrolldown(1)
                self.display_current_tab()
            elif input == curses.KEY_END or input in [ord(key) for key in self.config['keys']['scrollbottom']]:
                self.tabs[self.current_tab].scrolldown(0)
                self.display_current_tab()
            elif input == curses.KEY_NPAGE or input in [ord(key) for key in self.config['keys']['pagedown']]:
                self.tabs[self.current_tab].scrolldown(self.main_window.getmaxyx()[0] - 11) # as above
                self.display_current_tab()
            elif input == ord("=") or input in [ord(key) for key in self.config['keys']['firstpage']]:
                if self.tabs[self.current_tab].prevpage(0):
                    self.status_bar.update_left("Moving to first page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == curses.KEY_LEFT or input in [ord(key) for key in self.config['keys']['newerpage']]:
                if self.tabs[self.current_tab].prevpage():
                    self.status_bar.update_left("Moving to newer page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == curses.KEY_RIGHT or input in [ord(key) for key in self.config['keys']['olderpage']]:
                if self.tabs[self.current_tab].nextpage():
                    self.status_bar.update_left("Moving to older page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == ord("r") or input in [ord(key) for key in self.config['keys']['refresh']]:
                self.update_tabs()
            elif input == ord("i") or input in [ord(key) for key in self.config['keys']['input']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit())
            elif input == ord("/") or input in [ord(key) for key in self.config['keys']['search']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.search_mode = True
                self.parse_search(self.text_entry.edit())
            elif input == ord("q") or input in [ord(key) for key in self.config['keys']['quit']]:
                running = False
            elif input == ord("x") or input in [ord(key) for key in self.config['keys']['closetab']]:
                self.close_current_tab()
            elif input == ord("h") or input in [ord(key) for key in self.config['keys']['help']]:
                self.tabs.append(Help(self.notice_window, self.path))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
            elif input == ord("l") or input in [ord(key) for key in self.config['keys']['qreply']]:
                self.qreply = True
            elif input == ord("d") or input in [ord(key) for key in self.config['keys']['creply']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit("/r " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
            elif input == ord("s") or input in [ord(key) for key in self.config['keys']['cnext']]:
                if self.tabs[self.current_tab].chosen_one != (len(self.tabs[self.current_tab].timeline) - 1):
                    self.tabs[self.current_tab].chosen_one += 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("a") or input in [ord(key) for key in self.config['keys']['cprev']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one -= 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("z") or input in [ord(key) for key in self.config['keys']['cfirst']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one = 0
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("f") or input in [ord(key) for key in self.config['keys']['cfav']]:
                self.status_bar.update_left("Favouriting Notice...")
                if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                else:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                self.conn.favorites_create(id)
                self.status_bar.update_left("Doing Nothing.")
            elif input == ord("e") or input in [ord(key) for key in self.config['keys']['crepeat']]:
                self.status_bar.update_left("Repeating Notice...")
                if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                else:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                update = self.conn.statuses_retweet(id, source="IdentiCurse")
                if isinstance(update, list):
                    for notice in update:
                        self.tabs[self.current_tab].timeline.insert(0, notice)
                else:
                    self.tabs[self.current_tab].timeline.insert(0, update)
                self.tabs[self.current_tab].update_buffer()
                self.status_bar.update_left("Doing Nothing.")
            elif input == ord("c") or input in [ord(key) for key in self.config['keys']['ccontext']]:
                self.status_bar.update_left("Loading Context...")
                if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                else:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                self.tabs.append(Context(self.conn, self.notice_window, id, compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
                self.status_bar.update_left("Doing Nothing.")
            elif input == ord("n") or input in [ord(key) for key in self.config['keys']['nextmatch']]:
                if (self.last_page_search['query'] != "") and (self.last_page_search['tab'] == self.current_tab):
                    if self.last_page_search['viewing'] < (len(self.last_page_search['occurs']) - 1):
                        self.last_page_search['viewing'] += 1
                    else:
                        self.last_page_search['viewing'] = 0
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    if self.last_page_search['viewing'] == 0:
                        self.status_bar.update_left("Viewing result #%d for '%s' (search hit BOTTOM, continuing at TOP)" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    else:
                        self.status_bar.update_left("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    self.display_current_tab()
            elif input == ord("N") or input in [ord(key) for key in self.config['keys']['prevmatch']]:
                if (self.last_page_search['query'] != "") and (self.last_page_search['tab'] == self.current_tab):
                    if self.last_page_search['viewing'] > 0:
                        self.last_page_search['viewing'] -= 1
                    else:
                        self.last_page_search['viewing'] = len(self.last_page_search['occurs']) - 1
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    if self.last_page_search['viewing'] == (len(self.last_page_search['occurs']) - 1):
                        self.status_bar.update_left("Viewing result #%d for '%s' (search hit TOP, continuing at BOTTOM)" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    else:
                        self.status_bar.update_left("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    self.display_current_tab()
            elif input == curses.ascii.ctrl(ord("l")):
                self.redraw()

            y, x = self.screen.getmaxyx()
            if y != self.y or x != self.x:
                self.redraw()
                self.update_tab_buffers()


            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, character_count):
        if not self.search_mode:
            if self.conn.length_limit == 0:
                self.status_bar.update_left("Insert Mode: " + str(character_count))
            else:
                self.status_bar.update_left("Insert Mode: " + str(self.conn.length_limit - character_count))
        else:
            if self.last_page_search['query'] != "":
                self.status_bar.update_left("In-page Search (last search: '%s')" % (self.last_page_search['query']))
            else:
                self.status_bar.update_left("In-page Search")

    def parse_input(self, input):
        update = False

        if input is None:
            input = ""

        if len(input) > 0:      # don't do anything if the user didn't enter anything
            input = input.rstrip()

            tokens = [token for token in input.split(" ") if token != ""]

            if tokens[0][0] == "i" and ((tokens[0][1:] in self.known_commands) or (tokens[0][1:] in self.config["aliases"])):
                tokens[0] = tokens[0][1:]  # avoid doing the wrong thing when people accidentally submit stuff like "i/r 2 blabla"

            # catch mistakes like "/r1" - the last condition is so that, for example, "/directs" is not mistakenly converted to "/direct s"
            for command in self.known_commands:
                if (tokens[0][:len(command)] == command) and (tokens[0] != command) and not (tokens[0] in self.known_commands) and not (tokens[0] in self.config['aliases']):
                    tokens[:1] = [command, tokens[0].replace(command, "")]
            for alias in self.config['aliases']:
                if (tokens[0][:len(alias)] == alias) and (tokens[0] != alias) and not (tokens[0] in self.known_commands) and not (tokens[0] in self.config['aliases']):
                    tokens[:1] = [alias, tokens[0].replace(alias, "")]

            if tokens[0] in self.config["aliases"]:
                tokens = self.config["aliases"][tokens[0]].split(" ") + tokens[1:]

            try:
                if ("direct" in self.tabs[self.current_tab].timeline_type) and (tokens[0] == "/reply"):
                    tokens[0] = "/direct"
            except AttributeError:
                # the tab has no timeline_type, so it's *definitely* not directs.
                pass

            if tokens[0] in self.known_commands:
                
                try:
                    if tokens[0] == "/reply" and len(tokens) >= 3:
                        self.status_bar.update_left("Posting Reply...")
    
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = 0  # this is not a reply to a dent
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        status = "@" + user + " " + " ".join(tokens[2:])
    
                        try:
                            update = self.conn.statuses_update(status, "IdentiCurse", int(id), long_dent=self.config['long_dent'], dup_first_word=True)
                        except Exception, (errmsg):
                            self.status_bar.timed_update_left("ERROR: Couldn't post status: %s" % (errmsg))
    
                    elif tokens[0] == "/favourite" and len(tokens) == 2:
                        self.status_bar.update_left("Favouriting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        self.conn.favorites_create(id)
    
                    elif tokens[0] == "/repeat" and len(tokens) == 2:
                        self.status_bar.update_left("Repeating Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        update = self.conn.statuses_retweet(id, source="IdentiCurse")
                        
                    elif tokens[0] == "/direct" and len(tokens) >= 3:
                        self.status_bar.update_left("Sending Direct...")
                        
                        try:
                            float(tokens[1])
                        except ValueError:
                            screen_name = tokens[1]
                            if screen_name[0] == "@":
                                screen_name = screen_name[1:]
                        else:
                            if "direct" in self.tabs[self.current_tab].timeline_type:
                                screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['sender']['screen_name']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['user']['screen_name']
                                else:
                                    screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['screen_name']
                        id = self.conn.users_show(screen_name=screen_name)['id']
                        
                        self.conn.direct_messages_new(screen_name, id, " ".join(tokens[2:]), source="IdentiCurse")
    
                    elif tokens[0] == "/delete" and len(tokens) == 2:
                        self.status_bar.update_left("Deleting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            repeat_id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        try:
                            self.conn.statuses_destroy(id)
                        except statusnet.StatusNetError, e:
                            if e.errcode == 403:  # user doesn't own the original status, so is probably trying to delete the repeat
                                self.conn.statuses_destroy(repeat_id)
                            else:  # it wasn't a 403, so re-raise
                                raise(e)
    
                    elif tokens[0] == "/profile" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Profile...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
    
                        self.tabs.append(Profile(self.conn, self.notice_window,user))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/spamreport" and len(tokens) >= 3:
                        self.status_bar.update_left("Firing Orbital Laser Cannon...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            username = tokens[1]
                            if username[0] == "@":
                                    username = username[1:]
                            id = self.conn.users_show(screen_name=username)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['user']['id']
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        status = "@support !sr @%s UID %d %s" % (username, id, " ".join(tokens[2:]))
                        update = self.conn.statuses_update(status, "IdentiCurse")
                        self.conn.blocks_create(user_id=id, screen_name=username)
    
                    elif tokens[0] == "/block" and len(tokens) >= 2:
                        self.status_bar.update_left("Creating Block(s)...")
                        for token in tokens[1:]:
                            # Yeuch
                            try:
                                float(token)
                            except ValueError:
                                user = token
                                if user[0] == "@":
                                    user = user[1:]
                                id = self.conn.users_show(screen_name=user)['id']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                            self.conn.blocks_create(user_id=id, screen_name=user)
    
                    elif tokens[0] == "/unblock" and len(tokens) >= 2:
                        self.status_bar.update_left("Removing Block(s)...")
                        for token in tokens[1:]:
                            # Yeuch
                            try:
                                float(token)
                            except ValueError:
                                user = token
                                if user[0] == "@":
                                    user = user[1:]
                                id = self.conn.users_show(screen_name=user)['id']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                            self.conn.blocks_destroy(user_id=id, screen_name=user)
    
                    elif tokens[0] == "/user" and len(tokens) == 2:
                        self.status_bar.update_left("Loading User Timeline...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                        
                        self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'user_id':id, 'screen_name':user}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/context" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Context...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["id"]
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]
    
                        self.tabs.append(Context(self.conn, self.notice_window, id, compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/subscribe" and len(tokens) == 2:
                        self.status_bar.update_left("Subscribing...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
    
                        self.conn.friendships_create(user_id=id, screen_name=user)
                        
                    elif tokens[0] == "/unsubscribe" and len(tokens) == 2:
                        self.status_bar.update_left("Unsubscribing...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
    
                        self.conn.friendships_destroy(user_id=id, screen_name=user)
    
                    elif tokens[0] == "/group" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Group Timeline...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'group_id':id, 'nickname':group}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/groupjoin" and len(tokens) == 2:
                        self.status_bar.update_left("Joining Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_join(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupleave" and len(tokens) == 2:
                        self.status_bar.update_left("Leaving Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_leave(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupmember" and len(tokens) == 2:
                        self.status_bar.update_left("Checking membership...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
                        user_id = int(self.conn.users_show(screen_name=self.config['username'])['id'])

                        if self.conn.statusnet_groups_is_member(user_id, group_id):
                            self.status_bar.timed_update_left("You are a member of !%s." % (group))
                        else:
                            self.status_bar.timed_update_left("You are not a member of !%s." % (group))

                    elif tokens[0] == "/tag" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Tag Timeline...")
                        tag = tokens[1]
                        if tag[0] == "#":
                            tag = tag[1:]
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}, notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], group_rainbow=self.config['group_rainbow'], tag_rainbow=self.config['tag_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/sentdirects" and len(tokens) == 1:
                        self.status_bar.update_left("Loading Sent Directs...")
                        self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/favourites" and len(tokens) == 1:
                        self.status_bar.update_left("Loading Favourites...")
                        self.tabs.append(Timeline(self.conn, self.notice_window, "favourites", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/search" and len(tokens) >= 2:
                        self.status_bar.update_left("Searching...")
                        query = " ".join(tokens[1:])
                        self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':query}, filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/home" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "home", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/mentions" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "mentions", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/directs" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "direct", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/public" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "public", notice_limit=self.config['notice_limit'], filters=self.config['filters'], compact_style=self.config['compact_notices'], user_rainbow=self.config['user_rainbow'], tag_rainbow=self.config['tag_rainbow'], group_rainbow=self.config['group_rainbow'], expand_remote=self.config['expand_remote']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/config" and len(tokens) >= 3:
                        keys, value = tokens[1].split('.'), " ".join(tokens[2:])
                        if len(keys) == 2:      # there has to be a clean way to avoid hardcoded len checks, but I can't think what right now, and technically it works for all currently valid config keys
                            self.config[keys[0]][keys[1]] = value
                        else:
                            self.config[keys[0]] = value
                        open(self.config_file, 'w').write(json.dumps(self.config, indent=4))
    
                    elif tokens[0] == "/alias" and len(tokens) >= 3:
                        self.status_bar.update_left("Creating alias...")
                        alias, command = tokens[1], " ".join(tokens[2:])
                        if alias[0] != "/":
                            alias = "/" + alias
                        if command[0] != "/":
                            command = "/" + command
                        self.config["aliases"][alias] = command
                        open(self.config_file, 'w').write(json.dumps(self.config, indent=4))

                    elif tokens[0] == "/link":
                        dent_index = int(tokens[2]) - 1
                        if tokens[1] == "*":
                            self.status_bar.update_left("Opening links...")
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text']):
                                    subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                            else:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text']):
                                    subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                        else:
                            self.status_bar.update_left("Opening link...")
                            link_index = int(tokens[1]) - 1
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text'])[link_index]
                            else:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text'])[link_index]
                            subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

                    elif tokens[0] == "/bugreport" and len(tokens) >= 2:
                        self.status_bar.update_left("Reporting bug...")
    
                        status = "#icursebug " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=self.config['long_dent'], dup_first_word=True)
   
                    elif tokens[0] == "/featurerequest" and len(tokens) >= 2:
                        self.status_bar.update_left("Posting feature request...")
    
                        status = "#icurserequest " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=self.config['long_dent'], dup_first_word=True)
   
                except StatusNetError, e:
                    self.status_bar.timed_update_left("Status.Net error %d: %s" % (e.errcode, e.details))
            else:
                self.status_bar.update_left("Posting Notice...")
                try:
                    update = self.conn.statuses_update(input, source="IdentiCurse", long_dent=self.config['long_dent'])
                except Exception, (errmsg):
                    self.status_bar.timed_update_left("ERROR: Couldn't post status: %s" % (errmsg))

        if hasattr(self.tabs[self.current_tab], 'timeline_type'):
            if update != False and (self.tabs[self.current_tab].timeline_type == 'home' or self.tabs[self.current_tab].timeline_type == 'mentions'):
                if isinstance(update, list):
                    for notice in update:
                        self.tabs[self.current_tab].timeline.insert(0, notice)
                else:
                    self.tabs[self.current_tab].timeline.insert(0, update)
                self.tabs[self.current_tab].update_buffer()
                self.status_bar.update_left("Doing nothing.")
            else:
                self.tabs[self.current_tab].update()
        elif update != False and self.tabs[self.current_tab].name == "Context":
            self.tabs[self.current_tab].timeline.insert(0, update)
            self.tabs[self.current_tab].update_buffer()
            self.status_bar.update_left("Doing nothing.")
        else:
            self.tabs[self.current_tab].update()
          

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.tabs[self.current_tab].search_highlight_line = -1
        self.display_current_tab()
        self.status_bar.update_left("Doing nothing.")
        self.insert_mode = False
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def parse_search(self, query):
        if query is not None:
            query = query.rstrip()
            if query == "":
                query = self.last_page_search['query']
            if (self.last_page_search['query'] == query) and not (query == "") and (self.last_page_search['tab'] == self.current_tab):
                # this is a continued search
                if self.last_page_search['viewing'] < (len(self.last_page_search['occurs']) - 1):
                    self.last_page_search['viewing'] += 1
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    self.status_bar.update_left("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, query))
                    self.display_current_tab()
                else:
                    self.tabs[self.current_tab].search_highlight_line = -1
                    self.status_bar.update_left("No more results for '%s'" % (query))
            else:
                # new search
                maxx = self.tabs[self.current_tab].window.getmaxyx()[1]
                search_buffer = self.tabs[self.current_tab].buffer.reflowed(maxx - 2)

                page_search = {'query':query, 'occurs':[], 'viewing':0, 'tab':self.current_tab}
                
                for line_index in range(len(search_buffer)):
                    match_found = False
                    for block in search_buffer[line_index]:
                        if self.config['search_case_sensitive'] == "sensitive":
                            if query in block[0]:
                                match_found = True
                                break
                        else:
                            if query.upper() in block[0].upper():
                                match_found = True
                                break
                    if match_found:
                        page_search['occurs'].append(line_index)

                if len(page_search['occurs']) > 0:
                    self.tabs[self.current_tab].scrollto(page_search['occurs'][0])
                    self.tabs[self.current_tab].search_highlight_line = page_search['occurs'][0]
                    self.status_bar.update_left("Viewing result #1 for '%s'" % (query))
                    self.last_page_search = page_search  # keep this search
                else:
                    self.tabs[self.current_tab].search_highlight_line = -1
                    self.status_bar.update_left("No results for '%s'" % (query))
                    self.last_page_search = {'query':"", 'occurs':[], 'viewing':0, 'tab':-1}  # reset to no search
        else:
            self.status_bar.update_left("Doing nothing.")

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.display_current_tab()
        self.insert_mode = False
        self.search_mode = False
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def quit(self):
        self.update_timer.cancel()
        curses.endwin()
        sys.exit()
