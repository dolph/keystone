# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 OpenStack, LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Rules-based Policy Engine."""

from keystone.common import kvs
from keystone import exception
from keystone.policy.backends import rules


class Policy(kvs.Base, rules.Policy):
    def create_policy(self, policy_id, policy):
        try:
            self.get_policy(policy_id)
        except:
            pass
        else:
            msg = 'Duplicate ID, %s.' % policy_id
            raise exception.Conflict(type='policy', details=msg)
        self.db.set('policy-%s' % policy_id, policy)
        policy_list = set(self.db.get('policy_list', []))
        policy_list.add(policy_id)
        self.db.set('policy_list', list(policy_list))
        return policy

    def list_policies(self):
        policy_ids = self.db.get('policy_list', [])
        return [self.get_policy(x) for x in policy_ids]

    def get_policy(self, policy_id):
        policy_ref = self.db.get('policy-%s' % policy_id)
        return policy_ref

    def update_policy(self, policy_id, policy):
        old_policy = self.db.get('policy-%s' % policy_id)
        new_policy = old_policy.copy()
        new_policy.update(policy)
        new_policy['id'] = policy_id
        self.db.set('policy-%s' % policy_id, new_policy)
        return new_policy

    def delete_policy(self, policy_id):
        self.db.delete('policy-%s' % policy_id)
        policy_list = set(self.db.get('policy_list', []))
        policy_list.remove(policy_id)
        self.db.set('policy_list', list(policy_list))
