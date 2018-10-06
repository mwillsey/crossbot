import sqlite3
import html
import re
from multiprocessing import Pool, TimeoutError

from crossbot.models import MiniCrosswordTime
import crossbot


def init(client):

    parser = client.parser.subparsers.add_parser('sql', help='Run a sql command.')
    parser.set_defaults(command=sql)

    parser.add_argument(
        'sql_command',
        # type = str,
        nargs = '*',
        help = 'sql command to run again at table of (user, date, seconds)')

SAFE_SQL_OPS = (
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    31, # sqlite3.SQLITE_FUNCTION
)

ALLOWED_TABLES = {
    MiniCrosswordTime._meta.db_table: ["mini_crossword_time"]
}

def replace_table_names(query):
    result = query
    for db_table, names in ALLOWED_TABLES.items():
        for name in names:
            result = result.replace(name, db_table)
    return result

def allow_only_select(operation, arg1, arg2, db_name, trigger):
    if operation in SAFE_SQL_OPS:
        if operation == sqlite3.SQLITE_READ:
            table_name = arg1
            print('should allow?: ', operation, arg1, arg2)
            print(table_name in ALLOWED_TABLES)
            if table_name in ALLOWED_TABLES:
                return sqlite3.SQLITE_OK
            else:
                return sqlite3.SQLITE_DENY

        return sqlite3.SQLITE_OK
    else:
        return sqlite3.SQLITE_DENY

def fmt_elem(elem):
    s = str(elem)
    if len(s) > 40:
        return s[:40] + '...'
    return s

def fmt_tup(tup):
    if len(tup) > 10:
        msg = 'tuple was {} elems, truncating...'.format(len(tup))
        tup = tup[:10]
        tup.append(msg)
    return ', '.join(fmt_elem(elem) for elem in tup)

def do_sql(cmd, *args):
    with sqlite3.connect(crossbot.db_path) as con:
        con.set_authorizer(allow_only_select)
        con.create_function('user_str', 1, user_str)
        try:
            rows = con.execute(cmd, args).fetchall()
            if len(rows) > 20:
                msg = 'result was {} rows, truncating...'.format(len(rows))
                rows = rows[:20]
                rows.append((msg,))
            result = '\n'.join(fmt_tup(tup) for tup in rows)
        except Exception as e:
            result = str(e) + ', this incident has been reported'
    return result

def format_sql_cmd(cmd):
    def replace_with_id(match):
        return match.group(1)
    cmd = html.unescape(cmd)
    cmd = re.sub(r'<@(\w+)>', replace_with_id, cmd)
    cmd = cmd.replace(u"\u2018", "'").replace(u"\u2019", "'").replace(u"\u201c","'").replace(u"\u201d", "'")

    return replace_table_names(cmd)

def user_str(pk):
    from crossbot.models import MyUser
    u = MyUser.objects.get(pk=pk)
    return str(u)

def format_sql_result(result, client):
    def replace_with_name(match):
        match = match.group()
        return client.user(match)
    result = re.sub(r'\w{9}', replace_with_name, result)
    return result

def sql(request):
    '''Run a sql command.'''

    cmd = ' '.join(request.args.sql_command)
    print("raw command: {}".format(cmd))
    cmd = format_sql_cmd(cmd)
    print("formatted command: {}".format(cmd))

    try:
        with Pool() as pool:
            result = pool.apply_async(do_sql, (cmd,)).get(1)
    except TimeoutError:
        result = "dont try to dos me, this incident has been reported"

    # result = format_sql_result(result, client)

    request.reply(result)
