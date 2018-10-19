import hashlib
import hmac
import json
import time
import os.path

import unittest
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from crossbot.slack.commands import parse_date
from crossbot.slack.api import SLACK_URL
from crossbot.views import slash_command
from crossbot.models import (
    CBUser,
    MiniCrosswordTime,
    CrosswordTime,
    EasySudokuTime,
    QueryShorthand,
)
from crossbot.settings import CROSSBUCKS_PER_SOLVE


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class MockedRequestTestCase(TestCase):
    def setUp(self):
        self.router = {}
        self._patcher_get = patch(
            'requests.get', side_effect=self.mocked_requests_get)
        self._patcher_post = patch(
            'requests.post', side_effect=self.mocked_requests_post)
        self._patcher_get.start()
        self._patcher_post.start()

    def tearDown(self):
        self.router = {}
        self._patcher_get.stop()
        self._patcher_post.stop()

    def mocked_requests_get(self, url, **kwargs):
        return self.mocked_request('GET', url, **kwargs)

    def mocked_requests_post(self, url, **kwargs):
        return self.mocked_request('POST', url, **kwargs)

    def check_headers(self, method, url, headers):
        pass

    def mocked_request(self, method, url, *, headers, params):
        self.check_headers(method, url, headers)
        func = self.router.get(url)
        if func:
            return func(method, url, headers, params)
        else:
            MockResponse(None, 404)


class SlackTestCase(MockedRequestTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.router[SLACK_URL + 'chat.postMessage'] = self.slack_chat_post
        self.router[SLACK_URL + 'reactions.add'] = self.slack_reaction_add

        self.slack_timestamp = 0
        self.messages = []

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patch('settings.SLACK_SECRET_SIGNING_KEY', self.slack_sk)
        self.patch('settings.SLACK_OAUTH_ACCESS_TOKEN', 'oauth_token')

    def patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher

    def check_headers(self, method, url, headers):
        if url.startswith(SLACK_URL):
            self.assertEquals(headers['Authorization'], 'Bearer oauth_token')

    def slack_reaction_add(self, method, url, headers, params):
        return MockResponse({'ok': True}, 200)

    def slack_chat_post(self, method, url, headers, params):
        self.assertEquals(method, 'POST')
        ts = self.slack_timestamp
        self.slack_timestamp += 1
        return MockResponse({'ok': True, 'ts': ts}, 200)

    def post_valid_request(self, post_data):
        request = self.factory.post(reverse('slash_command'), post_data)
        ts = str(time.time())
        request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP'] = ts
        request.META['HTTP_X_SLACK_SIGNATURE'] = 'v0=' + hmac.new(
            key=self.slack_sk,
            msg=b'v0:' + bytes(ts, 'utf8') + b':' + request.body,
            digestmod=hashlib.sha256).hexdigest()
        return slash_command(request)

    def slack_post(self,
                   text,
                   who='alice',
                   expected_status_code=200,
                   expected_response_type='ephemeral'):
        response = self.post_valid_request({
            'type': 'event_callback',
            'text': text,
            'response_url': 'foobar',
            'trigger_id': 'foobar',
            'channel_id': 'foobar',
            'user_id': 'U' + who.upper(),
            'user_name': '@' + who,
        })

        self.assertEqual(response.status_code, expected_status_code)

        body = json.loads(response.content)
        self.assertEqual(body['response_type'], expected_response_type)

        return body


class ModelTests(TestCase):
    def test_add_user(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertIsInstance(alice, CBUser)
        self.assertEqual(alice, CBUser.from_slackid('UALICE', 'bob'))
        alice = CBUser.from_slackid('UALICE')
        self.assertEqual(CBUser.from_slackid('UALICE').slackname, 'bob')

    def test_add_time(self):
        alice = CBUser.from_slackid('UALICE', 'alice')

        a, t = alice.add_mini_crossword_time(10, parse_date(None))
        self.assertTrue(a)
        self.assertEqual(t.user, alice)
        self.assertEqual(t.seconds, 10)
        self.assertEqual(t.date, parse_date(None))

        self.assertEqual(alice.get_mini_crossword_time(parse_date(None)), t)

    def test_add_remove_time(self):
        alice = CBUser.from_slackid('UALICE', 'alice')

        alice.add_mini_crossword_time(10, parse_date(None))

        alice.remove_mini_crossword_time(parse_date(None))
        self.assertEqual(alice.get_mini_crossword_time(parse_date(None)), None)

        a, t = alice.add_mini_crossword_time(10, parse_date(None))
        self.assertTrue(a)
        self.assertEqual(t.user, alice)
        self.assertEqual(t.seconds, 10)
        self.assertEqual(t.date, parse_date(None))
        self.assertNotEqual(
            alice.get_mini_crossword_time(parse_date(None)), None)

    def test_add_fail(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        a, t = alice.add_mini_crossword_time(-1, parse_date(None))
        self.assertTrue(a)
        self.assertEqual(t.seconds, -1)
        self.assertEqual(t.date, parse_date(None))
        self.assertTrue(t.is_fail())

    def test_crossbucks_add_remove(self):
        # Checks that removing a time actually removes crossbucks
        alice = CBUser.from_slackid('UALICE', 'alice')
        alice.add_mini_crossword_time(10, parse_date(None))
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)
        alice.add_mini_crossword_time(10, parse_date(None))
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)
        alice.remove_mini_crossword_time(parse_date(None))
        self.assertEqual(alice.crossbucks, 0)
        alice.remove_mini_crossword_time(parse_date(None))
        self.assertEqual(alice.crossbucks, 0)
        alice.add_mini_crossword_time(10, parse_date(None))
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)


class SlackAuthTests(SlackTestCase):
    def test_bad_signature(self):
        response = self.client.post(
            reverse('slash_command'),
            HTTP_X_SLACK_REQUEST_TIMESTAMP=str(time.time()),
            HTTP_X_SLACK_SIGNATURE=b'')
        self.assertEqual(response.status_code, 400)


class SlackAppTests(SlackTestCase):
    def test_add(self):
        self.slack_post(text='add :10')

        # make sure the database reflects this
        alice = CBUser.objects.get(slackid='UALICE')
        self.assertEqual(len(alice.minicrosswordtime_set.all()), 1)

    def test_double_add(self):

        # two adds on the same day should trigger an error
        self.slack_post(text='add :10 2018-08-01')
        response = self.slack_post(text='add :11 2018-08-01')

        # make sure the error message refers to the previous time
        self.assertIn(':10', response['text'])

        alice = CBUser.objects.get(slackid='UALICE')

        # make sure both times didn't get submitted
        times = alice.minicrosswordtime_set.all()
        self.assertEqual(len(times), 1)

        # make sure the original time was preserved
        self.assertEqual(times[0].seconds, 10)

    def test_times(self):
        self.slack_post('add :15 2018-08-01', who='alice')
        self.slack_post('add :40 2018-08-01', who='bob')

        # check date parsing here too
        response = self.slack_post('times 2018-8-1')

        lines = response['text'].split('\n')

        # line 0 is date, line 1 should be alice
        self.assertIn('alice', lines[1])
        self.assertIn(':fire:', lines[1])

    def test_help(self):
        response = self.slack_post(text='')
        self.assertIn('usage:', response['text'])

        response = self.slack_post(text='   ')
        self.assertIn('usage:', response['text'])

        response = self.slack_post(text='-h')
        self.assertIn('usage:', response['text'])

        response = self.slack_post(text='help')
        self.assertIn('usage:', response['text'])

        # this is an actual bad command, should respond with a different error
        response = self.slack_post(text='asdfasdiufpasdfa')
        self.assertIn('invalid choice:', response['text'])

    def test_add_delete(self):
        self.slack_post(text='add :23 2018-08-01')

        # Make sure the delete response actually references the time
        response = self.slack_post(text='delete 2018-08-01')
        self.assertIn(':23', response['text'])

        # Ensure the time doesn't show up in the times list
        response = self.slack_post(text='times 2018-08-01')
        self.assertNotIn(':23', response['text'])

    @unittest.skipUnless(os.path.isfile('crossbot.db'), 'No existing db found')
    def test_sql(self):
        # should be able to handle an empty query
        response = self.slack_post(text='sql')
        self.assertIn('Please type', response['text'])
        response = self.slack_post(text='sql  ')
        self.assertIn('Please type', response['text'])

        query_text = 'select count(*) from mini_crossword_time'
        response = self.slack_post(text='sql ' + query_text)
        self.assertIn(query_text, response['text'])
        # just check that we can turn the response into an int
        # because we are just making raw sqlite, the django testing thing
        # doesn't clear out the model
        int(response['text'].split('\n')[-1])

        response = self.slack_post(
            text='sql select * from mini_crossword_time')
        self.assertNotIn('reported', response['text'])

    @unittest.skipUnless(os.path.isfile('crossbot.db'), 'No existing db found')
    def test_query(self):
        # make sure the command tells you how to do it if there are no saved queries
        response = self.slack_post(text='query')
        self.assertIn('no saved', response['text'])
        self.assertIn('query --save', response['text'])

        # make sure we can save a new query
        query_text = 'select count(*) from mini_crossword_time'
        response = self.slack_post('query --save num_minis ' + query_text)
        self.assertIn('Saved new', response['text'])

        # make sure it's the right command
        query = QueryShorthand.objects.first()
        self.assertEqual(query.command, query_text)
        self.assertEqual(query.user_id, 'UALICE')

        # make sure the empty query tells you about queries
        response = self.slack_post('query')
        self.assertIn('num_minis', response['text'])

        # make sure we can run it
        # again, we can only check that the result is an int because we aren't
        # going through the django testing thing
        response = self.slack_post('query num_minis')
        int(response['text'].split('\n')[-1])

    def test_plot(self):
        self.slack_post(text='add :10 2018-08-01')
        self.slack_post(text='add :10 2018-08-02')
        self.slack_post(text='add :10 2018-08-03')
        self.slack_post(text='add :10 2018-08-04')
        response = self.slack_post(text='plot')
        self.assertIn(settings.MEDIA_URL,
                      response['attachments'][0]['image_url'])
