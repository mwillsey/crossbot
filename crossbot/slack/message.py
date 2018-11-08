import json
import logging

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static

from ..models import CBUser

logger = logging.getLogger(__name__)


class SlashCommandRequest:
    def __init__(self, django_request, args=None):
        self._django_request = django_request
        self.args = args

        post_data = django_request.POST

        self.text = post_data['text']
        self.response_url = post_data['response_url']
        self.trigger_id = post_data['trigger_id']
        self.channel = post_data['channel_id']

        self.slackid = post_data['user_id']
        self.user = CBUser.from_slackid(
            slackid=post_data['user_id'], slackname=post_data['user_name']
        )

    def build_absolute_uri(self, location):
        return self._django_request.build_absolute_uri(location)

    def in_main_channel(self):
        return self.channel == settings.CROSSBOT_MAIN_CHANNEL


class SlashCommandResponse:
    """Contains both an ephemeral and non-ephemeral message to send."""

    def __init__(
            self, *args, ephemeral=True, ephemeral_command=True, **kwargs
    ):
        """Initializes both messages, but sends all args to chosen one."""
        if ephemeral:
            self.ephemeral_message = Message(ephemeral=True, *args, **kwargs)
            self.direct_message = Message(ephemeral=False)
        else:
            self.ephemeral_message = Message(ephemeral=True)
            self.direct_message = Message(ephemeral=False, *args, **kwargs)

        # Whether or not the original slash command should be ephemeral
        self.ephemeral_command = ephemeral_command

    def set_user(self, *args, **kwargs):
        # User can only be sent on a non-ephemeral message
        self.direct_message.set_user(*args, **kwargs)

    def add_reaction(self, *args, **kwargs):
        # Reaction can only be sent to a direct message
        self.direct_message.add_reaction(*args, **kwargs)

    # TODO: maybe use magic methods instead of these for convenience methods
    def add_text(self, *args, ephemeral=True, **kwargs):
        if ephemeral:
            self.ephemeral_message.add_text(*args, **kwargs)
        else:
            self.direct_message.add_text(*args, **kwargs)

    def add_attachment_text(self, *args, ephemeral=True, **kwargs):
        if ephemeral:
            self.ephemeral_message.add_attachment_text(*args, **kwargs)
        else:
            self.direct_message.add_attachment_text(*args, **kwargs)

    def attach(self, *args, ephemeral=True, **kwargs):
        if ephemeral:
            self.ephemeral_message.attach(*args, **kwargs)
        else:
            self.direct_message.attach(*args, **kwargs)

    def attach_image(self, *args, ephemeral=True, **kwargs):
        if ephemeral:
            self.ephemeral_message.attach_image(*args, **kwargs)
        else:
            self.direct_message.attach_image(*args, **kwargs)


class Message:
    def __init__(self, text='', user=None, ephemeral=None):
        self.text = text
        self.attachments = []
        self.ephemeral = ephemeral

        self.username = None
        self.icon_url = None

        if user is not None:
            self.set_user(user)

        self.reactions = []

    def set_user(self, user):
        self.username = user.slack_fullname or user.slackname or None
        self.icon_url = user.image_url or None

    def add_text(self, text, add_newline=True):
        """Adds text to the main message."""
        if self.text and add_newline and not self.text.endswith('\n'):
            self.text += '\n'
        self.text += text

    def add_attachment_text(self, text, add_newline=True):
        """Adds text to the last attachment."""
        if not self.attachments:
            self.attach()
        self.attachments[-1].add_text(text, add_newline=add_newline)

    def attach(self, **attachment_kwargs):
        attachment = Attachment(**attachment_kwargs)
        self.attachments.append(attachment)
        return attachment

    def attach_image(self, name, path):
        return self.attach(
            fallback="image: %s" % name, pretext=name, image_url=path
        )

    def add_reaction(self, emoji):
        emoji = emoji.strip(':')
        if emoji not in self.reactions:
            self.reactions.append(emoji)

    def has_user(self):
        return (self.username is not None) or (self.icon_url is not None)

    def __bool__(self):
        return bool(self.text or self.attachments)

    def asdict(self, include_response_type=True):
        message_dict = {}
        if self.text:
            message_dict['text'] = self.text
        if self.attachments:
            message_dict['attachments'] = [
                a.asdict() for a in self.attachments
            ]
        if include_response_type and self.ephemeral is not None:
            message_dict['response_type'] = (
                'ephemeral' if self.ephemeral else 'in_channel'
            )
        if self.username is not None:
            message_dict['username'] = self.username
        if self.icon_url is not None:
            message_dict['icon_url'] = self.icon_url
        return message_dict


class Attachment:
    def __init__(self, user=None, **kwargs):
        self.fallback = kwargs.get('fallback')
        self.color = kwargs.get('color')
        self.pretext = kwargs.get('pretext')
        self.author_name = kwargs.get('author_name')
        self.author_link = kwargs.get('author_link')
        self.author_icon = kwargs.get('author_icon')
        self.title = kwargs.get('title')
        self.title_link = kwargs.get('title_link')
        self.text = kwargs.get('text')
        self.image_url = kwargs.get('image_url')
        self.thumb_url = kwargs.get('thumb_url')
        self.footer = kwargs.get('footer')
        self.footer_icon = kwargs.get('footer_icon')
        self.ts = kwargs.get('ts')

        self.fields = kwargs.get('fields', [])

        if user is not None:
            self.author_name = str(user)
            if user.image_url:
                self.author_icon = user.image_url

    def add_text(self, text, add_newline=True):
        """Adds text to the main message."""
        if self.text and add_newline and not self.text.endswith('\n'):
            self.text += '\n'
        self.text += text

    @staticmethod
    def field(title, value, short=True):
        """Construct a field dict from arguments."""
        return {'title': title, 'value': value, 'short': short}

    def add_field(self, title, value, short=True):
        """Add a field to the fields list for the attachment."""
        self.fields.append(self.field(title, value, short))

    # TODO: maybe use magic methods instead of this
    def asdict(self):
        """Return a JSON string representing this attachment."""
        attachment_dict = {}

        if self.fallback:
            attachment_dict['fallback'] = self.fallback
        if self.color:
            attachment_dict['color'] = self.color
        if self.pretext:
            attachment_dict['pretext'] = self.pretext
        if self.author_name:
            attachment_dict['author_name'] = self.author_name
        if self.author_link:
            attachment_dict['author_link'] = self.author_link
        if self.author_icon:
            attachment_dict['author_icon'] = self.author_icon
        if self.title:
            attachment_dict['title'] = self.title
        if self.title_link:
            attachment_dict['title_link'] = self.title_link
        if self.text:
            attachment_dict['text'] = self.text
            # By default, assume that text has markdown (but not pretext/fields)
            attachment_dict['mrkdwn_in'] = ['text']
        if self.image_url:
            attachment_dict['image_url'] = self.image_url
        if self.thumb_url:
            attachment_dict['thumb_url'] = self.thumb_url
        if self.footer:
            attachment_dict['footer'] = self.footer
        if self.footer_icon:
            attachment_dict['footer_icon'] = self.footer_icon
        if self.ts:
            attachment_dict['ts'] = self.ts

        if self.fields:
            attachment_dict['fields'] = self.fields

        return attachment_dict
