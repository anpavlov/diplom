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
from flask import request, render_template_string, redirect
from pages.admin import admin
from pages.api import api

app = Flask(__name__)

app.config['DEBUG'] = True
app.config.from_object(settings)

mysql.init_app(app)

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
    return redirect("/login")


@app.route("/html/<module_name>/<html_file>.html")
def html_file(module_name, html_file):
    if not os.path.isfile("modules/html/{}/{}.html".format(module_name, html_file)):
        return "Нет такого файла"
    with open("modules/html/{}/{}.html".format(module_name, html_file), 'r') as html_f:
        html_text = unicode(html_f.read(), 'utf-8')
    if not os.path.isfile("modules/html/{}/{}.lua".format(module_name, html_file)):
        return render_template_string(html_text)
    lua = lupa.LuaRuntime()
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, approved, activated, has_settings FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None or data[1] != 1 or data[2] != 1:
        return "no module"

    sandbox = lua.eval("{}")
    sandbox['string'] = lua.eval("string")
    sandbox['math'] = lua.eval("math")
    sandbox['error'] = lua.eval("error")
    sandbox['tonumber'] = lua.eval("tonumber")
    sandbox['db'] = lua.eval(fdb_str.format(settings.MYSQL_DATABASE_DB, "m{}".format(data[0]), "qwe123"))()

    args = dict(request.args)
    sandbox['args'] = lua.table_from(args)

    mod_settings = {}
    if data[3] == 1:
        cursor.execute("SELECT name, type, value FROM Module_setting WHERE module_id=%s", (data[0],))
        sd = cursor.fetchall()
        for row in sd:
            val = row[2]
            if row[1] == 'int':
                val = int(val)
            elif row[1] == 'boolean':
                val = True if val == "true" else False
            mod_settings[row[0]] = val
    if len(mod_settings) != 0:
        sandbox['settings'] = lua.table_from(mod_settings)

    setfenv = lua.eval("setfenv")
    setfenv(0, sandbox)

    with open("modules/html/{}/{}.lua".format(module_name, html_file), 'r') as f:
        lua_code = f.read()
    try:
        method = lua.eval(lua_code)
    except lupa.LuaSyntaxError:
        return "lua syntax error"
    # except:
    #     return "error occurred"
    try:
        res = to_dict(method())
    except lupa.LuaError as e:
        return "lua error: {}".format(e)
    # except:
    #     return "error occurred"
    return render_template_string(html_text, **res)


@app.route("/api/<module_name>/<module_method>", methods=["POST", "GET"])
def module_api(module_name, module_method):
    lua = lupa.LuaRuntime()
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, approved, activated, has_settings FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None or data[1] != 1 or data[2] != 1:
        return "no module"
    if not os.path.isfile("lua/modules/{}/{}.lua".format(module_name, module_method)):
        return "no method"

    sandbox = lua.eval("{}")
    sandbox['string'] = lua.eval("string")
    sandbox['math'] = lua.eval("math")
    sandbox['error'] = lua.eval("error")
    sandbox['tonumber'] = lua.eval("tonumber")
    sandbox['db'] = lua.eval(fdb_str.format(settings.MYSQL_DATABASE_DB, "m{}".format(data[0]), "qwe123"))()

    if request.method == 'POST':
        args = dict(request.form)
    else:
        args = dict(request.args)
    sandbox['args'] = lua.table_from(args)
    sandbox['method'] = request.method

    mod_settings = {}
    if data[3] == 1:
        cursor.execute("SELECT name, type, value FROM Module_setting WHERE module_id=%s", (data[0],))
        sd = cursor.fetchall()
        for row in sd:
            val = row[2]
            if row[1] == 'int':
                val = int(val)
            elif row[1] == 'boolean':
                val = True if val == "true" else False
            mod_settings[row[0]] = val
    if len(mod_settings) != 0:
        sandbox['settings'] = lua.table_from(mod_settings)

    setfenv = lua.eval("setfenv")
    setfenv(0, sandbox)

    with open("lua/modules/{}/{}.lua".format(module_name, module_method)) as f:
        lua_code = f.read()
    try:
        method = lua.eval(lua_code)
    except lupa.LuaSyntaxError:
        return "lua syntax error"
    except:
        return "error occurred"
    try:
        res = to_dict(method())
    except lupa.LuaError as e:
        return "lua error: {}".format(e)
    except:
        return "error occurred"
    return json.dumps(res)


def to_dict(t1):
    for tu in t1.items():
        if lupa.lua_type(tu[1]) == 'table':
            t1[tu[0]] = to_dict(tu[1])
    try:
        l = sorted(t1.keys())
        if len(l) != 0 and l == range(1, l[-1] + 1):
            return list(t1.values())
    except TypeError:
        pass
    return dict(t1)


if __name__ == "__main__":
    app.run()
