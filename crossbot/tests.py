from datetime import date
from django.test import TestCase
from django.utils import timezone

from crossbot.models import MiniCrosswordTime, MyUser

# Create your tests here.

class SimpleTests(TestCase):

    def test_something(self):

        alice = MyUser.objects.create_user('alice')
        bob = MyUser.objects.create_user('bob')
        charlie = MyUser.objects.create_user('charlie')

        print(MyUser.objects.all())

        MiniCrosswordTime.objects.bulk_create([
            MiniCrosswordTime(seconds=20, user=alice, date=date(2018, 5, 5))
        ])

        print(MiniCrosswordTime.objects.all())


        self.assertEqual(1, 1)
