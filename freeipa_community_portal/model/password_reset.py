# Authors:
#   Drew Erny <derny@redhat.com>
#
# Copyright (C) 2015  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, timedelta
import os
import base64

from sqlalchemy import Table, Column, MetaData, String, DateTime, create_engine
from sqlalchemy.sql import select, insert, delete

import ConfigParser

from ipalib import api, errors

from . import api_connect


Config = ConfigParser.ConfigParser()
Config.read(['/etc/freeipa_community_portal.ini', 'conf/freeipa_community_portal_dev.ini'])

DATABASE_LOCATION = Config.get('Database', 'db_directory') + 'resets.db'

_engine = create_engine('sqlite:///' + DATABASE_LOCATION)

_metadata = MetaData()
_password_reset = Table('password_reset', _metadata,
    Column('username', String, primary_key=True),
    Column('token', String),
    Column('timestamp', DateTime)
)

_metadata.create_all(_engine)

USE_BY = timedelta(days=3)

class PasswordReset(object):
    """Represents a password reset object"""

    def __init__(self, username):
        self.username = username
        self.token = base64.urlsafe_b64encode(os.urandom(8)).rstrip('=')
        self.timestamp = datetime.now()
        self.email = None
        self._valid = None

    @staticmethod
    def load(username):
        """Class method. Load a password reset, if one exists.

        :param: username - the user to laod

        :return: a PasswordReset object associated with the user if one exists,
        None otherwise
        """
        # connect to the database
        conn = _engine.connect()
        # and grab a record cooresponding to this username
        result = conn.execute(
            select([_password_reset]).where(_password_reset.c.username == username)
        )

        row = result.first()
        # if there is no result, return None
        if row is None:
            reset = None
        # or the result is too old, expire the result and return None
        elif (datetime.now() - row['timestamp']) > USE_BY:
            reset = None
            PasswordReset.expire(row['username'])
        # but if the result is valid...
        else:
            reset = PasswordReset(row['username'])
            reset.token = row['token']
            reset.timestamp =  row['timestamp']

        # close our resources
        conn.close()
        return reset

    def save(self):
        if self.check_valid():
            conn = _engine.connect()
            self.expire(self.username)
            conn.execute(
                _password_reset.insert().values(
                    username=self.username,
                    token=self.token,
                    timestamp = self.timestamp
                )
            )
            conn.close()

    def check_valid(self):
        """checks the validity of the the user provided by querying the ipa
        server
        """
        if self._valid is not None:
            return self._valid

        api_connect()

        try:
            response = api.Command.user_show(uid=self.username)
        except errors.NotFound:
            self._valid = False
            return self._valid

        # i'm sorry mom
        if response['result'].has_key('mail') \
                and response['result']['mail'] is not None \
                and not response['result']['mail'][0].isspace():
            self.email = response['result']['mail'][0]
            self._valid = True
        else:
            self._valid = False
        return self._valid

    def reset_password(self):
        """Calls the IPA API and sets the password to a new, random value"""
        newpass = base64.urlsafe_b64encode(os.urandom(8)).rstrip('=')
        api_connect()
        api.Command.passwd(self.username, password=unicode(newpass))
        return newpass

    @staticmethod
    def expire(username):
        conn = _engine.connect()
        conn.execute(
            delete(_password_reset).where(_password_reset.c.username == username)
        )
        conn.close()
    
