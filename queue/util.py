import hashlib


def make_hashkey(seed):
    '''
    Generate a hashkey (string)
    '''
    h = hashlib.md5()
    h.update(seed.encode('utf-8'))
    return h.hexdigest()

def get_request_ip(request):
    '''
    Retrieve the IP origin of a Django request
    '''
    ip = request.META.get('HTTP_X_REAL_IP','') # nginx reverse proxy
    if not ip:
        ip = request.META.get('REMOTE_ADDR','None')
    return ip
