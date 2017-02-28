# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import json  # noqa: F401
import time
import requests

from os import environ
try:
    from ConfigParser import ConfigParser  # py2
except:
    from configparser import ConfigParser  # py3

from pprint import pprint  # noqa: F401

from biokbase.workspace.client import Workspace as workspaceService
from CoreServicesIntegrationTests.CoreServicesIntegrationTestsImpl import CoreServicesIntegrationTests
from CoreServicesIntegrationTests.CoreServicesIntegrationTestsServer import MethodContext
from CoreServicesIntegrationTests.authclient import KBaseAuth as _KBaseAuth
from DataFileUtil.DataFileUtilClient import DataFileUtil


class CoreServicesIntegrationTestsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('CoreServicesIntegrationTests'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'CoreServicesIntegrationTests',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = CoreServicesIntegrationTests(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        if hasattr(self.__class__, 'wsName'):
            return self.__class__.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_CoreServicesIntegrationTests_" + str(suffix)
        ret = self.getWsClient().create_workspace({'workspace': wsName})  # noqa
        self.__class__.wsName = wsName
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_shock_handle_ws(self):
        test_phrase = "Hi there!"
        path_to_temp_file = "/kb/module/work/tmp/temp_" + str(time.time()) + ".fq"
        with open(path_to_temp_file, 'w') as f:
            f.write(test_phrase)
        dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'],
                           token=self.ctx['token'])
        uploaded = dfu.file_to_shock({'file_path': path_to_temp_file,
                                      'make_handle': 1})
        fhandle = uploaded['handle']
        self.assertTrue('hid' in fhandle, "Handle: " + str(fhandle))
        data = {'hid': fhandle['hid']}
        obj_name = 'TestObject.1'
        info = self.getWsClient().save_objects({'workspace': self.getWsName(),
                                                'objects': [{'type': 'Empty.AHandle',
                                                             'data': data,
                                                             'name': obj_name
                                                            }]})[0]
        self.assertEqual(info[1], obj_name)
        ref = self.getWsName() + '/' + obj_name
        handle_data = self.getWsClient().get_objects([{'ref': ref}])[0]['data']
        self.assertTrue('hid' in handle_data, "Data: " + str(handle_data))
        hid = handle_data['hid']
        path_to_temp_file2 = "/kb/module/work/tmp/temp2_" + str(time.time()) + ".fq"
        dfu.shock_to_file({'handle_id': hid, 'file_path': path_to_temp_file2})
        phrase2 = ""
        with open(path_to_temp_file2, 'r') as f:
            phrase2 = f.read()
        self.assertEqual(test_phrase, phrase2)
