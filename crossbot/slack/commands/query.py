import logging
import re

from . import sql, models, SlashCommandResponse

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser('query', help='Run a saved query')
    parser.set_defaults(command=query)

    parser.add_argument('name', nargs='?', help='Stored query name to run')
    parser.add_argument(
        '--save',
        action='store_true',
        help='Create or overwrite a stored query')
    parser.add_argument(
        'params',
        nargs='*',
        help='Parameters for the stored query or, if saving, the query itself, '
        'with question marks for parameters')


DATE_REGEX = re.compile(r'((\d\d\d\d)-(\d\d)-(\d\d))')


def linkify_dates(s):
    return DATE_REGEX.sub(
        r'<https://www.nytimes.com/crosswords/game/mini/\2/\3/\4|\1>', s)


def query(request):
    args = request.args

    if args.save:
        if not args.name:
            return SlashCommandResponse(
                "Cannot save a command without a name.")

        models.QueryShorthand.objects.update_or_create(
            name=args.name,
            defaults={
                'user': request.user,
                'command': ' '.join(args.params),
            })

        return SlashCommandResponse("Saved new query `{}` from {}".format(
            request.args.name, request.user))

    if args.name:
        q = models.QueryShorthand.from_name(args.name)
        if not q:
            return SlashCommandResponse(
                "Could not find saved query `{}`".format(args.name))
        return SlashCommandResponse(
            sql.run_sql_command(q.command, args.params))

    # Finally, just echo the list of all queries
    msgs = '\n\n'.join(str(q) for q in models.QueryShorthand.objects.all())
    if msgs:
        return SlashCommandResponse(msgs)
    else:
        return SlashCommandResponse("There are no saved messages yet... "
                                    "make one with `query --save ...`!")
