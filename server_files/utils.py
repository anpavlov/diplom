# coding=utf-8
import errno
import json
import os
import random
import string
from zipfile import ZipFile

from flaskext.mysql import MySQL
from lxml import etree
from werkzeug.security import check_password_hash

from settings import SESSION_COOKIE_STRING, SESSION_COOKIE_LENGTH, MYSQL_DATABASE_DB

# from flask import request

mysql = MySQL()
with open("schema.xml") as xml_sch:
    db_schema = etree.XMLSchema(etree.parse(xml_sch))


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
    cursor.execute("SELECT id, password, is_admin FROM User WHERE name = %s", (name,))
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
    cursor.execute("SELECT id, name, version, approved, activated FROM Module")
    modules = []
    count = 0
    new_count = 0
    for row in cursor.fetchall():
        modules.append({
            'id': row[0],
            'name': row[1],
            'version': row[2],
            'approved': row[3],
            'activated': row[4]
        })
        count += 1
        if row[3] == 0:
            new_count += 1
    return count, new_count, modules


def upload_module(archive):
    connection = mysql.connect()
    cursor = connection.cursor()
    with ZipFile(archive) as zip_archive:
        try:
            with zip_archive.open('manifest.json') as manifest_file:
                manifest = json.loads(manifest_file.read())
        except KeyError:
            return "no manifest"

        try:
            module_name = manifest['name']
            module_version = manifest['version']
            module_urls = manifest['urls']
            module_db = manifest['database']
        except KeyError as err:
            return "no module " + err.args[0]

        if not isinstance(module_name, basestring):
            return "name is not a string"

        if not isinstance(module_version, basestring):
            return "version is not a string"

        cursor.execute("SELECT 1 FROM Module WHERE name=%s", (module_name,))
        data = cursor.fetchone()
        if data is not None:
            return "module already exists"

        if not isinstance(module_urls, list):
            return "urls is not a list"

        for url in module_urls:
            if not isinstance(url, basestring):
                return "url is not a string"
            if not "urls/{}.lua".format(url) in zip_archive.namelist():
                return "no lua script '{}'".format(url)

        if not isinstance(module_db, bool):
            return "database is not a boolean"

        if module_db is True:
            if "database.xml" not in zip_archive.namelist():
                return "no database schema"
            with zip_archive.open('database.xml') as db_xml:
                if not db_schema.validate(etree.parse(db_xml)):
                    return "bad db xml schema"
                else:
                    # TODO check foreign keys
                    pass

        with ZipFile('modules/archives/{}{}.zip'.format(module_name, module_version), 'w') as zip_out:
            for file_name in zip_archive.namelist():
                zip_out.writestr(file_name, zip_archive.read(file_name))

    cursor.execute("INSERT INTO Module (name, version) VALUES (%s, %s)", (module_name, module_version))
    connection.commit()
    return "ok"


def approve_module(mod_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, version, approved FROM Module WHERE id=%s", mod_id)
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
        for url in module_urls:
            with zip.open('urls/{}.lua'.format(url)) as lua_file:
                try:
                    os.makedirs('lua/modules/{}/'.format(module_name))
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
                with open('lua/modules/{}/{}.lua'.format(module_name, url), 'w') as f:
                    f.write(lua_file.read())

        if module_db is True:
            # TODO: generate password
            user_create = "CREATE USER 'm{}'@'localhost' IDENTIFIED BY 'qwe123'".format(mod_id)
            cursor.execute(user_create)
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

                    create_string = "CREATE TABLE module_{}_{} (".format(module_name, table_name)
                    create_string += ", ".join(fields_values)
                    create_string += ")"
                    cursor.execute(create_string)
                    grant_string = "GRANT SELECT, UPDATE, INSERT, DELETE ON {}.module_{}_{} TO 'm{}'@'localhost'"\
                                   .format(MYSQL_DATABASE_DB, module_name, table_name, mod_id)
                    cursor.execute(grant_string)

        cursor.execute("UPDATE Module SET approved=TRUE WHERE id=%s", mod_id)
        conn.commit()


def switch_mod_able(mod_id, what):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT approved FROM Module WHERE id=%s", mod_id)
    data = cursor.fetchone()
    if data is None or data[0] == 0:
        return "no module or is not approved"
    cursor.execute("UPDATE Module SET activated=%s WHERE id=%s", (what, mod_id))
    conn.commit()
    return "ok"
