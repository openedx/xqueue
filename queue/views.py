from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse 
from django.views.decorators.csrf import csrf_exempt

import json

# Xqueue reply format:
#    JSON-serialized dict:
#    { 'return_code': 0(success)/1(error),
#      'content'    : 'my content', }
#--------------------------------------------------


class XQueueResponse(HttpResponse):
    def __init__(self, success, content):
        return_code = 0 if success else 1
        resp = json.dumps({ 'return_code': return_code,
                            'content': content })
        super(XQueueResponse, self).__init__(resp, content_type="application/json")


# Log in
#--------------------------------------------------
@csrf_exempt
def log_in(request):
    resp = (False, "login_required")
    if request.method == 'POST':
        p = request.POST.copy()
        if p.has_key('username') and p.has_key('password'):
            user = authenticate(username=p['username'], password=p['password'])
            if user is not None:
                login(request, user)
                resp = (True, 'Logged in')
            else:
                resp = (False, 'Incorrect login credentials')
        else:
            resp = (False, 'Insufficient login info')

    return XQueueResponse(*resp)

def log_out(request):
    logout(request)
    return XQueueResponse(success=True, content='Goodbye')

# Status check
#--------------------------------------------------
def status(request):
    return XQueueResponse(success=True, content='OK')
