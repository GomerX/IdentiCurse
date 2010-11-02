#!/usr/bin/env python
import urllib, urllib2, json

class StatusNet(object):
    def __init__(self, api_path, username, password):
        import base64
        self.api_path = api_path
        self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
    
    def __makerequest(self, resource_path, raw_params={}):
        params = urllib.urlencode(raw_params)
        
        if len(params) > 0:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path), params)
        else:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path))
        request.add_header("Authorization", "Basic %s" % (self.auth_string))
        
        try:
            response = urllib2.urlopen(request)
            content = response.read()

            return json.loads(content)
        except:
            return []

    def statuses_update(self, status, source="", in_reply_to_status_id=0):
        params = {'status':status}
        if not (source == ""):
            params['source'] = source
        if not (in_reply_to_status_id == 0):
            params['in_reply_to_status_id'] = in_reply_to_status_id
        
        return self.__makerequest("statuses/update", params)
    
    def statuses_mentions(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/mentions", params)

    def statuses_friends_timeline(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/friends_timeline", params)

    def statuses_home_timeline(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        
        return self.__makerequest("statuses/home_timeline", params)

    def statuses_public_timeline(self):
        return self.__makerequest("statuses/public_timeline")

    def statuses_retweet(self, id):
        return self.__makerequest("statuses/retweet/%d" % (id))

    def statuses_user_timeline(self, user_id=0, screen_name="", since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/user_timeline", params)

    def direct_messages(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        
        return self.__makerequest("direct_messages", params)

