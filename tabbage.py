#!/usr/bin env python
import re
import threading

class TabUpdater(threading.Thread):
    def __init__(self, tabs, callback_object, callback_function):
        threading.Thread.__init__(self)
        self.tabs = tabs
        self.callback_object = callback_object
        self.callback_function = callback_function

    def run (self):
        for tab in self.tabs:
            tab.update()

        fun = getattr(self.callback_object, self.callback_function)
        fun()

class Tab(object):
    def __init__(self, window):
        self.window = window
        self.buffer = []
        self.start_line = 0
        self.html_regex = re.compile("<(.|\n)*?>") 
    
    def scrollup(self, n):
        self.start_line -= n
        if self.start_line < 0:
            self.start_line = 0

    def scrolldown(self, n):
        self.start_line += n
        if self.start_line > len(self.buffer) - (self.window.getmaxyx()[0] - 3):
            self.start_line = len(self.buffer) - (self.window.getmaxyx()[0] - 3)

    def display(self):
        self.window.erase()
        self.window.addstr("\n".join(self.buffer[self.start_line:self.window.getmaxyx()[0] - 3 + self.start_line]).encode("utf-8"))
        self.window.refresh()

class Help(Tab):
    def __init__(self, window):
        self.name = "Help"
        Tab.__init__(self, window) 

    def update(self):
        self.update_buffer()

    def update_buffer(self):
        self.buffer = open('README', 'r').read().split("\n")

class Timeline(Tab):
    def __init__(self, conn, window, timeline, type_params={}):
        self.conn = conn
        self.timeline = []
        self.timeline_type = timeline
        self.type_params = type_params

        if self.timeline_type == "user":
            self.name = "User (%s)" % self.type_params['screen_name']
        elif self.timeline_type == "tag":
            self.name = "Tag (%s)" % self.type_params['tag']
        elif self.timeline_type == "group":
            self.name = "Group (%s)" % self.type_params['nickname']
        elif self.timeline_type == "search":
            self.name = "Search (%s)" % self.type_params['query']
        elif self.timeline_type == "sentdirect":
            self.name = "Sent Directs"
        else:
            self.name = self.timeline_type.capitalize()

        Tab.__init__(self, window)

    def update(self):
        if self.timeline_type == "home":
            self.timeline = self.conn.statuses_home_timeline(count=25, page=0)
        elif self.timeline_type == "mentions":
            self.timeline  = self.conn.statuses_mentions(count=25, page=0)
        elif self.timeline_type == "direct":
            self.timeline = self.conn.direct_messages(count=25, page=0)
        elif self.timeline_type == "public":
            self.timeline = self.conn.statuses_public_timeline()
        elif self.timeline_type == "user":
            self.timeline = self.conn.statuses_user_timeline(user_id=self.type_params['user_id'], screen_name=self.type_params['screen_name'], count=25, page=0)
        elif self.timeline_type == "group":
            self.timeline = self.conn.statusnet_groups_timeline(group_id=self.type_params['group_id'], nickname=self.type_params['nickname'], count=25, page=0)
        elif self.timeline_type == "tag":
            self.timeline = self.conn.statusnet_tags_timeline(tag=self.type_params['tag'], count=25, page=0)
        elif self.timeline_type == "sentdirect":
            self.timeline = self.conn.direct_messages_sent(count=25, page=0)
        elif self.timeline_type == "favourites":
            self.timeline = self.conn.favorites(page=0)
        elif self.timeline_type == "search":
            self.timeline = self.conn.search(self.type_params['query'], page=0, standardise=True)

        self.update_buffer()

    def update_buffer(self):
        self.buffer = []

        maxx = self.window.getmaxyx()[1]
        c = 1

        for n in self.timeline:
            if "direct" in self.timeline_type:
                user = unicode("%s -> %s" % (n["sender"]["screen_name"], n["recipient"]["screen_name"]))
                source_msg = ""
            else:
                user = unicode(n["user"]["screen_name"])
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)
                if n["in_reply_to_status_id"] is not None:
                    source_msg += " [+]"
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1
            self.buffer[y] += ' ' * 3
            self.buffer[y] += user
            self.buffer[y] += ' ' * (maxx - ((len(source_msg) + (len(user)) + 6)))
            self.buffer[y] += source_msg

            try:
                self.buffer.append(n['text'])
            except UnicodeDecodeError:
                self.buffer += "Caution: Terminal too shit to display this notice"

            self.buffer.append("")
            self.buffer.append("")

            c += 1

class Context(Tab):
    def __init__(self, conn, window, notice_id):
        self.conn = conn
        self.notice = notice_id
        self.timeline = []

        self.name = "Context"

        Tab.__init__(self, window)

    def update(self):
        self.timeline = []
        next_id = self.notice

        while next_id is not None:
            self.timeline += [self.conn.statuses_show(id=next_id)]
            next_id = self.timeline[-1]['in_reply_to_status_id']

        self.update_buffer()

    def update_buffer(self):
        self.buffer = [] 

        c = 1

        maxx = self.window.getmaxyx()[1]

        for n in self.timeline:
            user = unicode(n["user"]["screen_name"])
            raw_source_msg = "from %s" % (n["source"])
            source_msg = self.html_regex.sub("", raw_source_msg)
            if n["in_reply_to_status_id"] is not None:
                source_msg += " [+]"
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1
            self.buffer[y] += ' ' * 3
            self.buffer[y] += user
            self.buffer[y] += ' ' * (maxx - ((len(source_msg) + (len(user)) + 6)))
            self.buffer[y] += source_msg

            try:
                self.buffer.append(n['text'])
            except UnicodeDecodeError:
                self.buffer += "Caution: Terminal too shit to display this notice"

            self.buffer.append("")
            self.buffer.append("")

            c += 1

class Profile(Tab):
    def __init__(self, conn, window, id):
        self.conn = conn
        self.id = id

        self.name = "Profile (%s)" % self.id

        Tab.__init__(self, window)

    def update(self):
        self.profile = self.conn.users_show(screen_name=self.id)
        self.update_buffer()

    def update_buffer(self):
        self.buffer = []
        self.buffer.append(self.profile['screen_name'].capitalize().encode("utf-8") + "'s Profile")
        self.buffer.append("")
        self.buffer.append("")

        if self.profile['name']:
            self.buffer.append("Real Name: " + self.profile['name'])
            self.buffer.append("")
       
        if self.profile['description']:
            self.buffer.append("Bio: " + self.profile['description'])
            self.buffer.append("")

        if self.profile['statuses_count']:
            self.buffer.append("Notices: " + str(self.profile['statuses_count']))
