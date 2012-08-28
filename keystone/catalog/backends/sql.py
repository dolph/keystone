# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 OpenStack LLC
# Copyright 2012 Canonical Ltd.
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

from keystone import catalog
from keystone.common import sql
from keystone.common.sql import migration
from keystone import config
from keystone import exception


CONF = config.CONF


class Service(sql.ModelBase, sql.DictBase):
    __tablename__ = 'service'
    id = sql.Column(sql.String(64), primary_key=True)
    type = sql.Column(sql.String(255))
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, service_dict):
        extra = {}
        for k, v in service_dict.copy().iteritems():
            if k not in ['id', 'type', 'extra']:
                extra[k] = service_dict.pop(k)

        service_dict['extra'] = extra
        return cls(**service_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['type'] = self.type
        return extra_copy


class Endpoint(sql.ModelBase, sql.DictBase):
    __tablename__ = 'endpoint'
    id = sql.Column(sql.String(64), primary_key=True)
    region = sql.Column('region', sql.String(255))
    service_id = sql.Column(sql.String(64),
                            sql.ForeignKey('service.id'),
                            nullable=False)
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, endpoint_dict):
        extra = {}
        for k, v in endpoint_dict.copy().iteritems():
            if k not in ['id', 'region', 'service_id', 'extra']:
                extra[k] = endpoint_dict.pop(k)
        endpoint_dict['extra'] = extra
        return cls(**endpoint_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['region'] = self.region
        extra_copy['service_id'] = self.service_id
        return extra_copy


class Catalog(sql.Base, catalog.Driver):
    def db_sync(self):
        migration.db_sync()

    # Services
    def list_services(self):
        session = self.get_session()
        services = session.query(Service)
        return [s['id'] for s in list(services)]

    def get_all_services(self):
        session = self.get_session()
        services = session.query(Service).all()
        return [s.to_dict() for s in list(services)]

    def get_service(self, service_id):
        session = self.get_session()
        service_ref = session.query(Service).filter_by(id=service_id).first()
        if not service_ref:
            raise exception.ServiceNotFound(service_id=service_id)
        return service_ref.to_dict()

    def delete_service(self, service_id):
        session = self.get_session()
        with session.begin():
            if not session.query(Service).filter_by(id=service_id).delete():
                raise exception.ServiceNotFound(service_id=service_id)
            session.flush()

    def create_service(self, service_id, service_ref):
        session = self.get_session()
        with session.begin():
            service = Service.from_dict(service_ref)
            session.add(service)
            session.flush()
        return service.to_dict()

    def update_service(self, service_id, service_ref):
        session = self.get_session()
        with session.begin():
            ref = session.query(Service).filter_by(id=service_id).first()
            if ref is None:
                raise exception.ServiceNotFound(service_id=service_id)
            old_dict = ref.to_dict()
            for k in service_ref:
                old_dict[k] = service_ref[k]
            new_service = Service.from_dict(old_dict)
            ref.type = new_service.type
            ref.extra = new_service.extra
            session.flush()
        return ref.to_dict()

    # Endpoints
    def create_endpoint(self, endpoint_id, endpoint_ref):
        session = self.get_session()
        self.get_service(endpoint_ref['service_id'])
        new_endpoint = Endpoint.from_dict(endpoint_ref)
        with session.begin():
            session.add(new_endpoint)
            session.flush()
        return new_endpoint.to_dict()

    def delete_endpoint(self, endpoint_id):
        session = self.get_session()
        with session.begin():
            if not session.query(Endpoint).filter_by(id=endpoint_id).delete():
                raise exception.EndpointNotFound(endpoint_id=endpoint_id)
            session.flush()

    def get_endpoint(self, endpoint_id):
        session = self.get_session()
        endpoint_ref = session.query(Endpoint)
        endpoint_ref = endpoint_ref.filter_by(id=endpoint_id).first()
        if not endpoint_ref:
            raise exception.EndpointNotFound(endpoint_id=endpoint_id)
        return endpoint_ref.to_dict()

    def list_endpoints(self):
        session = self.get_session()
        endpoints = session.query(Endpoint)
        return [e['id'] for e in list(endpoints)]

    def get_all_endpoints(self):
        session = self.get_session()
        endpoints = session.query(Endpoint)
        return [e.to_dict() for e in list(endpoints)]

    def update_endpoint(self, endpoint_id, endpoint_ref):
        session = self.get_session()
        with session.begin():
            ref = session.query(Endpoint).filter_by(id=endpoint_id).first()
            if ref is None:
                raise exception.EndpointNotFound(endpoint_id=endpoint_id)
            old_dict = ref.to_dict()
            for k in endpoint_ref:
                old_dict[k] = endpoint_ref[k]
            new_endpoint = Endpoint.from_dict(old_dict)
            ref.service_id = new_endpoint.service_id
            ref.region = new_endpoint.region
            ref.extra = new_endpoint.extra
            session.flush()
        return ref.to_dict()

    def get_catalog(self, user_id, tenant_id, metadata=None):
        d = dict(CONF.iteritems())
        d.update({'tenant_id': tenant_id,
                  'user_id': user_id})
        catalog = {}

        endpoints = [self.get_endpoint(e)
                     for e in self.list_endpoints()]
        for ep in endpoints:
            service = self.get_service(ep['service_id'])
            srv_type = service['type']
            srv_name = service['name']
            region = ep['region']

            if region not in catalog:
                catalog[region] = {}

            catalog[region][srv_type] = {}

            internal_url = ep['internalurl'].replace('$(', '%(')
            public_url = ep['publicurl'].replace('$(', '%(')
            admin_url = ep['adminurl'].replace('$(', '%(')
            catalog[region][srv_type]['name'] = srv_name
            catalog[region][srv_type]['publicURL'] = public_url % d
            catalog[region][srv_type]['adminURL'] = admin_url % d
            catalog[region][srv_type]['internalURL'] = internal_url % d

        return catalog
