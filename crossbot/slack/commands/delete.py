from . import parse_date


def init(client):

    parser = client.parser.subparsers.add_parser(
        'delete', help='Delete a time.'
    )
    parser.set_defaults(command=delete)

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to delete a score for.'
    )

    # TODO add a command-line only --user parameter


def delete(request):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    date = request.args.date
    deleted_time = request.user.remove_time(request.args.table, date)
    if deleted_time:
        request.reply('Deleted this time: ' + str(deleted_time))
    else:
        request.reply('No entry for {}'.format(date))
