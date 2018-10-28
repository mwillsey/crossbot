import json
import logging
import traceback

from django.contrib.staticfiles.templatetags.staticfiles import static

from .commands import COMMANDS
from .parser import Parser, ParserException
from .api import *
from ..models import CBUser

logger = logging.getLogger(__name__)


# TODO: this class and related classes/api methods need refactoring
class SlashCommandRequest:
    def __init__(self, request, in_channel=False):
        self._django_request = request

        post_data = request.POST

        self.text = post_data['text']
        self.response_url = post_data['response_url']
        self.trigger_id = post_data['trigger_id']
        self.channel = post_data['channel_id']

        self.slackid = post_data['user_id']
        self.user = CBUser.from_slackid(
            slackid=post_data['user_id'], slackname=post_data['user_name'])

        self.in_channel = in_channel
        self.replies = []
        self.attachments = []

        self.as_user_image = False

    def build_absolute_uri(self, location):
        return self._django_request.build_absolute_uri(location)


    def attach(self, attachment):
        self.attachments.append(attachment)

    def attach_image(self, name, path):
        self.attachments.append({
            'fallback': 'its a picture',
            'pretext': name,
            'image_url': path,
        })

class SlashCommandResponse:
    def __init__(self, text = ''):
        self.text = text
        self.attachments = []

    def add_field(self, title, value, short=True):
        """Adds a field to the first attachment of the reply."""
        if not self.attachments:
            self.attachments.append({})
        attachment = self.attachments[0]
        if not 'fields' in attachment:
            attachment['fields'] = []
        attachment['fields'].append({
            'title': title,
            'value': value,
            'short': short,
        })

    def attach(self, **attachment_kwargs):
        attachment = Attachment(**attachment_kwargs)
        self.attachments.append(attachment)
        return attachment

    def json(self):
        response = {}
        if self.replies:
            response['text'] = '\n'.join(self.replies)
        if self.attachments:
            response['attachments'] = json.dumps(self.attachments)
        if self.user.hat:
            response['as_user'] = json.dumps(False)
            response['username'] = 'crossbot'
            response['icon_url'] = self.build_absolute_uri(
                self.user.hat.image_url())
        post_message(self.channel, **response)

        return {'text': 'ok'}

class Attachment:
    def __init__(self):
        self.text = ''

    def json(self):
        response = {}
        if self.replies:
            response['text'] = '\n'.join(self.replies)
        if self.attachments:
            response['attachments'] = json.dumps(self.attachments)
        if self.user.hat:
            response['as_user'] = json.dumps(False)
            response['username'] = 'crossbot'
            response['icon_url'] = self.build_absolute_uri(
                self.user.hat.image_url())
        post_message(self.channel, **response)

        return {'text': 'ok'}
