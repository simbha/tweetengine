import hashlib
import hmac
import logging
import os
import urllib
import uuid
import urlparse
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from tweetengine.handlers import base
from tweetengine import model

class ManageHandler(base.UserHandler):
    @base.requires_account_admin
    def get(self, account_name):
        permissions = model.Permission.all().filter("account =", self.current_account).fetch(100)
        my_key = self.account_admin.key()
        self.render_template("manage.html", {
            "acct_permissions": permissions,
            "my_key": my_key,
            "sent": self.request.GET.get("sent", False),
        })

    @base.requires_account_admin
    def post(self, account_name):
        permissions = model.Permission.all().filter("account =", self.current_account).fetch(100)
        permission_map = dict((x.key().id(), x) for x in permissions)
        my_id = self.account_admin.key().id()
        
        # Handle deletion
        to_delete = [permission_map[int(x)]
                     for x in self.request.POST.getall("delete")
                     if int(x) in permission_map and x != my_id]
        db.delete(to_delete)
        
        # Handle permission changes
        new_permissions = [(int(k.split(".")[1]), int(v))
                           for k, v in self.request.POST.iteritems()
                           if k.startswith("permission.")]
        to_update = []
        for perm_id, role in new_permissions:
            if perm_id == my_id:
                continue
            permission = permission_map[perm_id]
            if permission.role != role:
                permission.role = role
                to_update.append(permission)
        db.put(to_update)
        
        # Handle new users
        invites = zip(self.request.POST.getall("username"),
                      self.request.POST.getall("new_permission"))
        invites = [x for x in invites if x[0]]
        self.send_invites(invites)
        
        if invites:
            self.redirect("/%s/manage?sent=true" % (self.current_account.username,))
        else:
            self.redirect("/%s/manage")

    def send_invites(self, invites):
        config = model.Configuration.instance()
        template_path = os.path.join(os.path.dirname(__file__), "..",
                                     "templates", "email.txt")
        account_username = self.current_account.username
        for username, role in invites:
            nonce = str(uuid.uuid4())
            mac_data = ":".join([account_username, role, nonce])
            mac = hmac.new(config.oauth_secret, mac_data, hashlib.sha1).hexdigest()
            qs = urllib.urlencode({
                "role": role,
                "nonce": nonce,
                "mac": mac
            })
            url = urlparse.urljoin(
                self.request.url,
                "/%s/invite?%s" % (account_username, qs))
            email_body = template.render(template_path, {
                "account_username": account_username,
                "username": username,
                "url": url
            })
            logging.info(email_body)
            subject = "You have been invited to tweet as %s!" % (account_username,)
            mail.send_mail(config.mail_from, username, subject, email_body)


class InviteHandler(base.UserHandler):
    @base.requires_account
    def get(self, account_name):
        config = model.Configuration.instance()
        role = self.request.GET.get("role", model.ROLE_USER)
        nonce = self.request.GET["nonce"]
        
        # Verify the mac
        mac_data = ":".join([account_name, role, nonce])
        mac = hmac.new(config.oauth_secret, mac_data, hashlib.sha1).hexdigest()
        if mac != self.request.GET["mac"]:
            logging.error("Invalid MAC")
            self.error(400)
            return
        
        # Check the nonce hasn't been reused
        if model.Permission.all().filter("invite_nonce =", nonce).count():
            logging.error("Reused nonce")
            self.error(400)
            return
        
        # Add the permission record
        q = model.Permission.all()
        q.filter("user =", self.user_account)
        q.filter("account =", self.current_account)
        if q.count() == 0:
            permission = model.Permission(
                user=self.user_account,
                account=self.current_account,
                role=int(role),
                invite_nonce=nonce)
            permission.put()
        self.redirect("/%s/" % (self.current_account.username,))
