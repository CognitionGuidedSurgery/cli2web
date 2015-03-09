FROM wadoon/python

MAINTAINER Alexander Weigl <alexander.weigl@student.kit.edu>

ADD .  /tmp/cli2web
RUN pip install --pre /tmp/cli2web && rm -rf /tmp/cli2web

ENTRYPOINT cli2web