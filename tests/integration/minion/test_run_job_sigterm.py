# -*- coding: utf-8 -*-
'''
Tests for various minion timeouts
'''

# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import os
import sys
import time
import logging
import shutil
import subprocess
import signal

# Import Salt Testing libs
from tests.support.case import ShellCase
from tests.support.paths import ScriptPathMixin
from tests.support.mixins import AdaptedConfigurationTestCaseMixin
from tests.support.helpers import get_unused_localhost_port

# Import 3rd-party libs
from tests.support.processes import terminate_process

# Import Salt libs
import salt.ext.six as six
from salt.utils.nb_popen import NonBlockingPopen
import salt.utils.platform

log = logging.getLogger(__name__)


class MinionRunJobSigTermTestCase(ShellCase):
    @classmethod
    def setUpClass(cls):
        overrides = {
            'id': 'temp_minion',
            'publish_port': get_unused_localhost_port(),
            'ret_port': get_unused_localhost_port(),
            'tcp_master_pub_port': get_unused_localhost_port(),
            'tcp_master_pull_port': get_unused_localhost_port(),
            'tcp_master_publish_pull': get_unused_localhost_port(),
            'tcp_master_workers': get_unused_localhost_port(),
            'runtests_conn_check_port': get_unused_localhost_port(),
            'runtests_log_port': get_unused_localhost_port()
        }
        overrides['pytest_engine_port'] = overrides['runtests_conn_check_port']
        temp_config = AdaptedConfigurationTestCaseMixin.get_temp_config('minion', **overrides)
        cls.root_dir = temp_config['root_dir']

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root_dir)
        cls.root_dir = None

    def test_error_on_sigterm(self):
        '''
        Test that error is returned when minion receives a SIGTERM.
        '''
        sleep_length = 60

        # Spin up a temporary minion
        temp_minion_proc = NonBlockingPopen(
            [
                self.get_script_path('minion'),
                '-c',
                self.config_dir,
                '-l',
                'info'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        out = six.b('')
        err = six.b('')

        try:
            if salt.utils.platform.is_windows():
                popen_kwargs = {'env': dict(os.environ, PYTHONPATH=';'.join(sys.path))}
            else:
                popen_kwargs = None

            out = temp_minion_proc.recv()
            err = temp_minion_proc.recv_err()

            # Send asynchronous sleep job to minion
            salt_ret = self.run_salt(
                'temp_minion --async test.sleep {0}'.format(sleep_length),
                timeout=30,
                catch_stderr=True,
                popen_kwargs=popen_kwargs,
            )
            print('Sleep for {0} seconds sent to minion with process id {1}'.format(sleep_length, temp_minion_proc.pid))

            result = os.kill(temp_minion_proc.pid, signal.SIGTERM)
            print('SIGTERM sent, process pid {0} terminated. Result: {1}.'.format(temp_minion_proc.pid, result))

            # Error should be thrown
            self.assertNotEqual(result, None)

        except IOError as e:
            print('{0} process errored: {1}'.format(temp_minion_proc.pid, e))
        finally:
            terminate_process(temp_minion_proc.pid, kill_children=True)

