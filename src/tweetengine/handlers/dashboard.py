import logging
from google.appengine.ext import db
from tweetengine.handlers import base
from tweetengine.oauth import TwitterClient
from tweetengine import model

class DashboardHandler(base.UserHandler):

    def get_tweets(self):
        q = model.OutgoingTweet.all()
        q.filter("account =", self.current_account)
        q.filter("sent =", False)
        return q.fetch(20)

    @base.requires_account
    def get(self, account_name):        
        self.render_template("dashboard.pt", {
            "tweets": self.get_tweets(),
        })

    @base.requires_account
    def post(self, account_name):
        if not self.current_permission.can_review():
            self.error(403)
            return
        q = self.get_tweets()
        tweet_map = dict((x.key().id(), x) for x in tweets)

        # Delete marked for deletion
        to_delete = [tweet_map[int(k.split(".")[1])]
                     for k, v in self.request.POST.iteritems()
                     if k.startswith("tweet.") and v=='delete']
        db.delete(to_delete)


        for k, v in self.request.POST.iteritems():
            if k.startswith("tweet.") and v=='send':
                tweet = tweet_map[int(k.split(".")[1])]
                tweet.approved_by = self.user_account
                response = tweet.send()
                if response.status_code != 200:
                    self.error(500)
                    logging.error(response.content)

        self.redirect('/%s/' % account_name)
