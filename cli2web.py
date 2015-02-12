import uuid
import xml.etree.ElementTree as ET
import subprocess
import mimetypes
import tempfile

from flask import Flask, render_template, request, current_app, send_from_directory, url_for
from path import Path


OUTPUT_DIRECTORIES = {
    "TEST": "/tmp/test"
}


class XMLArgumentNotSupportedByExecutable(BaseException):
    pass


class CLI(object):
    class Parameters(list):
        def __init__(self, *args):
            super(CLI.Parameters, self).__init__(*args)

            self.label = None
            self.description = None
            self.advanced = None


    class Parameter(object):
        def __init__(self, name, type, default, doc="", channel=None, values=None,
                     index=None, label=None, longflag=None, file_ext=None
        ):
            self.name = name
            self.type = type
            self.default = default
            self.doc = doc
            self.channel = channel

            self.values = values

            self.label = label
            self.index = index
            self.longflag = longflag
            self.file_ext = file_ext

        @property
        def pattern(self):
            PATTERN = {
                'string': "\w*",
                'integer': "\d+",
                'float': "^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$"}
            try:
                return PATTERN[self.type]
            except:
                if self.file_ext:
                    pattern = ["(.+%s)" % sfx.replace('.', r'\.') for sfx in self.file_ext.split(",")]
                    return "|".join(pattern)
                else:
                    return "\w*"


        @property
        def accept(self):
            def translate(sfx):
                m = mimetypes.guess_type("abc" + sfx, False)[0]
                if m:
                    return m
                return "application/octet"

            if self.file_ext:
                mimes = filter(bool, map(translate, self.file_ext.split(',')))
                print mimes
                return ' '.join(mimes)
            else:
                return str()

        @staticmethod
        def from_xml_node(xml_node):
            """constructs a CLI.Parameter from an xml node.
            :param xml_node:
            :type xml_node: xml.etree.ElementTree.Element
            :rtype: CLI.Parameter
            :return:
            """

            def gather_enum_values():
                l = []
                for element in xml_node.iterfind('element'):
                    l.append(element.text)
                return l

            name = xml_node.findtext("name")
            type = xml_node.tag

            if type in ("label", "description"): return None

            default = xml_node.findtext("default")

            longflag = xml_node.findtext('longflag')

            if default:
                default = default.replace('"', '').replace("'", '')

            index = xml_node.findtext('index')

            label = xml_node.findtext('label') or name or longflag

            doc = xml_node.findtext('description')

            values = gather_enum_values()

            channel = xml_node.findtext('channel')

            file_ext = xml_node.attrib.get('fileExtensions', None)

            return CLI.Parameter(name, type, default, doc, channel, values=values, index=index, label=label,
                                 longflag=longflag, file_ext=file_ext)

    def __init__(self, xml, name=None):
        """Creates a model about every fact from the CLI XML
        :param xml:
        :type xml: xml.etree.ElementTree.ElementTree
        :return:
        """
        self._xml = xml
        self.category = xml.findtext('category')
        self.title = xml.findtext('title') or self.name
        self.description = xml.findtext('description')
        self.license = xml.findtext('license') or "unknown"
        self.contributor = xml.findtext('contributor')

        self.name = name

        self.parameter_groups = []
        for ps in xml.iterfind("parameters"):
            assert isinstance(ps, ET.Element)
            paras = CLI.Parameters(
                filter(lambda x: x is not None,
                       map(CLI.Parameter.from_xml_node, list(ps))))

            paras.label = ps.findtext("label")
            paras.description = ps.findtext("description")
            paras.advanced = ps.attrib.get('advanced', "false") == "true"

            self.parameter_groups.append(paras)


    @staticmethod
    def from_xml(executable):
        command = "%s --xml" % executable
        sp = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        sp.wait()
        if sp.returncode == 0:
            xml = sp.stdout.read()
            tree = ET.fromstring(xml)
            return CLI(tree, name=Path(executable).namebase)
        else:
            raise XMLArgumentNotSupportedByExecutable("called %s got %s" % (command, sp.returncode))


class CLIResource(object):
    def __init__(self, executable):
        self._executable = executable
        self._model = CLI.from_xml(executable)

        self.__name__ = str(self.name)

    @property
    def name(self):
        return self._model.name

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