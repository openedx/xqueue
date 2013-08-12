#!/usr/bin/python
"""
An example external grader.
This app runs on Flask, a lightweight Python web framework.
You will need to install Flask to use this - pip install flask should work.
"""

import json
import requests
from flask import Flask, request, Response
app = Flask(__name__)

@app.route('/', methods=['POST'])
def grade():
    """
    A sample grader.
    """
    data = json.loads(request.data)
    # data['xqueue_body']['files'] contains a dictionary mapping file names to file
    # locations.  In this grader, the student is only allowed to submit one file.
    file_loc = json.loads(data['xqueue_body'])['files'].values()[0]
    print file_loc
    user_code = requests.get(file_loc).text
    print user_code
    # Do grading things here.
    resp = Response(
        response='{"correct": true, "score": 1, "msg": "<p>Great! You got the right answer!</p>"}',
        content_type='application/json'
    )
    return resp

if __name__ == '__main__':
    app.run(port=1234)