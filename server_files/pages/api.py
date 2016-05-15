# coding=utf-8
from utils import mysql, upload_module as util_upload
from flask import request, Blueprint, jsonify
from zipfile import ZipFile
import json
from lxml import etree


api = Blueprint('api', __name__)

# TODO: secure file names

@api.route("/check_module")
def check_module():
    # if request.method != 'GET':
    #     return jsonify(code=405, error='Method not allowed')
    name = request.args.get('name', '')
    if name == '':
        return jsonify(code=502, error='No module name in request')
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM Module WHERE name=%s", (name,))
    data = cursor.fetchall()
    if data:
        # вернет первую найденную версию
        return jsonify(code=200, name=name, exists=True, version=data[0][0])
    else:
        return jsonify(code=200, name=name, exists=False)


@api.route("/register_module", methods=['POST'])
def upload_module():
    archive = request.files['archive']
    if not archive:
        return "no zip archive"
    res = util_upload(archive)
    if res != "ok":
        return res
    return "ok"
