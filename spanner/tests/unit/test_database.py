# Copyright 2016 Google LLC All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest

import mock

from google.cloud.spanner_v1 import __version__


def _make_credentials():  # pragma: NO COVER
    import google.auth.credentials

    class _CredentialsWithScopes(
            google.auth.credentials.Credentials,
            google.auth.credentials.Scoped):
        pass

    return mock.Mock(spec=_CredentialsWithScopes)


class _BaseTest(unittest.TestCase):

    PROJECT_ID = 'project-id'
    PARENT = 'projects/' + PROJECT_ID
    INSTANCE_ID = 'instance-id'
    INSTANCE_NAME = PARENT + '/instances/' + INSTANCE_ID
    DATABASE_ID = 'database_id'
    DATABASE_NAME = INSTANCE_NAME + '/databases/' + DATABASE_ID
    SESSION_ID = 'session_id'
    SESSION_NAME = DATABASE_NAME + '/sessions/' + SESSION_ID

    def _make_one(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)


class TestDatabase(_BaseTest):

    def _getTargetClass(self):
        from google.cloud.spanner_v1.database import Database

        return Database

    def test_ctor_defaults(self):
        from google.cloud.spanner_v1.pool import BurstyPool

        instance = _Instance(self.INSTANCE_NAME)

        database = self._make_one(self.DATABASE_ID, instance)

        self.assertEqual(database.database_id, self.DATABASE_ID)
        self.assertIs(database._instance, instance)
        self.assertEqual(list(database.ddl_statements), [])
        self.assertIsInstance(database._pool, BurstyPool)
        # BurstyPool does not create sessions during 'bind()'.
        self.assertTrue(database._pool._sessions.empty())

    def test_ctor_w_explicit_pool(self):
        instance = _Instance(self.INSTANCE_NAME)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)
        self.assertEqual(database.database_id, self.DATABASE_ID)
        self.assertIs(database._instance, instance)
        self.assertEqual(list(database.ddl_statements), [])
        self.assertIs(database._pool, pool)
        self.assertIs(pool._bound, database)

    def test_ctor_w_ddl_statements_non_string(self):

        with self.assertRaises(ValueError):
            self._make_one(
                self.DATABASE_ID, instance=object(),
                ddl_statements=[object()])

    def test_ctor_w_ddl_statements_w_create_database(self):

        with self.assertRaises(ValueError):
            self._make_one(
                self.DATABASE_ID, instance=object(),
                ddl_statements=['CREATE DATABASE foo'])

    def test_ctor_w_ddl_statements_ok(self):
        from tests._fixtures import DDL_STATEMENTS

        instance = _Instance(self.INSTANCE_NAME)
        pool = _Pool()
        database = self._make_one(
            self.DATABASE_ID, instance, ddl_statements=DDL_STATEMENTS,
            pool=pool)
        self.assertEqual(database.database_id, self.DATABASE_ID)
        self.assertIs(database._instance, instance)
        self.assertEqual(list(database.ddl_statements), DDL_STATEMENTS)

    def test_from_pb_bad_database_name(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)

        database_name = 'INCORRECT_FORMAT'
        database_pb = admin_v1_pb2.Database(name=database_name)
        klass = self._getTargetClass()

        with self.assertRaises(ValueError):
            klass.from_pb(database_pb, None)

    def test_from_pb_project_mistmatch(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)

        ALT_PROJECT = 'ALT_PROJECT'
        client = _Client(project=ALT_PROJECT)
        instance = _Instance(self.INSTANCE_NAME, client)
        database_pb = admin_v1_pb2.Database(name=self.DATABASE_NAME)
        klass = self._getTargetClass()

        with self.assertRaises(ValueError):
            klass.from_pb(database_pb, instance)

    def test_from_pb_instance_mistmatch(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)

        ALT_INSTANCE = '/projects/%s/instances/ALT-INSTANCE' % (
            self.PROJECT_ID,)
        client = _Client()
        instance = _Instance(ALT_INSTANCE, client)
        database_pb = admin_v1_pb2.Database(name=self.DATABASE_NAME)
        klass = self._getTargetClass()

        with self.assertRaises(ValueError):
            klass.from_pb(database_pb, instance)

    def test_from_pb_success_w_explicit_pool(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client)
        database_pb = admin_v1_pb2.Database(name=self.DATABASE_NAME)
        klass = self._getTargetClass()
        pool = _Pool()

        database = klass.from_pb(database_pb, instance, pool=pool)

        self.assertTrue(isinstance(database, klass))
        self.assertEqual(database._instance, instance)
        self.assertEqual(database.database_id, self.DATABASE_ID)
        self.assertIs(database._pool, pool)

    def test_from_pb_success_w_hyphen_w_default_pool(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)
        from google.cloud.spanner_v1.pool import BurstyPool

        DATABASE_ID_HYPHEN = 'database-id'
        DATABASE_NAME_HYPHEN = (
            self.INSTANCE_NAME + '/databases/' + DATABASE_ID_HYPHEN)
        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client)
        database_pb = admin_v1_pb2.Database(name=DATABASE_NAME_HYPHEN)
        klass = self._getTargetClass()

        database = klass.from_pb(database_pb, instance)

        self.assertTrue(isinstance(database, klass))
        self.assertEqual(database._instance, instance)
        self.assertEqual(database.database_id, DATABASE_ID_HYPHEN)
        self.assertIsInstance(database._pool, BurstyPool)
        # BurstyPool does not create sessions during 'bind()'.
        self.assertTrue(database._pool._sessions.empty())

    def test_name_property(self):
        instance = _Instance(self.INSTANCE_NAME)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)
        expected_name = self.DATABASE_NAME
        self.assertEqual(database.name, expected_name)

    def test_spanner_api_property_w_scopeless_creds(self):
        client = _Client()
        credentials = client.credentials = object()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        patch = mock.patch('google.cloud.spanner_v1.database.SpannerClient')

        with patch as spanner_client:
            api = database.spanner_api

        self.assertIs(api, spanner_client.return_value)

        # API instance is cached
        again = database.spanner_api
        self.assertIs(again, api)

        spanner_client.assert_called_once_with(
            lib_name='gccl',
            lib_version=__version__,
            credentials=credentials)

    def test_spanner_api_w_scoped_creds(self):
        import google.auth.credentials
        from google.cloud.spanner_v1.database import SPANNER_DATA_SCOPE

        class _CredentialsWithScopes(
                google.auth.credentials.Scoped):

            def __init__(self, scopes=(), source=None):
                self._scopes = scopes
                self._source = source

            def requires_scopes(self):  # pragma: NO COVER
                return True

            def with_scopes(self, scopes):
                return self.__class__(scopes, self)

        expected_scopes = (SPANNER_DATA_SCOPE,)
        client = _Client()
        credentials = client.credentials = _CredentialsWithScopes()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        patch = mock.patch('google.cloud.spanner_v1.database.SpannerClient')

        with patch as spanner_client:
            api = database.spanner_api

        self.assertIs(api, spanner_client.return_value)

        # API instance is cached
        again = database.spanner_api
        self.assertIs(again, api)

        self.assertEqual(len(spanner_client.call_args_list), 1)
        called_args, called_kw = spanner_client.call_args
        self.assertEqual(called_args, ())
        self.assertEqual(called_kw['lib_name'], 'gccl')
        self.assertEqual(called_kw['lib_version'], __version__)
        scoped = called_kw['credentials']
        self.assertEqual(scoped._scopes, expected_scopes)
        self.assertIs(scoped._source, credentials)

    def test___eq__(self):
        instance = _Instance(self.INSTANCE_NAME)
        pool1, pool2 = _Pool(), _Pool()
        database1 = self._make_one(self.DATABASE_ID, instance, pool=pool1)
        database2 = self._make_one(self.DATABASE_ID, instance, pool=pool2)
        self.assertEqual(database1, database2)

    def test___eq__type_differ(self):
        pool = _Pool()
        database1 = self._make_one(self.DATABASE_ID, None, pool=pool)
        database2 = object()
        self.assertNotEqual(database1, database2)

    def test___ne__same_value(self):
        instance = _Instance(self.INSTANCE_NAME)
        pool1, pool2 = _Pool(), _Pool()
        database1 = self._make_one(self.DATABASE_ID, instance, pool=pool1)
        database2 = self._make_one(self.DATABASE_ID, instance, pool=pool2)
        comparison_val = (database1 != database2)
        self.assertFalse(comparison_val)

    def test___ne__(self):
        pool1, pool2 = _Pool(), _Pool()
        database1 = self._make_one('database_id1', 'instance1', pool=pool1)
        database2 = self._make_one('database_id2', 'instance2', pool=pool2)
        self.assertNotEqual(database1, database2)

    def test_create_grpc_error(self):
        from google.api_core.exceptions import GoogleAPICallError

        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _rpc_error=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(GoogleAPICallError):
            database.create()

        (parent, create_statement, extra_statements,
         metadata) = api._created_database
        self.assertEqual(parent, self.INSTANCE_NAME)
        self.assertEqual(create_statement,
                         'CREATE DATABASE %s' % self.DATABASE_ID)
        self.assertEqual(extra_statements, [])
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_create_already_exists(self):
        from google.cloud.exceptions import Conflict

        DATABASE_ID_HYPHEN = 'database-id'
        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _create_database_conflict=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(DATABASE_ID_HYPHEN, instance, pool=pool)

        with self.assertRaises(Conflict):
            database.create()

        (parent, create_statement, extra_statements,
         metadata) = api._created_database
        self.assertEqual(parent, self.INSTANCE_NAME)
        self.assertEqual(create_statement,
                         'CREATE DATABASE `%s`' % DATABASE_ID_HYPHEN)
        self.assertEqual(extra_statements, [])
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_create_instance_not_found(self):
        from google.cloud.exceptions import NotFound

        DATABASE_ID_HYPHEN = 'database-id'
        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _database_not_found=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(DATABASE_ID_HYPHEN, instance, pool=pool)

        with self.assertRaises(NotFound):
            database.create()

        (parent, create_statement, extra_statements,
         metadata) = api._created_database
        self.assertEqual(parent, self.INSTANCE_NAME)
        self.assertEqual(create_statement,
                         'CREATE DATABASE `%s`' % DATABASE_ID_HYPHEN)
        self.assertEqual(extra_statements, [])
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_create_success(self):
        from tests._fixtures import DDL_STATEMENTS

        op_future = _FauxOperationFuture()
        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _create_database_response=op_future)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(
            self.DATABASE_ID, instance, ddl_statements=DDL_STATEMENTS,
            pool=pool)

        future = database.create()

        self.assertIs(future, op_future)

        (parent, create_statement, extra_statements,
         metadata) = api._created_database
        self.assertEqual(parent, self.INSTANCE_NAME)
        self.assertEqual(create_statement,
                         'CREATE DATABASE %s' % self.DATABASE_ID)
        self.assertEqual(extra_statements, DDL_STATEMENTS)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_exists_grpc_error(self):
        from google.api_core.exceptions import Unknown

        client = _Client()
        client.database_admin_api = _FauxDatabaseAdminAPI(
            _rpc_error=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(Unknown):
            database.exists()

    def test_exists_not_found(self):
        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _database_not_found=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        self.assertFalse(database.exists())

        name, metadata = api._got_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_exists_success(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)
        from tests._fixtures import DDL_STATEMENTS

        client = _Client()
        ddl_pb = admin_v1_pb2.GetDatabaseDdlResponse(
            statements=DDL_STATEMENTS)
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _get_database_ddl_response=ddl_pb)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        self.assertTrue(database.exists())

        name, metadata = api._got_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_reload_grpc_error(self):
        from google.api_core.exceptions import Unknown

        client = _Client()
        client.database_admin_api = _FauxDatabaseAdminAPI(
            _rpc_error=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(Unknown):
            database.reload()

    def test_reload_not_found(self):
        from google.cloud.exceptions import NotFound

        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _database_not_found=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(NotFound):
            database.reload()

        name, metadata = api._got_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_reload_success(self):
        from google.cloud.spanner_admin_database_v1.proto import (
            spanner_database_admin_pb2 as admin_v1_pb2)
        from tests._fixtures import DDL_STATEMENTS

        client = _Client()
        ddl_pb = admin_v1_pb2.GetDatabaseDdlResponse(
            statements=DDL_STATEMENTS)
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _get_database_ddl_response=ddl_pb)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        database.reload()

        self.assertEqual(database._ddl_statements, tuple(DDL_STATEMENTS))

        name, metadata = api._got_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_update_ddl_grpc_error(self):
        from google.api_core.exceptions import Unknown
        from tests._fixtures import DDL_STATEMENTS

        client = _Client()
        client.database_admin_api = _FauxDatabaseAdminAPI(
            _rpc_error=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(Unknown):
            database.update_ddl(DDL_STATEMENTS)

    def test_update_ddl_not_found(self):
        from google.cloud.exceptions import NotFound
        from tests._fixtures import DDL_STATEMENTS

        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _database_not_found=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(NotFound):
            database.update_ddl(DDL_STATEMENTS)

        name, statements, op_id, metadata = api._updated_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(statements, DDL_STATEMENTS)
        self.assertEqual(op_id, '')
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_update_ddl(self):
        from tests._fixtures import DDL_STATEMENTS

        op_future = _FauxOperationFuture()
        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _update_database_ddl_response=op_future)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        future = database.update_ddl(DDL_STATEMENTS)

        self.assertIs(future, op_future)

        name, statements, op_id, metadata = api._updated_database_ddl
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(statements, DDL_STATEMENTS)
        self.assertEqual(op_id, '')
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_drop_grpc_error(self):
        from google.api_core.exceptions import Unknown

        client = _Client()
        client.database_admin_api = _FauxDatabaseAdminAPI(
            _rpc_error=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(Unknown):
            database.drop()

    def test_drop_not_found(self):
        from google.cloud.exceptions import NotFound

        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _database_not_found=True)
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        with self.assertRaises(NotFound):
            database.drop()

        name, metadata = api._dropped_database
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_drop_success(self):
        from google.protobuf.empty_pb2 import Empty

        client = _Client()
        api = client.database_admin_api = _FauxDatabaseAdminAPI(
            _drop_database_response=Empty())
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        database.drop()

        name, metadata = api._dropped_database
        self.assertEqual(name, self.DATABASE_NAME)
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_session_factory(self):
        from google.cloud.spanner_v1.session import Session

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        session = database.session()

        self.assertTrue(isinstance(session, Session))
        self.assertIs(session.session_id, None)
        self.assertIs(session._database, database)

    def test_snapshot_defaults(self):
        from google.cloud.spanner_v1.database import SnapshotCheckout

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        session = _Session()
        pool.put(session)
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        checkout = database.snapshot()
        self.assertIsInstance(checkout, SnapshotCheckout)
        self.assertIs(checkout._database, database)
        self.assertEqual(checkout._kw, {})

    def test_snapshot_w_read_timestamp_and_multi_use(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud.spanner_v1.database import SnapshotCheckout

        now = datetime.datetime.utcnow().replace(tzinfo=UTC)
        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        session = _Session()
        pool.put(session)
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        checkout = database.snapshot(read_timestamp=now, multi_use=True)

        self.assertIsInstance(checkout, SnapshotCheckout)
        self.assertIs(checkout._database, database)
        self.assertEqual(
            checkout._kw, {'read_timestamp': now, 'multi_use': True})

    def test_batch(self):
        from google.cloud.spanner_v1.database import BatchCheckout

        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        session = _Session()
        pool.put(session)
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        checkout = database.batch()
        self.assertIsInstance(checkout, BatchCheckout)
        self.assertIs(checkout._database, database)

    def test_run_in_transaction_wo_args(self):
        import datetime

        NOW = datetime.datetime.now()
        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        session = _Session()
        pool.put(session)
        session._committed = NOW
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        _unit_of_work = object()

        committed = database.run_in_transaction(_unit_of_work)

        self.assertEqual(committed, NOW)
        self.assertEqual(session._retried, (_unit_of_work, (), {}))

    def test_run_in_transaction_w_args(self):
        import datetime

        SINCE = datetime.datetime(2017, 1, 1)
        UNTIL = datetime.datetime(2018, 1, 1)
        NOW = datetime.datetime.now()
        client = _Client()
        instance = _Instance(self.INSTANCE_NAME, client=client)
        pool = _Pool()
        session = _Session()
        pool.put(session)
        session._committed = NOW
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        _unit_of_work = object()

        committed = database.run_in_transaction(
            _unit_of_work, SINCE, until=UNTIL)

        self.assertEqual(committed, NOW)
        self.assertEqual(session._retried,
                         (_unit_of_work, (SINCE,), {'until': UNTIL}))

    def test_run_in_transaction_nested(self):
        from datetime import datetime

        # Perform the various setup tasks.
        instance = _Instance(self.INSTANCE_NAME, client=_Client())
        pool = _Pool()
        session = _Session(run_transaction_function=True)
        session._committed = datetime.now()
        pool.put(session)
        database = self._make_one(self.DATABASE_ID, instance, pool=pool)

        # Define the inner function.
        inner = mock.Mock(spec=())

        # Define the nested transaction.
        def nested_unit_of_work():
            return database.run_in_transaction(inner)

        # Attempting to run this transaction should raise RuntimeError.
        with self.assertRaises(RuntimeError):
            database.run_in_transaction(nested_unit_of_work)
        self.assertEqual(inner.call_count, 0)


class TestBatchCheckout(_BaseTest):

    def _getTargetClass(self):
        from google.cloud.spanner_v1.database import BatchCheckout

        return BatchCheckout

    def test_ctor(self):
        database = _Database(self.DATABASE_NAME)
        checkout = self._make_one(database)
        self.assertIs(checkout._database, database)

    def test_context_mgr_success(self):
        import datetime
        from google.cloud.spanner_v1.proto.spanner_pb2 import CommitResponse
        from google.cloud.spanner_v1.proto.transaction_pb2 import (
            TransactionOptions)
        from google.cloud._helpers import UTC
        from google.cloud._helpers import _datetime_to_pb_timestamp
        from google.cloud.spanner_v1.batch import Batch

        now = datetime.datetime.utcnow().replace(tzinfo=UTC)
        now_pb = _datetime_to_pb_timestamp(now)
        response = CommitResponse(commit_timestamp=now_pb)
        database = _Database(self.DATABASE_NAME)
        api = database.spanner_api = _FauxSpannerClient()
        api._commit_response = response
        pool = database._pool = _Pool()
        session = _Session(database)
        pool.put(session)
        checkout = self._make_one(database)

        with checkout as batch:
            self.assertIsNone(pool._session)
            self.assertIsInstance(batch, Batch)
            self.assertIs(batch._session, session)

        self.assertIs(pool._session, session)
        self.assertEqual(batch.committed, now)
        (session_name, mutations, single_use_txn,
         metadata) = api._committed
        self.assertIs(session_name, self.SESSION_NAME)
        self.assertEqual(mutations, [])
        self.assertIsInstance(single_use_txn, TransactionOptions)
        self.assertTrue(single_use_txn.HasField('read_write'))
        self.assertEqual(
            metadata, [('google-cloud-resource-prefix', database.name)])

    def test_context_mgr_failure(self):
        from google.cloud.spanner_v1.batch import Batch

        database = _Database(self.DATABASE_NAME)
        pool = database._pool = _Pool()
        session = _Session(database)
        pool.put(session)
        checkout = self._make_one(database)

        class Testing(Exception):
            pass

        with self.assertRaises(Testing):
            with checkout as batch:
                self.assertIsNone(pool._session)
                self.assertIsInstance(batch, Batch)
                self.assertIs(batch._session, session)
                raise Testing()

        self.assertIs(pool._session, session)
        self.assertIsNone(batch.committed)


class TestSnapshotCheckout(_BaseTest):

    def _getTargetClass(self):
        from google.cloud.spanner_v1.database import SnapshotCheckout

        return SnapshotCheckout

    def test_ctor_defaults(self):
        from google.cloud.spanner_v1.snapshot import Snapshot

        database = _Database(self.DATABASE_NAME)
        session = _Session(database)
        pool = database._pool = _Pool()
        pool.put(session)

        checkout = self._make_one(database)
        self.assertIs(checkout._database, database)
        self.assertEqual(checkout._kw, {})

        with checkout as snapshot:
            self.assertIsNone(pool._session)
            self.assertIsInstance(snapshot, Snapshot)
            self.assertIs(snapshot._session, session)
            self.assertTrue(snapshot._strong)
            self.assertFalse(snapshot._multi_use)

        self.assertIs(pool._session, session)

    def test_ctor_w_read_timestamp_and_multi_use(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud.spanner_v1.snapshot import Snapshot

        now = datetime.datetime.utcnow().replace(tzinfo=UTC)
        database = _Database(self.DATABASE_NAME)
        session = _Session(database)
        pool = database._pool = _Pool()
        pool.put(session)

        checkout = self._make_one(database, read_timestamp=now, multi_use=True)
        self.assertIs(checkout._database, database)
        self.assertEqual(checkout._kw,
                         {'read_timestamp': now, 'multi_use': True})

        with checkout as snapshot:
            self.assertIsNone(pool._session)
            self.assertIsInstance(snapshot, Snapshot)
            self.assertIs(snapshot._session, session)
            self.assertEqual(snapshot._read_timestamp, now)
            self.assertTrue(snapshot._multi_use)

        self.assertIs(pool._session, session)

    def test_context_mgr_failure(self):
        from google.cloud.spanner_v1.snapshot import Snapshot

        database = _Database(self.DATABASE_NAME)
        pool = database._pool = _Pool()
        session = _Session(database)
        pool.put(session)
        checkout = self._make_one(database)

        class Testing(Exception):
            pass

        with self.assertRaises(Testing):
            with checkout as snapshot:
                self.assertIsNone(pool._session)
                self.assertIsInstance(snapshot, Snapshot)
                self.assertIs(snapshot._session, session)
                raise Testing()

        self.assertIs(pool._session, session)


class _Client(object):

    def __init__(self, project=TestDatabase.PROJECT_ID):
        self.project = project
        self.project_name = 'projects/' + self.project


class _Instance(object):

    def __init__(self, name, client=None):
        self.name = name
        self.instance_id = name.rsplit('/', 1)[1]
        self._client = client


class _Database(object):

    def __init__(self, name, instance=None):
        self.name = name
        self.database_id = name.rsplit('/', 1)[1]
        self._instance = instance


class _Pool(object):
    _bound = None

    def bind(self, database):
        self._bound = database

    def get(self):
        session, self._session = self._session, None
        return session

    def put(self, session):
        self._session = session


class _Session(object):

    _rows = ()

    def __init__(self, database=None, name=_BaseTest.SESSION_NAME,
                 run_transaction_function=False):
        self._database = database
        self.name = name
        self._run_transaction_function = run_transaction_function

    def run_in_transaction(self, func, *args, **kw):
        if self._run_transaction_function:
            func(*args, **kw)
        self._retried = (func, args, kw)
        return self._committed


class _SessionPB(object):
    name = TestDatabase.SESSION_NAME


class _FauxOperationFuture(object):
    pass


class _FauxSpannerClient(object):

    _committed = None

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def commit(self, session, mutations,
               transaction_id='', single_use_transaction=None, metadata=None):
        assert transaction_id == ''
        self._committed = (
            session, mutations, single_use_transaction, metadata)
        return self._commit_response


class _FauxDatabaseAdminAPI(object):

    _create_database_conflict = False
    _database_not_found = False
    _rpc_error = False

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def create_database(self, parent, create_statement, extra_statements=None,
                        metadata=None):
        from google.api_core.exceptions import AlreadyExists, NotFound, Unknown

        self._created_database = (
            parent, create_statement, extra_statements, metadata)
        if self._rpc_error:
            raise Unknown('error')
        if self._create_database_conflict:
            raise AlreadyExists('conflict')
        if self._database_not_found:
            raise NotFound('not found')
        return self._create_database_response

    def get_database_ddl(self, database, metadata=None):
        from google.api_core.exceptions import NotFound, Unknown

        self._got_database_ddl = database, metadata
        if self._rpc_error:
            raise Unknown('error')
        if self._database_not_found:
            raise NotFound('not found')
        return self._get_database_ddl_response

    def drop_database(self, database, metadata=None):
        from google.api_core.exceptions import NotFound, Unknown

        self._dropped_database = database, metadata
        if self._rpc_error:
            raise Unknown('error')
        if self._database_not_found:
            raise NotFound('not found')
        return self._drop_database_response

    def update_database_ddl(self, database, statements, operation_id,
                            metadata=None):
        from google.api_core.exceptions import NotFound, Unknown

        self._updated_database_ddl = (
            database, statements, operation_id, metadata)
        if self._rpc_error:
            raise Unknown('error')
        if self._database_not_found:
            raise NotFound('not found')
        return self._update_database_ddl_response
