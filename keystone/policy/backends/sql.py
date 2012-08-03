# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import functools

from keystone.common import sql
from keystone.common.sql import migration
from keystone import exception
from keystone.policy.backends import rules


def handle_conflicts(type='object'):
    """Converts IntegrityError into HTTP 409 Conflict."""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except sql.IntegrityError as e:
                raise exception.Conflict(type=type, details=str(e))
        return wrapper
    return decorator


class PolicyModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'policy'
    id = sql.Column(sql.String(64), primary_key=True)
    endpoint_id = sql.Column(sql.String(64), nullable=False)
    blob = sql.Column(sql.JsonBlob(), nullable=False)
    type = sql.Column(sql.String(255), nullable=False)
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, user_dict):
        # shove any non-indexed properties into extra
        extra = {}
        for k, v in user_dict.copy().iteritems():
            # TODO(termie): infer this somehow
            if k not in ['id', 'endpoint_id', 'blob', 'type', 'extra']:
                extra[k] = user_dict.pop(k)

        user_dict['extra'] = extra
        return cls(**user_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['endpoint_id'] = self.endpoint_id
        extra_copy['blob'] = self.blob
        extra_copy['type'] = self.type
        return extra_copy


class Policy(sql.Base, rules.Policy):
    # Internal interface to manage the database
    def db_sync(self):
        migration.db_sync()

    @handle_conflicts(type='policy')
    def create_policy(self, policy_id, policy):
        session = self.get_session()
        with session.begin():
            ref = PolicyModel.from_dict(policy)
            session.add(ref)
            session.flush()
        return ref.to_dict()

    def list_policies(self):
        session = self.get_session()
        refs = session.query(PolicyModel).all()
        return [ref.to_dict() for ref in refs]

    def get_policy(self, policy_id):
        session = self.get_session()
        ref = session.query(PolicyModel).filter_by(id=policy_id).first()
        if ref is None:
            raise exception.PolicyNotFound(policy_id=policy_id)
        return ref.to_dict()

    @handle_conflicts(type='policy')
    def update_policy(self, policy_id, policy):
        session = self.get_session()
        with session.begin():
            ref = session.query(PolicyModel).filter_by(id=policy_id).first()
            if ref is None:
                raise exception.PolicyNotFound(policy_id=policy_id)
            old_dict = ref.to_dict()
            for k in policy:
                old_dict[k] = policy[k]
            new_policy = PolicyModel.from_dict(old_dict)
            ref.endpoint_id = new_policy.endpoint_id
            ref.blob = new_policy.blob
            ref.type = new_policy.type
            ref.extra = new_policy.extra
            session.flush()
        return ref.to_dict()

    def delete_policy(self, policy_id):
        session = self.get_session()
        ref = session.query(PolicyModel).filter_by(id=policy_id).first()
        if not ref:
            raise exception.PolicyNotFound(policy_id=policy_id)
        with session.begin():
            session.delete(ref)
            session.flush()
