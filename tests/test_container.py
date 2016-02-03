﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import requests
from datetime import datetime, timedelta
from azure.common import (
    AzureHttpError,
    AzureConflictHttpError,
    AzureMissingResourceHttpError,
)
from azure.storage import (
    AccessPolicy,
)
from azure.storage.blob import (
    BlockBlobService,
    ContainerPermissions,
    Include,
)
from tests.testcase import (
    StorageTestCase,
    TestMode,
    record,
)

#------------------------------------------------------------------------------
TEST_CONTAINER_PREFIX = 'container'
#------------------------------------------------------------------------------

class StorageContainerTest(StorageTestCase):

    def setUp(self):
        super(StorageContainerTest, self).setUp()

        self.bs = self._create_storage_service(BlockBlobService, self.settings)
        self.test_containers = []

    def tearDown(self):
        if not self.is_playback():
            for container_name in self.test_containers:
                try:
                    self.bs.delete_container(container_name)
                except AzureHttpError:
                    try: 
                        self.bs.break_container_lease(container_name, 0)
                        self.bs.delete_container(container_name)
                    except:
                        pass
                except:
                    pass
        return super(StorageContainerTest, self).tearDown()

    #--Helpers-----------------------------------------------------------------
    def _get_container_reference(self, prefix=TEST_CONTAINER_PREFIX):
        container_name = self.get_resource_name(prefix)
        self.test_containers.append(container_name)
        return container_name

    def _create_container(self, prefix=TEST_CONTAINER_PREFIX):
        container_name = self._get_container_reference(prefix)
        self.bs.create_container(container_name)
        return container_name

    #--Test cases for containers -----------------------------------------
    @record
    def test_create_container(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created = self.bs.create_container(container_name)

        # Assert
        self.assertTrue(created)

    @record
    def test_create_container_fail_on_exist(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created = self.bs.create_container(container_name, None, None, True)

        # Assert
        self.assertTrue(created)

    @record
    def test_create_container_with_already_existing_container(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created1 = self.bs.create_container(container_name)
        created2 = self.bs.create_container(container_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    @record
    def test_create_container_with_already_existing_container_fail_on_exist(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created = self.bs.create_container(container_name)
        with self.assertRaises(AzureConflictHttpError):
            self.bs.create_container(container_name, None, None, True)

        # Assert
        self.assertTrue(created)

    @record
    def test_create_container_with_public_access_container(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created = self.bs.create_container(container_name, None, 'container')
        anonymous_service = BlockBlobService(self.settings.STORAGE_ACCOUNT_NAME)

        # Assert
        self.assertTrue(created)
        anonymous_service.list_blobs(container_name)

    @record
    def test_create_container_with_public_access_blob(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        created = self.bs.create_container(container_name, None, 'blob')
        self.bs.create_blob_from_text(container_name, 'blob1', u'xyz')
        anonymous_service = BlockBlobService(self.settings.STORAGE_ACCOUNT_NAME)

        # Assert
        self.assertTrue(created)
        anonymous_service.get_blob_to_text(container_name, 'blob1')

    @record
    def test_create_container_with_metadata(self):
        # Arrange
        container_name = self._get_container_reference()
        metadata = {'hello': 'world', 'number': '42'}

        # Act
        created = self.bs.create_container(container_name, metadata)

        # Assert
        self.assertTrue(created)
        md = self.bs.get_container_metadata(container_name)
        self.assertDictEqual(md, metadata)

    @record
    def test_container_exists(self):
        # Arrange
        container_name = self._create_container()

        # Act
        exists = self.bs.exists(container_name)

        # Assert
        self.assertTrue(exists)

    @record
    def test_container_not_exists(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        exists = self.bs.exists(container_name)

        # Assert
        self.assertFalse(exists)

    @record
    def test_container_exists_with_lease(self):
        # Arrange
        container_name = self._create_container()
        self.bs.acquire_container_lease(container_name)

        # Act
        exists = self.bs.exists(container_name)

        # Assert
        self.assertTrue(exists)

    @record
    def test_unicode_create_container_unicode_name(self):
        # Arrange
        container_name = u'啊齄丂狛狜'

        # Act
        with self.assertRaises(AzureHttpError):
            # not supported - container name must be alphanumeric, lowercase
            self.bs.create_container(container_name)

        # Assert

    @record
    def test_list_containers(self):
        # Arrange
        container_name = self._create_container()

        # Act
        containers = list(self.bs.list_containers())

        # Assert
        self.assertIsNotNone(containers)
        self.assertGreaterEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertNamedItemInContainer(containers, container_name)

    @record
    def test_list_containers_with_prefix(self):
        # Arrange
        container_name = self._create_container()

        # Act
        containers = list(self.bs.list_containers(container_name))

        # Assert
        self.assertIsNotNone(containers)
        self.assertEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertEqual(containers[0].name, container_name)
        self.assertIsNone(containers[0].metadata)

    @record
    def test_list_containers_with_include_metadata(self):
        # Arrange
        container_name = self._create_container()
        metadata = {'hello': 'world', 'number': '42'}
        resp = self.bs.set_container_metadata(container_name, metadata)

        # Act
        containers = list(self.bs.list_containers(container_name, include_metadata=True))

        # Assert
        self.assertIsNotNone(containers)
        self.assertGreaterEqual(len(containers), 1)
        self.assertIsNotNone(containers[0])
        self.assertNamedItemInContainer(containers, container_name)
        self.assertDictEqual(containers[0].metadata, metadata)

    @record
    def test_list_containers_with_maxresults_and_marker(self):
        # Arrange
        prefix = 'listcontainer'
        container_names = []
        for i in range(0, 4):
            container_names.append(self._create_container(prefix + str(i)))

        container_names.sort()

        # Act
        generator1 = self.bs.list_containers(prefix, None, 2)
        generator2 = self.bs.list_containers(prefix, generator1.next_marker, 2)

        containers1 = generator1.items
        containers2 = generator2.items

        # Assert
        self.assertIsNotNone(containers1)
        self.assertEqual(len(containers1), 2)
        self.assertNamedItemInContainer(containers1, container_names[0])
        self.assertNamedItemInContainer(containers1, container_names[1])
        self.assertIsNotNone(containers2)
        self.assertEqual(len(containers2), 2)
        self.assertNamedItemInContainer(containers2, container_names[2])
        self.assertNamedItemInContainer(containers2, container_names[3])

    @record
    def test_set_container_metadata(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '43'}
        container_name = self._create_container()

        # Act
        props = self.bs.set_container_metadata(container_name, metadata)

        # Assert
        self.assertIsNotNone(props.etag)
        self.assertIsNotNone(props.last_modified)
        md = self.bs.get_container_metadata(container_name)
        self.assertDictEqual(md, metadata)

    @record
    def test_set_container_metadata_with_lease_id(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '43'}
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(container_name)

        # Act
        self.bs.set_container_metadata(container_name, metadata, lease_id)

        # Assert
        md = self.bs.get_container_metadata(container_name)
        self.assertDictEqual(md, metadata)

    @record
    def test_set_container_metadata_with_non_existing_container(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        with self.assertRaises(AzureHttpError):
            self.bs.set_container_metadata(
                container_name, {'hello': 'world', 'number': '43'})

        # Assert

    @record
    def test_get_container_metadata(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '42'}
        container_name = self._create_container()
        self.bs.set_container_metadata(container_name, metadata)

        # Act
        md = self.bs.get_container_metadata(container_name)

        # Assert
        self.assertDictEqual(md, metadata)

    @record
    def test_get_container_metadata_with_lease_id(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '42'}
        container_name = self._create_container()
        self.bs.set_container_metadata(container_name, metadata)
        lease_id = self.bs.acquire_container_lease(container_name)

        # Act
        md = self.bs.get_container_metadata(container_name, lease_id)

        # Assert
        self.assertDictEqual(md, metadata)

    @record
    def test_get_container_properties(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '42'}
        container_name = self._create_container()
        self.bs.set_container_metadata(container_name, metadata)
        self.bs.acquire_container_lease(container_name)

        # Act
        props = self.bs.get_container_properties(container_name)

        # Assert
        self.assertIsNotNone(props)
        self.assertDictEqual(props.metadata, metadata)
        self.assertEqual(props.properties.lease.duration, 'infinite')
        self.assertEqual(props.properties.lease.state, 'leased')
        self.assertEqual(props.properties.lease.status, 'locked')

    @record
    def test_get_container_properties_with_lease_id(self):
        # Arrange
        metadata = {'hello': 'world', 'number': '42'}
        container_name = self._create_container()
        self.bs.set_container_metadata(container_name, metadata)
        lease_id = self.bs.acquire_container_lease(container_name)

        # Act
        props = self.bs.get_container_properties(container_name, lease_id)
        self.bs.break_container_lease(container_name)

        # Assert
        self.assertIsNotNone(props)
        self.assertDictEqual(props.metadata, metadata)
        self.assertEqual(props.properties.lease.duration, 'infinite')
        self.assertEqual(props.properties.lease.state, 'leased')
        self.assertEqual(props.properties.lease.status, 'locked')

    @record
    def test_get_container_acl(self):
        # Arrange
        container_name = self._create_container()

        # Act
        acl = self.bs.get_container_acl(container_name)

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)
        self.assertIsNone(acl.public_access)

    @record
    def test_get_container_acl_with_lease_id(self):
        # Arrange
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(container_name)

        # Act
        acl = self.bs.get_container_acl(container_name, lease_id)

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)
        self.assertIsNone(acl.public_access)

    @record
    def test_set_container_acl(self):
        # Arrange
        container_name = self._create_container()

        # Act
        self.bs.set_container_acl(container_name)

        # Assert
        acl = self.bs.get_container_acl(container_name)
        self.assertIsNotNone(acl)
        self.assertIsNone(acl.public_access)

    @record
    def test_set_container_acl_with_lease_id(self):
        # Arrange
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(container_name)

        # Act
        self.bs.set_container_acl(container_name, lease_id=lease_id)

        # Assert
        acl = self.bs.get_container_acl(container_name)
        self.assertIsNotNone(acl)
        self.assertIsNone(acl.public_access)

    @record
    def test_set_container_acl_with_public_access(self):
        # Arrange
        container_name = self._create_container()

        # Act
        self.bs.set_container_acl(container_name, None, 'container')

        # Assert
        acl = self.bs.get_container_acl(container_name)
        self.assertIsNotNone(acl)
        self.assertEqual('container', acl.public_access)

    @record
    def test_set_container_acl_with_empty_signed_identifiers(self):
        # Arrange
        container_name = self._create_container()

        # Act
        self.bs.set_container_acl(container_name, dict())

        # Assert
        acl = self.bs.get_container_acl(container_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)
        self.assertIsNone(acl.public_access)


    @record
    def test_set_container_acl_with_signed_identifiers(self):
        # Arrange
        container_name = self._create_container()

        # Act
        identifiers = dict()
        identifiers['testid'] = AccessPolicy(
            permission=ContainerPermissions.READ,
            expiry=datetime.utcnow() + timedelta(hours=1),  
            start=datetime.utcnow() - timedelta(minutes=1),  
            )

        self.bs.set_container_acl(container_name, identifiers)

        # Assert
        acl = self.bs.get_container_acl(container_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 1)
        self.assertTrue('testid' in acl)
        self.assertIsNone(acl.public_access)

    @record
    def test_lease_container_acquire_and_release(self):
        # Arrange
        container_name = self._create_container()

        # Act
        lease_id = self.bs.acquire_container_lease(container_name)
        lease = self.bs.release_container_lease(container_name, lease_id)

        # Assert

    @record
    def test_lease_container_renew(self):
        # Arrange
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(
            container_name, lease_duration=15)
        self.sleep(10)

        # Act
        renewed_lease_id = self.bs.renew_container_lease(
            container_name, lease_id)

        # Assert
        self.assertEqual(lease_id, renewed_lease_id)
        self.sleep(5)
        with self.assertRaises(AzureHttpError):
            self.bs.delete_container(container_name)
        self.sleep(10)
        self.bs.delete_container(container_name)

    @record
    def test_lease_container_break_period(self):
        # Arrange
        container_name = self._create_container()

        # Act
        lease_id = self.bs.acquire_container_lease(
            container_name, lease_duration=15)

        # Assert
        self.bs.break_container_lease(container_name,
                                      lease_break_period=5)
        self.sleep(6)
        with self.assertRaises(AzureHttpError):
            self.bs.delete_container(container_name, lease_id=lease_id)

    @record
    def test_lease_container_break_released_lease_fails(self):
        # Arrange
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(container_name)
        self.bs.release_container_lease(container_name, lease_id)

        # Act
        with self.assertRaises(AzureHttpError):
            self.bs.break_container_lease(container_name)

        # Assert

    @record
    def test_lease_container_with_duration(self):
        # Arrange
        container_name = self._create_container()

        # Act
        lease_id = self.bs.acquire_container_lease(container_name, lease_duration=15)

        # Assert
        with self.assertRaises(AzureHttpError):
            self.bs.acquire_container_lease(container_name)
        self.sleep(15)
        self.bs.acquire_container_lease(container_name)

    @record
    def test_lease_container_with_proposed_lease_id(self):
        # Arrange
        container_name = self._create_container()

        # Act
        proposed_lease_id = '55e97f64-73e8-4390-838d-d9e84a374321'
        lease_id = self.bs.acquire_container_lease(
            container_name, proposed_lease_id=proposed_lease_id)

        # Assert
        self.assertEqual(proposed_lease_id, lease_id)

    @record
    def test_lease_container_change_lease_id(self):
        # Arrange
        container_name = self._create_container()

        # Act
        lease_id = '29e0b239-ecda-4f69-bfa3-95f6af91464c'
        lease_id1 = self.bs.acquire_container_lease(container_name)
        self.bs.change_container_lease(container_name,
                                        lease_id1,
                                        proposed_lease_id=lease_id)
        lease_id2 = self.bs.renew_container_lease(container_name, lease_id)

        # Assert
        self.assertIsNotNone(lease_id1)
        self.assertIsNotNone(lease_id2)
        self.assertNotEqual(lease_id1, lease_id)
        self.assertEqual(lease_id2, lease_id)

    @record
    def test_delete_container_with_existing_container(self):
        # Arrange
        container_name = self._create_container()

        # Act
        deleted = self.bs.delete_container(container_name)

        # Assert
        self.assertTrue(deleted)
        exists = self.bs.exists(container_name)
        self.assertFalse(exists)

    @record
    def test_delete_container_with_existing_container_fail_not_exist(self):
        # Arrange
        container_name = self._create_container()

        # Act
        deleted = self.bs.delete_container(container_name, True)

        # Assert
        self.assertTrue(deleted)
        exists = self.bs.exists(container_name)
        self.assertFalse(exists)

    @record
    def test_delete_container_with_non_existing_container(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        deleted = self.bs.delete_container(container_name)

        # Assert
        self.assertFalse(deleted)

    @record
    def test_delete_container_with_non_existing_container_fail_not_exist(self):
        # Arrange
        container_name = self._get_container_reference()

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.bs.delete_container(container_name, True)

        # Assert

    @record
    def test_delete_container_with_lease_id(self):
        # Arrange
        container_name = self._create_container()
        lease_id = self.bs.acquire_container_lease(container_name, lease_duration=15)

        # Act
        deleted = self.bs.delete_container(container_name, lease_id=lease_id)

        # Assert
        self.assertTrue(deleted)
        exists = self.bs.exists(container_name)
        self.assertFalse(exists)

    @record
    def test_list_blobs(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data, )
        self.bs.create_blob_from_bytes (container_name, 'blob2', data, )

        # Act
        blobs = list(self.bs.list_blobs(container_name))

        # Assert
        self.assertIsNotNone(blobs)
        self.assertGreaterEqual(len(blobs), 2)
        self.assertIsNotNone(blobs[0])
        self.assertNamedItemInContainer(blobs, 'blob1')
        self.assertNamedItemInContainer(blobs, 'blob2')
        self.assertEqual(blobs[0].properties.content_length, 11)
        self.assertEqual(blobs[1].properties.content_type,
                         'application/octet-stream')

    @record
    def test_list_blobs_leased_blob(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data, )
        lease = self.bs.acquire_blob_lease(container_name, 'blob1')

        # Act
        resp = list(self.bs.list_blobs(container_name))

        # Assert
        self.assertIsNotNone(resp)
        self.assertGreaterEqual(len(resp), 1)
        self.assertIsNotNone(resp[0])
        self.assertNamedItemInContainer(resp, 'blob1')
        self.assertEqual(resp[0].properties.content_length, 11)
        self.assertEqual(resp[0].properties.lease_duration, 'infinite')
        self.assertEqual(resp[0].properties.lease_status, 'locked')
        self.assertEqual(resp[0].properties.lease_state, 'leased')

    @record
    def test_list_blobs_with_prefix(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'bloba1', data, )
        self.bs.create_blob_from_bytes (container_name, 'bloba2', data, )
        self.bs.create_blob_from_bytes (container_name, 'blobb1', data, )

        # Act
        resp = list(self.bs.list_blobs(container_name, 'bloba'))

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(len(resp), 2)
        self.assertNamedItemInContainer(resp, 'bloba1')
        self.assertNamedItemInContainer(resp, 'bloba2')

    @record
    def test_list_blobs_with_max_results(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'bloba1', data, )
        self.bs.create_blob_from_bytes (container_name, 'bloba2', data, )
        self.bs.create_blob_from_bytes (container_name, 'bloba3', data, )
        self.bs.create_blob_from_bytes (container_name, 'blobb1', data, )

        # Act
        blobs = list(self.bs.list_blobs(container_name, max_results=2))

        # Assert
        self.assertIsNotNone(blobs)
        self.assertEqual(len(blobs), 2)
        self.assertNamedItemInContainer(blobs, 'bloba1')
        self.assertNamedItemInContainer(blobs, 'bloba2')

    @record
    def test_list_blobs_with_include_snapshots(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data, )
        self.bs.create_blob_from_bytes (container_name, 'blob2', data, )
        self.bs.snapshot_blob(container_name, 'blob1')

        # Act
        blobs = list(self.bs.list_blobs(container_name, include=Include.SNAPSHOTS))

        # Assert
        self.assertEqual(len(blobs), 3)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertIsNotNone(blobs[0].snapshot)
        self.assertEqual(blobs[1].name, 'blob1')
        self.assertIsNone(blobs[1].snapshot)
        self.assertEqual(blobs[2].name, 'blob2')
        self.assertIsNone(blobs[2].snapshot)

    @record
    def test_list_blobs_with_include_metadata(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data,
                         metadata={'number': '1', 'name': 'bob'})
        self.bs.create_blob_from_bytes (container_name, 'blob2', data,
                         metadata={'number': '2', 'name': 'car'})
        self.bs.snapshot_blob(container_name, 'blob1')

        # Act
        blobs =list(self.bs.list_blobs(container_name, include=Include.METADATA))

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[0].metadata['number'], '1')
        self.assertEqual(blobs[0].metadata['name'], 'bob')
        self.assertEqual(blobs[1].name, 'blob2')
        self.assertEqual(blobs[1].metadata['number'], '2')
        self.assertEqual(blobs[1].metadata['name'], 'car')

    @record
    def test_list_blobs_with_include_uncommittedblobs(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.put_block(container_name, 'blob1', b'AAA', '1')
        self.bs.put_block(container_name, 'blob1', b'BBB', '2')
        self.bs.put_block(container_name, 'blob1', b'CCC', '3')
        self.bs.create_blob_from_bytes (container_name, 'blob2', data,
                         metadata={'number': '2', 'name': 'car'})

        # Act
        blobs = list(self.bs.list_blobs(container_name, include=Include.UNCOMMITTED_BLOBS))

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[1].name, 'blob2')

    @record
    def test_list_blobs_with_include_copy(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data,
                         metadata={'status': 'original'})
        sourceblob = 'https://{0}.blob.core.windows.net/{1}/{2}'.format(
            self.settings.STORAGE_ACCOUNT_NAME,
            container_name,
            'blob1')
        self.bs.copy_blob(container_name, 'blob1copy',
                          sourceblob, {'status': 'copy'})

        # Act
        blobs = list(self.bs.list_blobs(container_name, include=Include.COPY))

        # Assert
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertEqual(blobs[1].name, 'blob1copy')
        self.assertEqual(blobs[1].properties.content_length, 11)
        self.assertEqual(blobs[1].properties.content_type,
                         'application/octet-stream')
        self.assertEqual(blobs[1].properties.content_encoding, None)
        self.assertEqual(blobs[1].properties.content_language, None)
        self.assertNotEqual(blobs[1].properties.content_md5, None)
        self.assertEqual(blobs[1].properties.blob_type, self.bs.blob_type)
        self.assertEqual(blobs[1].properties.lease_status, 'unlocked')
        self.assertEqual(blobs[1].properties.lease_state, 'available')
        self.assertNotEqual(blobs[1].properties.copy_id, None)
        self.assertEqual(blobs[1].properties.copy_source, sourceblob)
        self.assertEqual(blobs[1].properties.copy_status, 'success')
        self.assertEqual(blobs[1].properties.copy_progress, '11/11')
        self.assertNotEqual(blobs[1].properties.copy_completion_time, None)

    @record
    def test_list_blobs_with_delimiter(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'a/blob1', data, )
        self.bs.create_blob_from_bytes (container_name, 'a/blob2', data, )
        self.bs.create_blob_from_bytes (container_name, 'b/blob1', data, )
        self.bs.create_blob_from_bytes (container_name, 'blob1', data, )

        # Act
        resp = list(self.bs.list_blobs(container_name, delimiter='/'))

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(len(resp), 3)
        self.assertNamedItemInContainer(resp, 'a/')
        self.assertNamedItemInContainer(resp, 'b/')
        self.assertNamedItemInContainer(resp, 'blob1')

    @record
    def test_list_blobs_with_include_multiple(self):
        # Arrange
        container_name = self._create_container()
        data = b'hello world'
        self.bs.create_blob_from_bytes (container_name, 'blob1', data,
                         metadata={'number': '1', 'name': 'bob'})
        self.bs.create_blob_from_bytes (container_name, 'blob2', data,
                         metadata={'number': '2', 'name': 'car'})
        self.bs.snapshot_blob(container_name, 'blob1')

        # Act
        blobs = list(self.bs.list_blobs(container_name, include=Include(snapshots=True, metadata=True)))

        # Assert
        self.assertEqual(len(blobs), 3)
        self.assertEqual(blobs[0].name, 'blob1')
        self.assertIsNotNone(blobs[0].snapshot)
        self.assertEqual(blobs[0].metadata['number'], '1')
        self.assertEqual(blobs[0].metadata['name'], 'bob')
        self.assertEqual(blobs[1].name, 'blob1')
        self.assertIsNone(blobs[1].snapshot)
        self.assertEqual(blobs[1].metadata['number'], '1')
        self.assertEqual(blobs[1].metadata['name'], 'bob')
        self.assertEqual(blobs[2].name, 'blob2')
        self.assertIsNone(blobs[2].snapshot)
        self.assertEqual(blobs[2].metadata['number'], '2')
        self.assertEqual(blobs[2].metadata['name'], 'car')


    @record
    def test_shared_access_container(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        container_name = self._create_container()
        blob_name  = 'blob1'
        data = b'hello world'

        self.bs.create_blob_from_bytes (container_name, blob_name, data)

        token = self.bs.generate_container_shared_access_signature(
            container_name,
            expiry=datetime.utcnow() + timedelta(hours=1),
            permission=ContainerPermissions.READ,
        )
        url = self.bs.make_blob_url(
            container_name,
            blob_name,
            sas_token=token,
        )

        # Act
        response = requests.get(url)

        # Assert
        self.assertTrue(response.ok)
        self.assertEqual(data, response.content)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
