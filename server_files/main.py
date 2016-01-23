# coding=utf-8
import os
import sys
import ConfigParser
from zipfile import ZipFile
from werkzeug.utils import secure_filename

from flask import Flask
from flask import render_template
from flask import request
from flaskext.mysql import MySQL

app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('../conf/server.ini')
database_config_section = 'database'

app.config['MYSQL_DATABASE_USER'] = config.get(database_config_section, 'user')
app.config['MYSQL_DATABASE_PASSWORD'] = config.get(database_config_section, 'password')
app.config['MYSQL_DATABASE_DB'] = config.get(database_config_section, 'db')
app.config['MYSQL_DATABASE_HOST'] = config.get(database_config_section, 'host')

mysql = MySQL()
mysql.init_app(app)

# открывает файлы в diplom ((?)где запускают uwsgi)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/upload_module", methods=['POST',])
def upload_module():
    archive = request.files['archive']
    # archive = False
    if archive:
        module_name = secure_filename(archive.filename).rsplit('.', 1)[0]
        with ZipFile(archive) as zip_archive:
            os.makedirs('lua/modules/' + module_name)
            zip_archive.extractall('lua/modules/' + module_name + '/')
    return render_template("admin.html")


@app.route("/create_test")
def create_test():
    os.makedirs('lua/modules/test/')
    with open('lua/modules/test/sample.lua', 'w') as f:
        f.write('ngx.say("hi from test")')
    return "from create!"

if __name__ == "__main__":
    app.run()
