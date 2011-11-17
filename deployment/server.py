from __future__ import with_statement

import os
import subprocess

from fabric.api import *
from fabric.contrib import files
from fabulaws.ec2 import UbuntuInstance
from fabulaws.ubuntu.packages import ShorewallMixin


class OpenRuralInstance(ShorewallMixin, UbuntuInstance):
    # from http://uec-images.ubuntu.com/releases/10.04/release/
    ami_map = {
        't1.micro': 'ami-ad36fbc4', # us-east-1 10.04 64-bit w/EBS root store
        'm1.small': 'ami-6936fb00', # us-east-1 10.04 32-bit w/instance root store
        'm1.large': 'ami-1136fb78', # us-east-1 10.04 64-bit w/instance root store
    }
    admin_groups = ['admin', 'sudo']
    deployment_dir = os.path.dirname(__file__)
    run_upgrade = True

    def __init__(self, *args, **kwargs):
        self.deploy_user = kwargs.pop('deploy_user')
        self.instance_type = kwargs.pop('instance_type')
        if 'terminate' not in kwargs:
            kwargs['terminate'] = False
        if self.instance_type not in self.ami_map:
            supported_types = ', '.join(self.ami_map.keys())
            raise ValueError('Unsupported instance_type "%s". Pick one of: %s'
                             '' % (self.instance_type, supported_types))
        self.ami = self.ami_map[self.instance_type]
        super(OpenRuralInstance, self).__init__(*args, **kwargs)

    def setup(self):
        """
        Creates necessary directories, installs required packages, and copies
        the required SSH keys to the server.
        """
        super(OpenRuralInstance, self).setup()
        self.create_users()
        with self:
            self._setup_sudoers()

    def _get_users(self):
        """
        Returns a list of tuples of (username, key_file_path).
        """
        users_dir = os.path.join(self.deployment_dir, 'users')
        users = [(n, os.path.join(users_dir, n))
                 for n in os.listdir(users_dir)]
        return users

    def create_users(self):
        """
        Creates sysadmin users on the remote server.
        """
        super(OpenRuralInstance, self).create_users(self._get_users())

    def _setup_sudoers(self):
        """
        Creates the sudoers file on the server, based on the supplied template.
        """
        sudoers_file = os.path.join(self.deployment_dir, 'templates', 'sudoers')
        files.upload_template(sudoers_file, '/etc/sudoers.new', backup=False,
                              use_sudo=True, mode=0440)
        sudo('chown root:root /etc/sudoers.new')
        sudo('mv /etc/sudoers.new /etc/sudoers')


class OpenRuralWebInstance(OpenRuralInstance):

    security_groups = ['openrural-web-sg']
    shorewall_open_ports = ['SSH', 'HTTP', 'HTTPS']
    key_prefix = 'openrural-web-'

    def setup(self):
        """
        Creates necessary directories, installs required packages, and copies
        the required SSH keys to the server.
        """

        super(OpenRuralWebInstance, self).setup()
        self.create_deployer()
        self.update_deployer_keys()

    def create_deployer(self):
        """
        Creates a deployment user with a directory for Apache configurations.
        """
        with self:
            user = self.deploy_user
            sudo('useradd -d /home/{0} -m -s /bin/bash {0}'.format(user))
            sudo('mkdir /home/{0}/.ssh'.format(user), user=user)

    def update_deployer_keys(self):
        """
        Replaces deployer keys with the current sysadmin users keys.
        """
        with self:
            user = self.deploy_user
            file_ = '/home/{0}/.ssh/authorized_keys2'.format(user)
            #sudo('rm /home/{0}/.ssh/authorized_keys*'.format(user), user=user)
            sudo('touch {0}'.format(file_), user=user)
            for _, key_file in self._get_users():
                files.append(file_, open(key_file).read(), use_sudo=True)

