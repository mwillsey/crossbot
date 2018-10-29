from . import parse_date, SlashCommandResponse


def init(parser):
    parser = parser.subparsers.add_parser(
        'delete', help='Delete a time.')
    parser.set_defaults(command=delete)

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to delete a score for.')

    # TODO add a command-line only --user parameter


def delete(request):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    date = request.args.date
    deleted_time = request.user.remove_time(request.args.table, date)
    if deleted_time:
        message = 'Deleted this time: ' + str(deleted_time)
    else:
        message = 'No entry for {}'.format(date)

    return SlashCommandResponse(text=message)
