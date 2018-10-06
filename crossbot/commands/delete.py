import sqlite3

import crossbot

def init(client):

    parser = client.parser.subparsers.add_parser('delete', help='Delete a time.')
    parser.set_defaults(command=delete)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to delete a score for.')

    # TODO add a command-line only --user parameter

def delete(request):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    table = request.args.table
    user = request.user
    date = request.args.date

    try:
        time = table.objects.get(date=date, user=user)
        time.delete()
        request.reply('Deleted this time: ' + str(time))
    except table.DoesNotExist:
        request.reply('No entry for {}'.format(date))
