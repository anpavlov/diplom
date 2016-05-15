# coding=utf-8
import os
# import ConfigParser
import settings
import lupa
import json

# from werkzeug.utils import secure_filename

from utils import mysql

from flask import Flask
# from flask import render_template
# from flask import request
from pages.admin import admin
from pages.api import api

app = Flask(__name__)

app.config['DEBUG'] = True
app.config.from_object(settings)

mysql.init_app(app)

# открывает файлы в diplom ((?)где запускают uwsgi)
app.register_blueprint(admin)
app.register_blueprint(api, url_prefix='/api')

fdb_str = '''
function ()
    local m = require("luasql.mysql")
    local env = m.mysql()
    local cn = env:connect("{}", "{}", "{}")
    return cn
end
'''


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/api/<module_name>/<module_method>")
def module_api(module_name, module_method):
    lua = lupa.LuaRuntime()
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, approved, activated FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None or data[1] != 1 or data[2] != 1:
        return "no module"
    if not os.path.isfile("lua/modules/{}/{}.lua".format(module_name, module_method)):
        return "no method"
    sandbox = lua.eval("{}")
    sandbox['string'] = lua.eval("string")
    sandbox['math'] = lua.eval("math")
    sandbox['db'] = lua.eval(fdb_str.format(settings.MYSQL_DATABASE_DB, "m{}".format(data[0]), "qwe123"))()
    setfenv = lua.eval("setfenv")
    setfenv(0, sandbox)

    # TODO: check lua norm (syntax errors)
    with open("lua/modules/{}/{}.lua".format(module_name, module_method)) as f:
        lua_code = f.read()
    method = lua.eval(lua_code)
    return json.dumps(dict(method()))


@app.route("/create_test")
def create_test():
    os.makedirs('lua/modules/test/')
    with open('lua/modules/test/sample.lua', 'w') as f:
        f.write('ngx.say("hi from test")')
    return "from create!"

if __name__ == "__main__":
    app.run()
