from google.appengine.ext import db
from google.appengine.ext.db import polymodel


class UserAccount(polymodel.PolyModel):
    pass


class GoogleUserAccount(UserAccount):
    user = db.UserProperty(required=True)


class TwitterAccount(db.Model):
    oauth_token = db.TextProperty(required=True)
    oauth_secret = db.TextProperty(required=True)
    name = db.TextProperty()
    picture = db.TextProperty()

    @property
    def username(self):
        return self.key().name()


ROLE_USER = 1
ROLE_ADMINISTRATOR = 2


class Permission(db.Model):
    user = db.ReferenceProperty(UserAccount, required=True)
    account = db.ReferenceProperty(TwitterAccount, required=True)
    role = db.IntegerProperty(required=True,
                              choices=[ROLE_USER, ROLE_ADMINISTRATOR])


class OutgoingTweet(db.Model):
    account = db.ReferenceProperty(TwitterAccount, required=True)
    user = db.ReferenceProperty(UserAccount, required=True,
                                collection_name='tweets')
    approved_by = db.ReferenceProperty(UserAccount, required=True,
                                       collection_name='approved_tweets')
    message = db.TextProperty(required=True)
    timestamp = db.DateTimeProperty(required=True, auto_now_add=True)


class Configuration(db.Model):
    secret = db.StringProperty()
    key = db.StringProperty()

    @classmethod
    def instance(cls):
        return cls.get_or_insert('key')
