import hashlib
import hmac
import json
import time
import logging
import os.path
from datetime import datetime

import unittest
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase as DjangoTestCase
from django.test.client import RequestFactory
from django.urls import reverse
from django.contrib.staticfiles import finders
from django.utils import timezone

from crossbot.slack.commands import parse_date
from crossbot.slack.api import SLACK_URL
from crossbot.views import slash_command
from crossbot.models import (
    CBUser,
    MiniCrosswordTime,
    CrosswordTime,
    EasySudokuTime,
    QueryShorthand,
    Item,
    ItemOwnershipRecord,
)
from crossbot.cron import ReleaseAnnouncement, MorningAnnouncement
from crossbot.settings import CROSSBUCKS_PER_SOLVE


class TestCase(DjangoTestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        super().setUp()

    def tearDown(self):
        logging.disable(logging.NOTSET)
        super().tearDown()


class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def json(self):
        if type(self.text) is dict:
            return self.text
        else:
            return json.loads(self.text)


class MockedRequestTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.router = {}
        self._patcher_get = patch(
            'requests.get', side_effect=self.mocked_requests_get
        )
        self._patcher_post = patch(
            'requests.post', side_effect=self.mocked_requests_post
        )
        self._patcher_get.start()
        self._patcher_post.start()

    def tearDown(self):
        super().tearDown()
        self.router = {}
        self._patcher_get.stop()
        self._patcher_post.stop()

    def mocked_requests_get(self, url, **kwargs):
        return self.mocked_request('GET', url, **kwargs)

    def mocked_requests_post(self, url, **kwargs):
        return self.mocked_request('POST', url, **kwargs)

    def check_headers(self, method, url, headers):
        pass

    def mocked_request(self, method, url, *, headers, params=None, data=None):
        self.check_headers(method, url, headers)
        func = self.router.get(url)
        if func:
            return func(method, url, headers, params, data)
        else:
            MockResponse(None, 404)


class SlackTestCase(MockedRequestTestCase):
    RESPONSE_URL = SLACK_URL + 'response_url/'

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        self.router[SLACK_URL + 'chat.postMessage'] = self._slack_chat_post
        self.router[SLACK_URL + 'reactions.add'] = self._slack_reaction_add
        self.router[SLACK_URL + 'users.list'] = self._slack_users_list
        self.router[SLACK_URL + 'users.info'] = self._slack_users_info
        self.router[self.RESPONSE_URL] = self._slack_response_post

        self.users = {
            'UALICE': {
                'id': 'UALICE',
                'name': 'alice',
                'profile': {
                    'real_name': 'Alice',
                    'image_48': 'http://example.com/alice.png'
                }
            },
            'UBOB': {
                'id': 'UBOB',
                'name': 'bob',
                'profile': {
                    'real_name': 'Bob',
                    'image_48': 'http://example.com/bob.png'
                }
            }
        }

        self.slack_timestamp = 0
        self.messages = []

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patch(
            'django.conf.settings.SLACK_SECRET_SIGNING_KEY', self.slack_sk
        )
        self.patch(
            'django.conf.settings.SLACK_OAUTH_ACCESS_TOKEN', 'oauth_token'
        )
        self.patch(
            'django.conf.settings.SLACK_OAUTH_BOT_ACCESS_TOKEN',
            'bot_oauth_token'
        )
        self.patch(
            'django.conf.settings.CROSSBOT_MAIN_CHANNEL', 'main_channel'
        )

    def patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher

    def check_headers(self, method, url, headers):
        if url.startswith(SLACK_URL):
            self.assertEqual(
                headers['Authorization'], 'Bearer bot_oauth_token'
            )

    def _slack_reaction_add(self, method, url, headers, params, data):
        return MockResponse(json.dumps({'ok': True}), 200)

    def _slack_chat_post(self, method, url, headers, params, data):
        self.assertEqual(method, 'POST')
        self.messages.append(data)
        ts = self.slack_timestamp
        self.slack_timestamp += 1
        return MockResponse(json.dumps({'ok': True, 'ts': ts}), 200)

    def _slack_response_post(self, method, url, headers, params, data):
        # TODO: handle this better?
        self.assertEqual(method, 'POST')
        self.messages.append(data)
        ts = self.slack_timestamp
        self.slack_timestamp += 1
        return MockResponse('ok', 200)

    def _slack_users_list(self, method, url, headers, params, data):
        self.assertEqual(method, 'GET')
        return MockResponse({'ok': True, 'members': self.users.values()}, 200)

    def _slack_users_info(self, method, url, headers, params, data):
        self.assertEqual(method, 'GET')
        if params['user'] in self.users:
            return MockResponse({
                'ok': True,
                'user': self.users[params['user']]
            }, 200)
        return MockResponse({'ok': False, 'error': 'user_not_found'}, 400)

    def post_valid_request(self, post_data):
        request = self.factory.post(reverse('slash_command'), post_data)
        ts = str(time.time())
        request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP'] = ts
        request.META['HTTP_X_SLACK_SIGNATURE'] = 'v0=' + hmac.new(
            key=self.slack_sk,
            msg=b'v0:' + bytes(ts, 'utf8') + b':' + request.body,
            digestmod=hashlib.sha256
        ).hexdigest()
        return slash_command(request)

    def slack_post(
            self,
            text,
            who='alice',
            expected_status_code=200,
            expected_response_type='ephemeral'
    ):
        response = self.post_valid_request({
            'type': 'event_callback',
            'text': text,
            'response_url': self.RESPONSE_URL,
            'trigger_id': 'foobar',
            'channel_id': 'main_channel',
            'user_id': 'U' + who.upper(),
            'user_name': '@' + who,
        })

        self.assertEqual(response.status_code, expected_status_code)

        if response.content:
            body = json.loads(response.content)
            self.assertEqual(body['response_type'], expected_response_type)
            return body

        self.assertEqual(expected_response_type, 'ephemeral')
        return None


class ModelTests(SlackTestCase):
    def test_from_slackid(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertIsInstance(alice, CBUser)
        self.assertEqual(alice.slackname, 'alice')
        self.assertEqual(alice.slack_fullname, 'Alice')
        self.assertEqual(alice.image_url, 'http://example.com/alice.png')
        self.assertEqual(alice, CBUser.from_slackid('UALICE', 'bob'))
        alice = CBUser.from_slackid('UALICE')
        self.assertEqual(CBUser.from_slackid('UALICE').slackname, 'bob')

        fake_user = CBUser.from_slackid('UFAKE')
        self.assertIsNone(fake_user)
        with self.assertRaises(ValueError) as exception_context:
            fake_user = CBUser.from_slackid('UFAKE', 'fake_user')

        self.assertIn('user_not_found', str(exception_context.exception))

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
            alice.get_mini_crossword_time(parse_date(None)), None
        )

    def test_add_fail(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        a, t = alice.add_mini_crossword_time(-1, parse_date(None))
        self.assertTrue(a)
        self.assertEqual(t.seconds, -1)
        self.assertEqual(t.date, parse_date(None))
        self.assertTrue(t.is_fail())

    def test_streak(self):
        alice = CBUser.from_slackid('UALICE', 'alice')

        # set up a broken 10 streak
        _, t1 = alice.add_mini_crossword_time(18, parse_date('2018-01-01'))
        _, t2 = alice.add_mini_crossword_time(12, parse_date('2018-01-02'))
        _, t3 = alice.add_mini_crossword_time(12, parse_date('2018-01-03'))
        _, t4 = alice.add_mini_crossword_time(15, parse_date('2018-01-04'))
        # t5 is missing
        _, t6 = alice.add_mini_crossword_time(15, parse_date('2018-01-06'))
        _, t7 = alice.add_mini_crossword_time(15, parse_date('2018-01-07'))
        _, t8 = alice.add_mini_crossword_time(15, parse_date('2018-01-08'))
        _, t9 = alice.add_mini_crossword_time(15, parse_date('2018-01-09'))
        _, t0 = alice.add_mini_crossword_time(18, parse_date('2018-01-10'))

        # make sure the streak is broken
        streaks = MiniCrosswordTime.participation_streaks(alice)
        self.assertListEqual(streaks, [[t1, t2, t3, t4], [t6, t7, t8, t9, t0]])

        # fix the broken streak
        _, t5 = alice.add_mini_crossword_time(15, parse_date('2018-01-05'))

        streaks = MiniCrosswordTime.participation_streaks(alice)
        self.assertListEqual(
            streaks, [[t1, t2, t3, t4, t5, t6, t7, t8, t9, t0]]
        )

        # now break it again with a deleted time (t2)
        alice.remove_mini_crossword_time(parse_date('2018-01-02'))
        streaks = MiniCrosswordTime.participation_streaks(alice)
        self.assertListEqual(streaks, [[t1], [t3, t4, t5, t6, t7, t8, t9, t0]])

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

    def test_wins(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        bob = CBUser.from_slackid('UBOB', 'bob')

        d = {x: parse_date('2018-01-0' + str(x)) for x in range(1, 6)}

        # make sure winners is empty right now
        self.assertEqual([], MiniCrosswordTime.winners(d[1]))

        # alice wins
        _, a1 = alice.add_mini_crossword_time(10, d[1])
        _, b1 = bob.add_mini_crossword_time(11, d[1])

        # they tie
        _, a2 = alice.add_mini_crossword_time(15, d[2])
        _, b2 = bob.add_mini_crossword_time(15, d[2])

        # bob wins
        _, a3 = alice.add_mini_crossword_time(21, d[3])
        _, b3 = bob.add_mini_crossword_time(20, d[3])

        # alice wins
        _, a4 = alice.add_mini_crossword_time(18, d[4])
        _, b4 = bob.add_mini_crossword_time(19, d[4])

        # check the winners
        self.assertEqual([a1], MiniCrosswordTime.winners(d[1]))
        self.assertEqual([a2, b2], MiniCrosswordTime.winners(d[2]))
        self.assertEqual([b3], MiniCrosswordTime.winners(d[3]))
        self.assertEqual([a4], MiniCrosswordTime.winners(d[4]))

        # check the winning times
        winning_times = MiniCrosswordTime.winning_times()
        expected = {d[1]: 10, d[2]: 15, d[3]: 20, d[4]: 18}
        self.assertEqual(winning_times, expected)

        # check the actual wins
        a_wins = MiniCrosswordTime.wins(alice)
        self.assertEqual(a_wins, [a1, a2, a4])
        b_wins = MiniCrosswordTime.wins(bob)
        self.assertEqual(b_wins, [b2, b3])

        # check the streaks
        a_win_streaks = MiniCrosswordTime.win_streaks(alice)
        self.assertEqual(a_win_streaks, [[a1, a2], [a4]])
        b_win_streaks = MiniCrosswordTime.win_streaks(bob)
        self.assertEqual(b_win_streaks, [[b2, b3]])

        # check the win streaks
        self.assertEqual({
            alice: [a1, a2],
            bob: [b2]
        }, MiniCrosswordTime.current_win_streaks(d[2]))
        self.assertEqual({
            bob: [b2, b3]
        }, MiniCrosswordTime.current_win_streaks(d[3]))
        self.assertEqual({}, MiniCrosswordTime.current_win_streaks(d[5]))

    def test_items(self):
        # Just add one item
        alice = CBUser.from_slackid('UALICE', 'alice')
        tophat = Item.from_key('tophat')
        self.assertEqual(tophat.key, 'tophat')
        self.assertEqual(alice.quantity_owned(tophat), 0)

        alice.add_item(tophat, amount=2)
        self.assertEqual(alice.quantity_owned(tophat), 2)
        self.assertEqual(alice.quantity_owned(Item.from_key('tophat')), 2)
        record = ItemOwnershipRecord.objects.get(
            owner=alice, item_key=tophat.key
        )
        self.assertEqual(record.quantity, 2)
        self.assertEqual(record.item, tophat)

        self.assertTrue(alice.remove_item(tophat, amount=2))
        self.assertEqual(alice.quantity_owned(tophat), 0)
        try:
            ItemOwnershipRecord.objects.get(owner=alice, item_key=tophat.key)
            self.fail()
        except ItemOwnershipRecord.DoesNotExist:
            pass

        # Check that the item image actually exists on disk
        url = tophat.image_url()
        self.assertEqual(settings.STATIC_URL, url[:len(settings.STATIC_URL)])
        url = url.replace(settings.STATIC_URL, '', 1)
        path = finders.find(url)
        self.assertTrue(os.path.isfile(path))


class SlackAuthTests(SlackTestCase):
    def test_bad_signature(self):
        response = self.client.post(
            reverse('slash_command'),
            HTTP_X_SLACK_REQUEST_TIMESTAMP=str(time.time()),
            HTTP_X_SLACK_SIGNATURE=b''
        )
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
        response = self.slack_post(
            'times 2018-8-1', expected_response_type='in_channel'
        )

        lines = response['text'].split('\n')

        # line 0 is date, line 1 should be Alice
        self.assertIn('Alice', lines[1])
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
        response = self.slack_post(
            text='times 2018-08-01', expected_response_type='in_channel'
        )
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
            text='sql select * from mini_crossword_time'
        )
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

    def test_add_streak(self):
        # build up to a streak of 3
        self.slack_post(text='add :10 2018-08-01')
        self.slack_post(text='add :10 2018-08-02')
        # make sure the message didn't come in early
        self.assertNotIn('streak', self.messages[-1])

        # get the streak of 3 and check for acknowledgment
        self.slack_post(text='add :10 2018-08-03')
        # the messages for streaks of 3 have the word row in them
        self.assertIn('3', self.messages[-1])
        self.assertIn('row', self.messages[-1])

        # go for the streak of 10
        for i in range(4, 11):
            self.slack_post(text='add :10 2018-08-{:02d}'.format(i))
        self.assertIn('10', self.messages[-1])
        self.assertIn('streak', self.messages[-1])

    def test_plot(self):
        self.slack_post(text='add :10 2018-08-01')
        self.slack_post(text='add :10 2018-08-02')
        self.slack_post(text='add :10 2018-08-03')
        self.slack_post(text='add :10 2018-08-04')
        response = self.slack_post(
            text='plot', expected_response_type='in_channel'
        )
        self.assertIn(
            settings.MEDIA_URL, response['attachments'][0]['image_url']
        )


class AnnouncementTests(SlackTestCase):
    def setUp(self):
        super().setUp()
        self.release_announcement = ReleaseAnnouncement()
        self.morning_announcement = MorningAnnouncement()
        tz = timezone.get_default_timezone()
        self.weekday_wrong_time = datetime(2018, 10, 25, 15, tzinfo=tz)
        self.weekday_right_time = datetime(2018, 10, 25, 19, tzinfo=tz)
        self.weekend_wrong_time = datetime(2018, 10, 27, 19, tzinfo=tz)
        self.weekend_right_time = datetime(2018, 10, 27, 15, tzinfo=tz)

    def test_release_announcement_should_run_now(self):
        self.assertFalse(
            self.release_announcement.should_run_now(self.weekday_wrong_time)
        )
        self.assertTrue(
            self.release_announcement.should_run_now(self.weekday_right_time)
        )
        self.assertFalse(
            self.release_announcement.should_run_now(self.weekend_wrong_time)
        )
        self.assertTrue(
            self.release_announcement.should_run_now(self.weekend_right_time)
        )

    def test_release_announcement_run(self):
        with patch.object(timezone, 'localtime',
                          return_value=self.weekday_right_time):
            self.release_announcement.do()
            self.assertEqual(len(self.messages), 1)

    def test_morning_announcement_run(self):
        self.morning_announcement.do()
        self.assertEqual(len(self.messages), 1)


class MiscTests(TestCase):
    def test_comma_and(self):
        from crossbot.util import comma_and

        self.assertEqual('', comma_and([]))
        self.assertEqual('bob', comma_and(['bob']))
        self.assertEqual('alice and bob', comma_and(['alice', 'bob']))
        self.assertEqual(
            'alice, bob, and charlie', comma_and(['alice', 'bob', 'charlie'])
        )


class PredictorTests(TestCase):
    data = {
        'U1': [None, 62, 38, 28, 42, 17],
        'U2': [73, 72, 36, 37, 51, None],
    }

    def setUp(self):
        self.maxDiff = None
        for u, ts in self.data.items():
            user = CBUser(slackid=u)
            user.save()
            for i, t in enumerate(ts):
                if t is not None:
                    user.add_mini_crossword_time(
                        t, parse_date("2018-01-0" + str(i + 1))
                    )

    def test_predictor(self):
        import crossbot.predictor as p
        data = p.data()
        fit = p.fit(data)
        model = p.extract_model(data, fit)
        p.save(model)
        model2 = p.load()
        self.assertDictEqual(model, model2)

    def test_cron(self):
        from crossbot.cron import Predictor
        Predictor().do()

