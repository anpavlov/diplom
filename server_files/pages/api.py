# coding=utf-8
from ext import mysql
from flask import request, Blueprint, jsonify
from zipfile import ZipFile
import json

api = Blueprint('api', __name__)


# TODO: secure file names
# {
#   "name": "supermodule"
#   "":""
# }
#
#

@api.route("/check_module")
def check_module():
    if request.method != 'GET':
        return jsonify(code=405, error='Method not allowed')
    name = request.args.get('name', '')
    if name == '':
        return jsonify(code=502, error='No module name in request')
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Module WHERE name=%s", (name,))
    if cursor.fetchall():
        return jsonify(code=200, name=name, exists=True)
    else:
        return jsonify(code=200, name=name, exists=False)


@api.route("/register_module", methods=['POST'])
def upload_module():
    archive = request.files['archive']
    # archive = False
    if archive:
        # module_name = secure_filename(archive.filename).rsplit('.', 1)[0]
        with ZipFile(archive) as zip_archive:
            # os.makedirs('lua/modules/' + module_name)
            # zip_archive.extractall('lua/modules/' + module_name + '/')
            try:
                with zip_archive.open('manifest.json') as manifest_file:
                    # manifest_json = manifest_file.read()
                    manifest = json.loads(manifest_file.read())
            except KeyError:
                return "no manifest"

            try:
                module_name = manifest['name']
                module_version = manifest['version']
                module_urls = manifest['urls']
            except KeyError as err:
                return "no module " + err.args[0]

            if not isinstance(module_name, basestring):
                return "name is not a string"

            if not isinstance(module_version, basestring):
                return "version is not a string"

            if not isinstance(module_urls, list):
                return "urls is not a list"

            for url in module_urls:
                if not isinstance(url, basestring):
                    return "url is not a string"
                if not "urls/{}.lua".format(url) in zip_archive.namelist():
                    return "no lua script"

            with ZipFile('modules/archives/{}{}.zip'.format(module_name, module_version), 'w') as zip_out:
                for file_name in zip_archive.namelist():
                    zip_out.writestr(file_name, zip_archive.read(file_name))

        connection = mysql.connect()
        cursor = connection.cursor()

        cursor.execute("INSERT INTO Module (name, version) VALUES (%s, %s)", (module_name, module_version))
        connection.commit()
        return "ok"

    else:
        return "no zip archive"
