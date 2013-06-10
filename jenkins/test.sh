#! /bin/bash

set -e
set -x

function github_status {
    gcli status create edx xqueue $GIT_COMMIT \
         --params=$1 \
                  target_url:$BUILD_URL \
                  description:"Build #$BUILD_NUMBER $2" \
         -f csv
}

function github_mark_failed_on_exit {
    trap '[ $? == "0" ] || github_status state:failure "failed"' EXIT
}

git remote prune origin

github_mark_failed_on_exit
github_status state:pending "is running"

# Set the IO encoding to UTF-8 so that askbot will start
export PYTHONIOENCODING=UTF-8

GIT_BRANCH=${GIT_BRANCH/HEAD/master}
if [ ! -d /mnt/virtualenvs/"$JOB_NAME" ]; then
    mkdir -p /mnt/virtualenvs/"$JOB_NAME"
    virtualenv /mnt/virtualenvs/"$JOB_NAME"
fi

source /mnt/virtualenvs/"$JOB_NAME"/bin/activate
pip install -q -r pre-requirements.txt
pip install -q -r requirements.txt

rake clobber
rake pep8 || echo "pep8 failed, continuing"
rake pylint || echo "pylint failed, continuing"
rake test

github_status state:success "passed"
