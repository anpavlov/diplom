# coding=utf-8
import errno
import json
import os
import random
import string
from zipfile import ZipFile, BadZipfile

from flaskext.mysql import MySQL
from lxml import etree
from werkzeug.security import check_password_hash

from settings import SESSION_COOKIE_STRING, SESSION_COOKIE_LENGTH, MYSQL_DATABASE_DB

# from flask import request

mysql = MySQL()
with open("db_schema.xml") as xml_sch:
    db_schema = etree.XMLSchema(etree.parse(xml_sch))
with open("settings_schema.xml") as xml_sch:
    settings_schema = etree.XMLSchema(etree.parse(xml_sch))


def get_logged_user_id(req):
    cookie = req.cookies.get(SESSION_COOKIE_STRING)
    if cookie == '':
        return None
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Session WHERE cookie = %s", (cookie,))
    row = cursor.fetchone()
    if row is None:
        return None
    else:
        return row[0]


def try_login_admin(name, password):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password, is_admin FROM Admin WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row is None:
        return None
    if row[2] != 1:
        return None
    if check_password_hash(row[1], password):
        return row[0]
    else:
        return None


def set_new_session(user_id, resp):
    conn = mysql.connect()
    cursor = conn.cursor()
    # sid = ''
    while True:
        sid = ''.join(random.SystemRandom().choice(string.digits + string.ascii_letters)
                      for _ in xrange(SESSION_COOKIE_LENGTH))
        cursor.execute("SELECT 1 FROM Session WHERE cookie = %s", (sid,))
        row = cursor.fetchone()
        if row is None:
            break
    cursor.execute("INSERT INTO Session (user_id, cookie) VALUES (%s, %s)", (user_id, sid))
    conn.commit()
    resp.set_cookie(SESSION_COOKIE_STRING, value=sid)


def get_all_modules():
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, version, approved, activated, has_settings, has_page FROM Module")
    modules = []
    count = 0
    new_count = 0
    for row in cursor.fetchall():
        modules.append({
            'id': row[0],
            'name': row[1],
            'version': row[2],
            'approved': row[3],
            'activated': row[4],
            'has_settings': row[5],
            'has_page': row[6]
        })
        count += 1
        if row[3] == 0:
            new_count += 1
    return count, new_count, modules


def upload_module(archive):
    connection = mysql.connect()
    cursor = connection.cursor()
    db_urls = []
    db_tables = []
    db_settings = []
    try:
        fz = ZipFile(archive)
        fz.close()
    except BadZipfile:
        return "Это не ZIP архив"
    with ZipFile(archive) as zip_archive:
        try:
            with zip_archive.open('manifest.json') as manifest_file:
                manifest = json.loads(manifest_file.read())
        except KeyError:
            return "ZIP архив не содержит манифест"

        try:
            module_name = manifest['name']
            module_version = manifest['version']
            module_urls = manifest['urls']
            module_db = manifest['database']
            module_settings = manifest['settings']
            module_html = manifest['html']
        except KeyError as err:
            return "В манифесте отсутствует поле " + err.args[0]

        if not isinstance(module_name, basestring):
            return "Поле name не является строкой"

        if not isinstance(module_version, basestring):
            return "Поле version не является строкой"

        cursor.execute("SELECT 1 FROM Module WHERE name=%s", (module_name,))
        data = cursor.fetchone()
        if data is not None:
            return "Компонент с таким именем уже существует"

        if not isinstance(module_urls, list):
            return "Поле urls не является списком"

        for url in module_urls:
            if not isinstance(url, basestring):
                return "Одно из значений в списке urls не является строкой"
            if not "urls/{}.lua".format(url) in zip_archive.namelist():
                return "Нет соответствующего Lua-скрипта для функции '{}'".format(url)
            db_urls.append(url)

        try:
            module_description = manifest['description']
        except KeyError:
            module_description = ""

        try:
            module_dependencies = manifest['dependencies']
        except KeyError:
            module_dependencies = []

        if not isinstance(module_db, bool):
            return "Поле database не является логическим"

        if module_db is True:
            if "database.xml" not in zip_archive.namelist():
                return "Отсутствует схема таблиц для базы данных"
            with zip_archive.open('database.xml') as db_xml_file:
                db_xml = etree.parse(db_xml_file)
                if not db_schema.validate(db_xml):
                    return "Неверная схема таблиц для базы данных"
                else:
                    # TODO check foreign keys
                    for table in db_xml.xpath('/Database/Table/@name'):
                        db_tables.append(table)

        if not isinstance(module_settings, bool):
            return "Поле settings не является логическим"

        if module_settings is True:
            if "settings.xml" not in zip_archive.namelist():
                return "Отсутствует схема натсроек"
            with zip_archive.open('settings.xml') as settings_xml_file:
                settings_xml = etree.parse(settings_xml_file)
                if not settings_schema.validate(settings_xml):
                    return "Неверная схема настроек"
                else:
                    for setting in settings_xml.xpath('/Settings/Setting'):
                        db_settings.append({
                            'name': setting.get('name'),
                            'type': setting.get('type'),
                            'default': setting.get('default')
                        })

        if not isinstance(module_html, bool):
            return "Поле html не является логическим"

        if module_html is True and 'html/index.html' not in zip_archive.namelist():
            return "Отсутствует файл index.html в папке html"

        with ZipFile('modules/archives/{}{}.zip'.format(module_name, module_version), 'w') as zip_out:
            for file_name in zip_archive.namelist():
                zip_out.writestr(file_name, zip_archive.read(file_name))

    cursor.execute("INSERT INTO Module (name, version, has_db, has_settings, has_page, description) VALUES (%s, %s, %s, %s, %s, %s)",
                   (module_name, module_version, module_db, module_settings, module_html, module_description))
    module_id = cursor.lastrowid
    for url in db_urls:
        cursor.execute("INSERT INTO Module_method (module_id, module_method) VALUES (%s, %s)", (module_id, url))
    for table in db_tables:
        cursor.execute("INSERT INTO Module_table (module_id, table_name) VALUES (%s, %s)", (module_id, table))
    for dep in module_dependencies:
        cursor.execute("INSERT INTO Module_dependency (module_id, dependency_name) VALUES (%s, %s)", (module_id, dep))
    for setting in db_settings:
        cursor.execute("INSERT INTO Module_setting (module_id, name, type, value) VALUES (%s, %s, %s, %s)",
                       (module_id, setting['name'], setting['type'], setting['default'] if setting['default'] is not None else ""))
    connection.commit()
    return "ok"


def approve_module(mod_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, version, approved FROM Module WHERE id=%s", (mod_id,))
    data = cursor.fetchone()
    if not data:
        return "no module"
    if data[2] is True:
        return "already approved"

    module_name = data[0]
    module_version = data[1]

    with ZipFile('modules/archives/{}{}.zip'.format(module_name, module_version), 'r') as zip:
        with zip.open('manifest.json') as manifest_file:
            manifest = json.loads(manifest_file.read())
        # TODO класть эту в бд
        module_urls = manifest['urls']
        module_db = manifest['database']
        module_html = manifest['html']

        cursor.execute("SELECT dependency_name FROM Module_dependency WHERE module_id=%s", (mod_id,))
        data = cursor.fetchall()
        for row in data:
            cursor.execute("SELECT 1 FROM Module WHERE name=%s and activated=1", (row[0],))
            dep_d = cursor.fetchone()
            if dep_d is None:
                return "Не удовлетворена зависимость: {}".format(row[0])

        for url in module_urls:
            with zip.open('urls/{}.lua'.format(url)) as lua_file:
                try:
                    os.makedirs('lua/modules/{}/'.format(module_name))
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
                with open('lua/modules/{}/{}.lua'.format(module_name, url), 'w') as f:
                    f.write(lua_file.read())

        if module_html:
            html_files = [x for x in zip.namelist() if x.startswith('html/') and x != "html/"]
            os.makedirs('modules/html/{}/'.format(module_name))
            for html_name in html_files:
                with zip.open(html_name) as html_file:
                    with open('modules/html/{}/{}'.format(module_name, html_name[5:]), 'w') as f:
                        f.write(html_file.read())

        if module_db is True:
            # TODO: generate password
            user_create = "CREATE USER 'm{}'@'localhost' IDENTIFIED BY 'qwe123'".format(mod_id)
            cursor.execute(user_create)
            foreign_tables = []
            with zip.open('database.xml') as db_xml:
                db = etree.XML(db_xml.read())
                # tables =
                for table in db.xpath('/Database/Table'):
                    table_name = table.get('name')
                    fields_values = []
                    # Fields
                    for field in db.xpath('/Database/Table[@name="{}"]/Field'.format(table_name)):
                        field_name = field.get('name')
                        field_type = field.get('type')
                        field_auto_increment = field.get('auto_increment')
                        field_not_null = field.get('not_null')
                        field_default = field.get('default')
                        field_string = '{} {}'.format(field_name, field_type)
                        if field_not_null is not None and field_not_null == "true":
                            field_string += ' NOT NULL'
                        if field_default is not None:
                            field_string += ' DEFAULT "{}"'.format(field_default)
                        if field_auto_increment is not None and field_auto_increment == "true":
                            field_string += ' AUTO_INCREMENT'
                        fields_values.append(field_string)

                    # Primary key
                    primary_fields = []
                    for column in db.xpath('/Database/Table[@name="{}"]/Primary'.format(table_name))[0]:
                        primary_fields.append(column.get("name"))
                    primary_string = "PRIMARY KEY ("
                    primary_string += ", ".join(primary_fields)
                    primary_string += ")"
                    fields_values.append(primary_string)

                    # Unique keys
                    for unique_key in db.xpath('/Database/Table[@name="{}"]/Unique'.format(table_name)):
                        unique_name = unique_key.get("name")
                        unique_fields = []
                        for column in unique_key:
                            unique_fields.append(column.get("name"))
                        unique_string = "UNIQUE KEY"
                        if unique_name is not None:
                            unique_string += " {} (".format(unique_name)
                        else:
                            unique_string += "("
                        unique_string += ", ".join(unique_fields)
                        unique_string += ")"
                        fields_values.append(unique_string)

                    # Index keys
                    for index_key in db.xpath('/Database/Table[@name="{}"]/Index'.format(table_name)):
                        index_name = index_key.get("name")
                        index_fields = []
                        for column in index_key:
                            index_fields.append(column.get("name"))
                        index_string = "INDEX"
                        if index_name is not None:
                            index_string += " {} (".format(index_name)
                        else:
                            index_string += " ("
                        index_string += ", ".join(index_fields)
                        index_string += ")"
                        fields_values.append(index_string)

                    # Foreign keys
                    for foreign_key in db.xpath('/Database/Table[@name="{}"]/Foreign'.format(table_name)):
                        foreign_name = foreign_key.get("name")
                        foreign_table = foreign_key.get("foreign-table")
                        foreign_tables.append(foreign_table)
                        foreign_this_fields = []
                        foreign_foreign_fields = []
                        for column in foreign_key:
                            foreign_this_fields.append(column.get("name"))
                            foreign_foreign_fields.append(column.get("foreign-field"))
                        foreign_string = "FOREIGN KEY"
                        if foreign_name is not None:
                            foreign_string += " {} (".format(foreign_name)
                        else:
                            foreign_string += " ("
                        foreign_string += ", ".join(foreign_this_fields)
                        foreign_string += ") REFERENCES {} (".format(foreign_table)
                        foreign_string += ", ".join(foreign_foreign_fields)
                        foreign_string += ")"
                        fields_values.append(foreign_string)

                    create_string = "CREATE TABLE m_{}_{} (".format(module_name, table_name)
                    create_string += ", ".join(fields_values)
                    create_string += ")"
                    cursor.execute(create_string)
                    grant_string = "GRANT SELECT, UPDATE, INSERT, DELETE ON {}.m_{}_{} TO 'm{}'@'localhost'"\
                                   .format(MYSQL_DATABASE_DB, module_name, table_name, mod_id)
                    cursor.execute(grant_string)

                    for t in foreign_tables:
                        grant_string = "GRANT SELECT ON {}.{} TO 'm{}'@'localhost'".format(MYSQL_DATABASE_DB, t, mod_id)
                        cursor.execute(grant_string)

        cursor.execute("UPDATE Module SET approved=TRUE WHERE id=%s", (mod_id,))
        conn.commit()
        return "ok"


def switch_mod_able(mod_id, what):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT approved, name FROM Module WHERE id=%s", (mod_id,))
    data = cursor.fetchone()
    if data is None or data[0] == 0:
        return "no module or is not approved"
    module_name = data[1]
    cursor.execute("SELECT 1 FROM Module_dependency WHERE dependency_name=%s", (module_name,))
    dp = cursor.fetchone()
    if dp is not None and what is False:
        return "Невозможно выключить, компонент используется другим компонентом"
    cursor.execute("UPDATE Module SET activated=%s WHERE id=%s", (what, mod_id))
    conn.commit()
    return "ok"


def delete_mod(module_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, version, approved FROM Module WHERE id=%s", (module_id,))
    data = cursor.fetchone()
    if data is None:
        return "no module"
    module_name = data[0]
    module_version = data[1]
    module_approved = data[2]
    cursor.execute("SELECT 1 FROM Module_dependency WHERE dependency_name=%s", (module_name,))
    dp = cursor.fetchone()
    if dp is not None:
        return "Невозможно удалить, компонент используется другим компонентом"
    if module_approved == 1:
        cursor.execute("SET foreign_key_checks = 0")
        cursor.execute("SELECT table_name FROM Module_table WHERE module_id=%s", (module_id,))
        data = cursor.fetchall()
        for row in data:
            cursor.execute("DROP TABLE m_{}_{}".format(module_name, row[0]))
        cursor.execute("SET foreign_key_checks = 1")

        cursor.execute("DROP USER 'm{}'@'localhost'".format(module_id))

        luadir_path = "lua/modules/{}/".format(module_name)
        for f in os.listdir(luadir_path):
            os.remove("lua/modules/{}/{}".format(module_name, f))
        os.rmdir(luadir_path)

        html_path = "modules/html/{}/".format(module_name)
        for f in os.listdir(html_path):
            os.remove("modules/html/{}/{}".format(module_name, f))
        os.rmdir(html_path)

    cursor.execute("DELETE FROM Module_table WHERE module_id=%s", (module_id,))
    cursor.execute("DELETE FROM Module_method WHERE module_id=%s", (module_id,))
    cursor.execute("DELETE FROM Module_setting WHERE module_id=%s", (module_id,))
    cursor.execute("DELETE FROM Module_dependency WHERE module_id=%s", (module_id,))
    cursor.execute("DELETE FROM Module WHERE id=%s", (module_id,))
    os.remove("modules/archives/{}{}.zip".format(module_name, module_version))

    conn.commit()
    return "ok"


def get_module_info(module_name):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, version, approved, activated, has_db, description, has_settings, has_page FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None:
        return None
    module_id = data[0]
    info = {
        'id': module_id,
        'name': module_name,
        'version': data[1],
        'approved': data[2],
        'activated': data[3],
        'has_db': data[4],
        'description': data[5],
        'has_settings': data[6],
        'has_page': data[7]

    }
    if data[4] == 1:
        cursor.execute("SELECT table_name FROM Module_table WHERE module_id=%s", (module_id,))
        data_n = cursor.fetchall()
        info['tables'] = []
        for row in data_n:
            info['tables'].append(row[0])

    if data[6] == 1:
        cursor.execute("SELECT name, type, value FROM Module_setting WHERE module_id=%s", (module_id,))
        data = cursor.fetchall()
        info['settings'] = []
        for row in data:
            info['settings'].append({
                'name': row[0],
                'type': row[1],
                'value': row[2]
            })

    cursor.execute("SELECT module_method FROM Module_method WHERE module_id=%s", (module_id,))
    data = cursor.fetchall()
    info['methods'] = []
    for row in data:
        info['methods'].append(row[0])

    cursor.execute("SELECT dependency_name FROM Module_dependency WHERE module_id=%s", (module_id,))
    data = cursor.fetchall()
    info['dependencies'] = []
    for row in data:
        info['dependencies'].append(row[0])

    return info


def get_module_contents(module_name):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, version, has_db, has_settings, has_page FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None:
        return None
    module_version = data[1]
    module_db = data[2]
    module_settings = data[3]
    module_html = data[4]
    methods = []
    static = []

    with ZipFile('modules/archives/{}{}.zip'.format(module_name, module_version), 'r') as zip_f:
        with zip_f.open('manifest.json') as manifest_file:
            manifest = json.loads(manifest_file.read())
        if module_db == 1:
            with zip_f.open('database.xml') as db_file:
                db_text = db_file.read()
        if module_settings == 1:
            with zip_f.open('settings.xml') as settings_file:
                settings_text = settings_file.read()
        module_urls = manifest['urls']
        for url in module_urls:
            with zip_f.open('urls/{}.lua'.format(url)) as lua_file:
                method = {'name': url, 'text': lua_file.read()}
                methods.append(method)

        if module_html:
            html_files = [x for x in zip_f.namelist() if x.startswith('html/') and x != "html/"]
            for html_name in html_files:
                with zip_f.open(html_name) as html_file:
                    static.append({'name': html_name[5:], 'data': unicode(html_file.read(), 'utf-8')})

    sources = {
        'manifest': json.dumps(manifest, indent=2),
        'methods': methods,
        'module': get_module_info(module_name)
    }

    if module_db == 1:
        sources['db'] = db_text
    if module_settings == 1:
        sources['settings'] = settings_text
    if module_html == 1:
        sources['html'] = static

    return sources


def get_settings(module_name):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, has_settings FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None or data[1] != 1:
        return None
    module_id = data[0]
    cursor.execute("SELECT name, type, value FROM Module_setting WHERE module_id=%s", (module_id,))
    data = cursor.fetchall()
    settings = []
    for row in data:
        settings.append({
            'name': row[0],
            'type': row[1],
            'value': row[2]
        })
    return {
        'settings': settings,
        'module': get_module_info(module_name)
    }


def set_settings(module_name, new_settings):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, has_settings FROM Module WHERE name=%s", (module_name,))
    data = cursor.fetchone()
    if data is None or data[1] != 1:
        return "no module or no settings"
    module_id = data[0]
    settings = get_settings(module_name)['settings']
    for new_setting in new_settings:
        if not any(d['name'] == new_setting['name'] for d in settings):
            return "no {} setting".format(new_setting['name'])
        # t = (i for i in settings if i['name'] == new_setting['name']).next()['type']
        cursor.execute("UPDATE Module_setting SET value=%s WHERE module_id=%s AND name=%s", (new_setting['value'], module_id, new_setting['name']))
    conn.commit()
    return "ok"

