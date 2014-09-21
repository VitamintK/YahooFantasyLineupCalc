import requests
from oauth_hook import OAuthHook
from requests import request
from urlparse import parse_qs
import webbrowser
import csv

GET_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_token'
AUTHORIZATION_URL = 'https://api.login.yahoo.com/oauth/v2/request_auth'
REQUEST_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_request_token'
CALLBACK_URL = 'oob'

class YHandler(object):

    def __init__(self, authf):
        print 'init'
        self.authf = authf
        self.authd = self.get_authvals_csv(self.authf)
        self.session = requests.session()


    def get_authvals_csv(self, authf):
        print 'get_authvals_csv'
        vals = {}   #dict of vals to be returned
        with open(authf, 'rb') as f:
            f_iter = csv.DictReader(f)
            vals = f_iter.next()
        return vals
        

    def write_authvals_csv(self, authd, authf):
        print 'write_authvals_csv'
        f = open(authf, 'wb')
        fieldnames = tuple(authd.iterkeys())
        headers = dict((n,n) for n in fieldnames)
        f_iter = csv.DictWriter(f, fieldnames=fieldnames)
        f_iter.writerow(headers)
        f_iter.writerow(authd)
        f.close

    def reg_user(self):
        print "reg_user"
        init_oauth_hook = OAuthHook(consumer_key=self.authd['consumer_key'], consumer_secret=self.authd['consumer_secret'])
        #http://stackoverflow.com/questions/15765210/python-requests-library-pre-request-hook
        request = requests.Request('POST', REQUEST_TOKEN_URL, params={'oauth_callback': CALLBACK_URL})
        request = init_oauth_hook(request)
        prepared = request.prepare()
        response = self.session.send(prepared)
                
        #response = requests.post(REQUEST_TOKEN_URL, params={'oauth_callback': CALLBACK_URL}, hooks={'pre_request': init_oauth_hook})
        qs = parse_qs(response.text)
        print qs.items()
        self.authd['oauth_token']= (qs['oauth_token'][0])
        self.authd['oauth_token_secret'] = (qs['oauth_token_secret'][0])
        
        #now send user to approve app
        print "You will now be directed to a website for authorization.\nPlease authorize the app, and then copy and paste the provide PIN below."
        webbrowser.open("%s?oauth_token=%s" % (AUTHORIZATION_URL, self.authd['oauth_token']))
        self.authd['oauth_verifier'] = raw_input('Please enter your PIN: ')

        #get final auth token
        self.get_login_token()

    def get_login_token(self):
        print "get_login_token"
        oauth_hook = OAuthHook(self.authd['oauth_token'], self.authd['oauth_token_secret'], self.authd['consumer_key'], self.authd['consumer_secret'])

        print "oauth_verifier: {0}".format(self.authd['oauth_verifier'])
        request = requests.Request('POST', GET_TOKEN_URL, params={'oauth_verifier': self.authd['oauth_verifier']})
        request = oauth_hook(request)
        prepared = request.prepare()
        response = self.session.send(prepared)
        print "line 73"
        
        #response = requests.post(GET_TOKEN_URL, {'oauth_verifier': self.authd['oauth_verifier']}, hooks={'pre_request': oauth_hook})
        qs = parse_qs(response.content)
        print qs.items()
        self.authd.update(map(lambda d: (d[0], (d[1][0])), qs.items()))
        self.write_authvals_csv(self.authd, self.authf)
        return response

    def refresh_token(self):
        print 'refresh_token'
        oauth_hook = OAuthHook(access_token=self.authd['oauth_token'], access_token_secret=self.authd['oauth_token_secret'], consumer_key=self.authd['consumer_key'], consumer_secret=self.authd['consumer_secret'])

        request = requests.Request('POST', GET_TOKEN_URL, params={'oauth_session_handle': self.authd['oauth_session_handle']})
        request = oauth_hook(request)
        prepared = request.prepare()
        response = self.session.send(prepared)

        #response = requests.post(GET_TOKEN_URL, {'oauth_session_handle': self.authd['oauth_session_handle']}, hooks={'pre_request': oauth_hook})
        qs = parse_qs(response.content)
        self.authd.update(map(lambda d: (d[0], (d[1][0])), qs.items()))
        self.write_authvals_csv(self.authd, self.authf)


    def call_api(self, url, req_meth='GET', data=None, headers=None):
        print 'call_api'
        req_oauth_hook = OAuthHook(self.authd['oauth_token'], self.authd['oauth_token_secret'], self.authd['consumer_key'], self.authd['consumer_secret'], header_auth=True)

        request = requests.Request(method=req_meth, url=url, data=data, headers=headers)
        request = req_oauth_hook(request)
        prepared = request.prepare()
        response = self.session.send(prepared)

        #client = requests.session(hooks={'pre_request':req_oauth_hook})
        return response
        #client.request(method=req_meth, url=url, data=data, headers=headers)

    def api_req(self, querystring, req_meth='GET', data=None, headers=None):
        print 'api_req'
        base_url = 'http://fantasysports.yahooapis.com/fantasy/v2/'
        url = base_url + querystring
        if ('oauth_token' not in self.authd) or ('oauth_token_secret' not in self.authd) or (not (self.authd['oauth_token'] and self.authd['oauth_token_secret'])):
            self.reg_user()
        query = self.call_api(url, req_meth, data=data, headers=headers)
        if query.status_code != 200: #We have both authtokens but are being rejected. Assume token expired. This could be a LOT more robust
            self.refresh_token()
            query = self.call_api(url, req_meth, data=data, headers=headers)
        return query

    
