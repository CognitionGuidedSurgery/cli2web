import uuid
import xml.etree.ElementTree as ET
import subprocess
import mimetypes
import tempfile

from flask import Flask, render_template, request, current_app, send_from_directory, url_for
from path import Path

from clictk import *

OUTPUT_DIRECTORIES = {
    "TEST": "/tmp/test"
}

class CLIResource(object):
    def __init__(self, executable):
        self._executable = executable

        p = subprocess.Popen([executable, "--xml"], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        p.wait()
        self._xml = ET.fromstring(p.stdout.read())
        self._model = Executable.from_etree(self._xml)
        self.__name__ = str(self.name)

    @property
    def name(self):
        return self._model.title

    def get(self):
        return render_template("cli.html", model=self._model)

    def post(self):
        flags = {}
        dir = Path(tempfile.mkdtemp())

        for g in self._model.parameter_groups:
            for p in g:
                try:  # must be a file
                    fil = request.files[p.longflag]
                    if fil:  # check for empty file inputs
                        place = dir / fil.filename
                        print "Save", place
                        fil.save(place)
                        flags[p.longflag] = place
                except KeyError:
                    val = request.values.get(p.longflag, None)

                    if val is None or val == p.default or val == "":
                        continue

                    if p.type == 'boolean':
                        if val == 'true':
                            flags[p.longflag] = ""
                    else:
                        flags[p.longflag] = val

        template = current_app.jinja_env.get_template("job.tpl.sh")
        j = template.render(executable=self._executable, flags=flags)

        jobfile = dir / "job.sh"
        with open(jobfile, 'w') as fp:
            fp.write(j)

        os.chmod(jobfile, 0755)

        sp = subprocess.Popen(jobfile, cwd=dir)
        sp.wait()

        token = str(uuid.uuid4())

        OUTPUT_DIRECTORIES[token] = dir

        return "%s <a href='%s'>%s</a>" % ("SUCCESS" if sp.returncode == 0 else "ERROR",url_for("list", token=str(token)), token)


def setup(executables):
    """create a flask web application, exposing every given `executable` as a webservice
    :param executables:
    :type executables: list
    :return:
    """
    app = Flask(__name__)
    # api = Api(app)

    resources = map(CLIResource, executables)

    for r in resources:
        app.route("/%s" % r.name, methods=['GET'], endpoint=r.name)(r.get)
        app.route("/%s" % r.name, methods=['POST'], endpoint="post_" + r.name)(r.post)

    @app.route('/')
    def hello_world():
        return render_template("overview.html", resources=resources)

    @app.route("/get/<string:token>")
    def list(token):
        try:
            pth = Path(OUTPUT_DIRECTORIES[token])

            if not pth.exists():
                raise KeyError()

            files = pth.listdir()

            return render_template("dir.html", token=token, files=files)

        except KeyError:
            print OUTPUT_DIRECTORIES
            return "Token invalid"


    @app.route("/get/<string:token>/<path:filename>")
    def get(token, filename):
        try:
            pth = Path(OUTPUT_DIRECTORIES[token])
            filename = pth / filename

            if not pth.exists():
                return 404, "File not exists"

            return send_from_directory(filename.dirname(), filename.name)

        except KeyError:
            return "Token invalid"


    @app.route('/js/<path:path>')
    def send_js(path):
        return send_from_directory('js', path)

    return app


import os