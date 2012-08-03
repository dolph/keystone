import uuid

import test_v3


class PolicyTestCase(test_v3.RestfulTestCase):
    """Test policy CRUD"""

    def setUp(self):
        super(PolicyTestCase, self).setUp()

        self.service_id = uuid.uuid4().hex
        self.service = self.new_service_ref()
        self.service['id'] = self.service_id
        self.catalog_api.create_service(
            self.service_id,
            self.service.copy())

        self.endpoint_id = uuid.uuid4().hex
        self.endpoint = self.new_endpoint_ref(service_id=self.service_id)
        self.endpoint['id'] = self.endpoint_id
        self.catalog_api.create_endpoint(
            self.endpoint_id,
            self.endpoint.copy())

        self.policy_id = uuid.uuid4().hex
        self.policy = self.new_policy_ref(endpoint_id=self.endpoint_id)
        self.policy['id'] = self.policy_id
        self.policy_api.create_policy(
            self.policy_id,
            self.policy.copy())

    # policy validation

    def assertValidPolicyListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'policies',
            self.assertValidPolicy,
            ref)

    def assertValidPolicyResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'policy',
            self.assertValidPolicy,
            ref)

    def assertValidPolicy(self, entity, ref=None):
        self.assertIsNotNone(entity.get('blob'))
        self.assertIsNotNone(entity.get('type'))
        self.assertIsNotNone(entity.get('endpoint_id'))
        if ref:
            self.assertEqual(ref['blob'], entity['blob'])
            self.assertEqual(ref['type'], entity['type'])
            self.assertEqual(ref['endpoint_id'], entity['endpoint_id'])
        return entity

    # policy crud tests

    def test_create_policy(self):
        """POST /policies"""
        ref = self.new_policy_ref(endpoint_id=self.endpoint_id)
        r = self.post(
            '/policies',
            body={'policy': ref})
        return self.assertValidPolicyResponse(r, ref)

    def test_list_policies(self):
        """GET /policies"""
        r = self.get('/policies')
        self.assertValidPolicyListResponse(r, self.policy)

    def test_get_policy(self):
        """GET /policies/{policy_id}"""
        r = self.get(
            '/policies/%(policy_id)s' % {
                'policy_id': self.policy_id})
        self.assertValidPolicyResponse(r, self.policy)

    def test_update_policy(self):
        """PATCH /policies/{policy_id}"""
        policy = self.new_policy_ref(endpoint_id=self.endpoint_id)
        policy['id'] = self.policy_id
        r = self.patch(
            '/policies/%(policy_id)s' % {
                'policy_id': self.policy_id},
            body={'policy': policy})
        self.assertValidPolicyResponse(r, policy)

    def test_delete_policy(self):
        """DELETE /policies/{policy_id}"""
        self.delete(
            '/policies/%(policy_id)s' % {
                'policy_id': self.policy_id})
