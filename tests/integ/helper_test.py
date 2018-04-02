##############################################################################
# Copyright by The HDF Group.                                                #
# All rights reserved.                                                       #
#                                                                            #
# This file is part of HSDS (HDF5 Scalable Data Service), Libraries and      #
# Utilities.  The full HSDS copyright notice, including                      #
# terms governing use, modification, and redistribution, is contained in     #
# the file COPYING, which can be found at the root of the source code        #
# distribution tree.  If you do not have access to this file, you may        #
# request a copy from help@hdfgroup.org.                                     #
##############################################################################
"""Quality-assurance for helper module."""
import unittest
import requests
import helper

class TestGetDNSDomain(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(helper.getDNSDomain(""), "")

    def test_root(self):
        self.assertEqual(helper.getDNSDomain("/"), "")

    def test_None(self):
        with self.assertRaises(AttributeError):
            helper.getDNSDomain(None)

    def test_nominal(self):
        self.assertEqual(
                helper.getDNSDomain("/path/to/a/file"),
                "file.a.to.path")

class GetUUIDByPathTest(unittest.TestCase):
    def setUp(self):
        """Set up the test domain as follows...

        /
        /g1/dset10
        /g2/g21/dset210
        /dset0
        /dset210_soft   (soft link to /g2/g21/dset210)
        """
        self.base_domain = helper.getTestDomainName(self.__class__.__name__)
        helper.setupDomain(self.base_domain)
        headers = helper.getRequestHeaders(domain=self.base_domain)
        endpoint = helper.getEndpoint()
        groups_endpt = endpoint + "/groups"
        dsets_endpt = endpoint + "/datasets"
        dset_payload = '{ "type": "H5T_STD_U32LE", "shape": [8] }'

        # create all groups and datasets
        rootid = helper.getRootUUID(self.base_domain)
        g1id = requests.post(groups_endpt, headers=headers).json()["id"]
        g2id = requests.post(groups_endpt, headers=headers).json()["id"]
        g21id = requests.post(groups_endpt, headers=headers).json()["id"]
        d0id = requests.post(
                dsets_endpt, headers=headers, data=dset_payload).json()["id"]
        d10id = requests.post(
                dsets_endpt, headers=headers, data=dset_payload).json()["id"]
        d210id = requests.post(
                dsets_endpt, headers=headers, data=dset_payload).json()["id"]

        # link objects into tree
        assert requests.put(
                f"{groups_endpt}/{rootid}/links/g1", 
                data=f'{{"id": "{g1id}"}}', # {"id": "<some_id>"}
                headers=headers
        ).status_code == 201, "unable to link `/g1`"
        assert requests.put(
                f"{groups_endpt}/{rootid}/links/g2", 
                data=f'{{"id": "{g2id}"}}',
                headers=headers
        ).status_code == 201, "unable to link `/g2`"
        assert requests.put(
                f"{groups_endpt}/{g2id}/links/g21", 
                data=f'{{"id": "{g21id}"}}',
                headers=headers
        ).status_code == 201, "unable to link `/g2/g21`"
        assert requests.put(
                f"{groups_endpt}/{rootid}/links/dset0", 
                data=f'{{"id": "{d0id}"}}',
                headers=headers
        ).status_code == 201, "unable to link `/dset0`"
        assert requests.put(
                f"{groups_endpt}/{g1id}/links/dset10", 
                data=f'{{"id": "{d10id}"}}',
                headers=headers
        ).status_code == 201, "unable to link `/g1/dset0`"
        assert requests.put(
                f"{groups_endpt}/{g21id}/links/dset210", 
                data=f'{{"id": "{d210id}"}}',
                headers=headers
        ).status_code == 201, "unable to link `/g2/g21/dset0`"
        assert requests.put(
                f"{groups_endpt}/{rootid}/links/dset210_soft", 
                data=f'{{"h5path": "/g2/g21/dset210"}}',
                headers=headers
        ).status_code == 201, "unable to link `/dset210_soft`"

        # remember ids for tests
        self.root = rootid
        self.g1 = g1id
        self.g2 = g2id
        self.g21 = g21id
        self.d0 = d0id
        self.d10 = d10id
        self.d210 = d210id

    def test_on_provided_domain(self):
        # Do most or all of the tests in one function because of the overhead
        # of creating the tree... 1-3 seconds per setup is _huge_.

        self.assertEqual(
                helper.getUUIDByPath(self.base_domain, "/"),
                self.root,
                "root group")

        self.assertEqual(
                helper.getUUIDByPath(self.base_domain, "/g1"),
                self.g1,
                "group linked from root")

        self.assertEqual(
                helper.getUUIDByPath(self.base_domain, "/dset0"),
                self.d0,
                "dataset linked from root")

        self.assertEqual(
                helper.getUUIDByPath(self.base_domain, "/g2/g21"),
                self.g21,
                "group linked away from root")

        self.assertEqual(
                helper.getUUIDByPath(self.base_domain, "/g2/g21/dset210"),
                self.d210,
                "dataset linked away from root")

        # softlink to dataset from root (not allowed)
        with self.assertRaises(KeyError):
            helper.getUUIDByPath(self.base_domain, "/dset210_soft")

        # object does not exist at target path
        with self.assertRaises(KeyError):
            helper.getUUIDByPath(self.base_domain, "/nonexistent/thing")

        # object does not exist at target path (partially viable)
        with self.assertRaises(KeyError):
            helper.getUUIDByPath(self.base_domain, "/g1/dset_gone")

        # path must begin with a slash
        with self.assertRaises(KeyError):
            helper.getUUIDByPath(self.base_domain, "g2/g21")

        # TODO: link dataset to dataset?

if __name__ == "__main__":
    unittest.main()


