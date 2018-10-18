"""Custom OAuth pipelines for Slack sign-in."""

from django.conf import settings
from social_core.pipeline.social_auth import AuthForbidden

from .models import CBUser


def auth_correct_team(response, *args, **kwargs):
    """If defined a specific team to use, restrict sign-in to that team."""
    team = response.get('team', {}).get('id', None)
    if team is None:
        raise AuthForbidden("No team info returned from Slack.")
    if (hasattr(settings, 'SOCIAL_AUTH_SLACK_TEAM') and
            team != settings.SOCIAL_AUTH_SLACK_TEAM):
        raise AuthForbidden("Team not authorized.")


def slackid_as_username(details, response, *args, **kwargs):
    """Use SlackID as username instead of Slack username."""
    new_details = details.copy()

    slackid = response.get('user', {}).get('id', None)
    if slackid is None:
        return
    new_details['username'] = slackid
    if 'username' in details:
        new_details['slackname'] = details['username']

    return {'details': new_details}


def associate_cb_user(response, user=None, *args, **kwargs):
    """Associate auth account with CBUser account."""
    if user is None:
        return
    slackid = response.get('user', {}).get('id', None)
    if slackid is None:
        return
    cb_user = CBUser.from_slackid(slackid)
    if cb_user.auth_user != user:
        cb_user.auth_user = user
        cb_user.save()
