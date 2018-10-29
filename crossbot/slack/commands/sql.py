import html
import logging
import multiprocessing
import re
import sqlite3
import traceback

from . import models, DB_PATH, SlashCommandResponse

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser('sql', help='Run a sql command.')
    parser.set_defaults(command=sql)

    parser.add_argument(
        'sql_command',
        nargs='*',
        help='sql command to run again at table of (user, date, seconds)'
    )


SAFE_SQL_OPS = (
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    31,  # sqlite3.SQLITE_FUNCTION
)

ALLOWED_TABLES = {
    models.MiniCrosswordTime._meta.db_table: ["mini_crossword_time"]
}


def _allow_only_select(operation, arg1, arg2, db_name, trigger):
    if operation not in SAFE_SQL_OPS:
        return sqlite3.SQLITE_DENY

    if operation != sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK

    table_name = arg1
    logger.debug(
        'should allow %s %s %s? %s', operation, arg1, arg2,
        table_name in ALLOWED_TABLES
    )

    if table_name not in ALLOWED_TABLES:
        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def fmt_tup(tup):
    def fmt_elem(elem):
        s = str(elem)
        if len(s) > 40:
            return s[:40] + '...'
        return s

    if len(tup) > 10:
        msg = 'tuple was {} elems, truncating...'.format(len(tup))
        tup = tup[:10]
        tup.append(msg)
    return ', '.join(fmt_elem(elem) for elem in tup)


def _do_sql(cmd, *args):
    """Function used by async worker, internal use only.

    Assumes the command and args have already been sanitized.
    """
    with sqlite3.connect(DB_PATH) as con:
        con.set_authorizer(_allow_only_select)
        # con.create_function('user_str', 1, user_str)
        try:
            rows = con.execute(cmd, args).fetchall()

            # Truncate to 20 rows
            if len(rows) > 20:
                msg = 'result was {} rows, truncating...'.format(len(rows))
                rows = rows[:20]
                rows.append((msg, ))

            result = '\n'.join(fmt_tup(tup) for tup in rows)

            # Replace slackids with slacknames
            def username_from_slackid(m):
                slackid = m.group(1)
                user = models.CBUser.from_slackid(slackid)
                if user:
                    return str(user)
                else:
                    logger.debug("Can't find slack name for %s", slackid)
                return slackid

            logger.debug('result %s', result)
            result = re.sub(r'(U[A-Z0-9]{8})', username_from_slackid, result)

            return result

        except Exception as e:
            tb = traceback.format_exc()
            logger.info(
                'sql exception. command:\n%s\n exception: %s\n%s', cmd, e, tb
            )
            return str(e) + ', this incident has been reported'


def _format_sql_cmd(cmd):
    cmd = html.unescape(cmd)
    cmd = re.sub(r'<@(\w+)(\|[^>]*)?>', lambda m: m.group(1), cmd)
    cmd = (
        cmd.replace(u"\u2018",
                    "'").replace(u"\u2019",
                                 "'").replace(u"\u201c",
                                              "'").replace(u"\u201d", "'")
    )

    # Now, replace the table names to help mask Django craziness
    for db_table, names in ALLOWED_TABLES.items():
        for name in names:
            cmd = cmd.replace(name, db_table)

    return cmd


def run_sql_command(raw_cmd, args):
    """Formats the command and runs it safely."""

    logger.debug("raw command: %s | %s", raw_cmd, args)

    cmd = _format_sql_cmd(raw_cmd)
    args = [_format_sql_cmd(arg) for arg in args]

    logger.debug("formatted command: %s | %s", cmd, args)

    try:
        with multiprocessing.Pool() as pool:
            result = pool.apply_async(_do_sql, [cmd] + args).get(1)
            return raw_cmd + '\n\n' + result
    except multiprocessing.TimeoutError:
        return "dont try to dos me, this incident has been reported"


def sql(request):
    '''Run a sql command.'''
    if request.args.sql_command:
        cmd = ' '.join(request.args.sql_command)
        return SlashCommandResponse(run_sql_command(cmd, []))
    else:
        return SlashCommandResponse("Please type some sql.")
