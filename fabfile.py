import os
import random
import string
import logging
import tempfile

from getpass import getpass
from fabric.api import cd, env, local, require, run, sudo, task
from fabric.contrib.files import exists, upload_template
from fabric.colors import yellow

from argyle import nginx, postgres, rabbitmq, supervisor, system

from fabulaws.api import *

from deployment.server import *

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

fabulaws_logger = logging.getLogger('fabulaws')
fabulaws_logger.setLevel(logging.DEBUG)

PROJECT_ROOT = os.path.dirname(__file__)
env.project = 'openrural'
env.deploy_user = 'openrural'
env.webserver_user = 'openrural-web'
env.database_user = 'openrural'
env.database_host = 'localhost'
env.template_db = 'template_postgis'
env.home = '/home/%(deploy_user)s/' % env
env.repo = u'https://github.com/openrural/openrural-nc.git'
env.shell = '/bin/bash -c'
env.placements = ['us-east-1a', 'us-east-1d']
env.environments = ['staging', 'production']
env.deployments = ['whiteville', 'orange']
env.deployment_dir = os.path.join(os.path.dirname(__file__), 'deployment') 
env.templates_dir = os.path.join(env.deployment_dir, 'templates')
env.server_ports = {'staging': 8000, 'production': 8001}
env.branches = {
    'whiteville': 'master',
    'orange': 'master',
}
env.instance_types = {'staging': 't1.micro', 'production': 'm1.small'}


def _get_hosts(deployment, environment):
    env.filters = {'tag:environment': environment,
                   'tag:deployment': deployment}
    inst_kwargs = {'deploy_user': env.deploy_user,
                   'instance_type': env.instance_type}
    servers = ec2_instances(filters=env.filters, cls=OpenRuralWebInstance,
                            inst_kwargs=inst_kwargs)
    return [server.hostname for server in servers]


def _setup_path():
    env.root = os.path.join(env.home, 'www', env.environment)
    env.log_dir = os.path.join(env.root, 'log')
    env.code_root = os.path.join(env.root, 'code_root')
    env.project_root = os.path.join(env.code_root, env.project)
    env.virtualenv_root = os.path.join(env.root, 'env')
    env.media_root = os.path.join(env.root, 'uploaded_media')
    env.static_root = os.path.join(env.root, 'static_media')
    env.services = os.path.join(env.home, 'services')
    env.database_name = '%s_%s1' % (env.project, env.environment)
    env.vhost = '%s_%s' % (env.project, env.environment)
    if (env.deployment_tag, env.environment) in env.branches:
        env.branch = env.branches[(env.deployment_tag, env.environment)]
    elif env.deployment_tag in env.branches:
        env.branch = env.branches[env.deployment_tag]
    elif env.environment in env.branches:
        env.branch = env.branches[env.environment]
    else:
        raise ValueError('Could not find branch to deploy.')
    env.server_port = env.server_ports[env.environment]
    env.instance_type = env.instance_types[env.environment]
    if not env.hosts:
        env.hosts = _get_hosts(env.deployment_tag, env.environment)


def _random_password(length=8, chars=string.letters + string.digits):
    return ''.join([random.choice(chars) for i in range(length)])


def _load_passwords(names, length=20, generate=False):
    """Retrieve password from the user's home directory, or generate a new random one if none exists"""

    for name in names:
        filename = ''.join([env.home, name])
        if generate:
            passwd = _random_password(length=length)
            sudo('touch %s' % filename, user=env.deploy_user)
            sudo('chmod 600 %s' % filename, user=env.deploy_user)
            with hide('running'):
                sudo('echo "%s">%s' % (passwd, filename), user=env.deploy_user)
        if files.exists(filename):
            with hide('stdout'):
                passwd = sudo('cat %s' % filename).strip()
        else:
            passwd = getpass('Please enter %s: ' % name)
        setattr(env, name, passwd)


@task
def new_instance(placement, deployment, environment, count=1):
    if placement not in env.placements:
        abort('Choose a valid placement: %s' % ', '.join(env.placements))
    if deployment not in env.deployments:
        abort('Choose a valid deployment: %s' % ', '.join(env.deployments))
    if environment not in env.environments:
        abort('Choose a valid environment: %s' % ', '.join(env.environments))
    count = int(count)
    tags = {'environment': environment, 'deployment': deployment}
    env.hosts = []
    env.deployment_tag = deployment
    env.environment = environment
    for x in range(count):
        instance_type = env.instance_types[env.environment]
        instance = OpenRuralWebInstance(instance_type=instance_type,
                                        deploy_user=env.deploy_user,
                                        placement=placement, tags=tags)
        env.hosts.append(instance.hostname)
    _setup_path()


@task
def staging(deployment):
    if deployment not in env.deployments:
        abort('Choose a valid deployment: %s' % ', '.join(env.deployments))
    env.deployment_tag = deployment
    env.environment = 'staging'
    _setup_path()


@task
def production():
    abort('No production environment has been configured yet.')


@task
def update_sysadmin_users():
    """Create sysadmin users on the server"""
    
    require('environment', provided_by=env.environments)
    servers = ec2_instances(filters=env.filters, cls=OpenRuralWebInstance,
                            inst_kwargs={'deploy_user': env.deploy_user,
                                         'instance_type': env.instance_type})
    for server in servers:
        server.create_users()
        server.update_deployer_keys()


@task
def install_packages():
    """Install packages, given a list of package names"""

    require('environment', provided_by=env.environments)
    packages_file = os.path.join(PROJECT_ROOT, 'requirements', 'packages.txt')
    system.install_packages_from_file(packages_file)


@task
def upgrade_packages():
    """Bring all the installed packages up to date"""

    require('environment', provided_by=env.environments)
    system.update_apt_sources()
    system.upgrade_apt_packages()


@task
def create_db_user():
    """Create the Postgres user."""

    require('environment', provided_by=env.environments)
    _load_passwords(['database_password'], generate=True)
    postgres.create_db_user(env.database_user, password=env.database_password)


@task
def create_postgis_template():
    """Create the Postgres postgis template database."""

    require('environment', provided_by=env.environments)
    share_dir = run('pg_config --sharedir').strip()
    env.postgis_path = '%s/contrib' % share_dir
    sudo('createdb -E UTF8 %(template_db)s' % env, user='postgres')
    sudo('createlang -d %(template_db)s plpgsql' % env, user='postgres')
    # Allows non-superusers the ability to create from this template
    sudo('psql -d postgres -c "UPDATE pg_database SET datistemplate=\'true\' WHERE datname=\'%(template_db)s\';"' % env, user='postgres')
    # Loading the PostGIS SQL routines
    sudo('psql -d %(template_db)s -f %(postgis_path)s/postgis.sql' % env, user='postgres')
    sudo('psql -d %(template_db)s -f %(postgis_path)s/spatial_ref_sys.sql' % env, user='postgres')
    # Enabling users to alter spatial tables.
    sudo('psql -d %(template_db)s -c "GRANT ALL ON geometry_columns TO PUBLIC;"' % env, user='postgres')
    #sudo('psql -d %(template_db)s -c "GRANT ALL ON geography_columns TO PUBLIC;"' % env, user='postgres')
    sudo('psql -d %(template_db)s -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"' % env, user='postgres')


@task
def create_db():
    """Create the Postgres database."""

    require('environment', provided_by=env.environments)
    sudo('createdb -O %(database_user)s -T %(template_db)s %(database_name)s' % env, user='postgres')


@task
def reset_db():
    """Drop and recreate the Postgres database."""
    
    if not env.environment == 'staging':
        abort('reset_db requires the staging environment.')
    answer = prompt('Are you sure you want to drop and re-create the database?', default='n')
    if answer == 'y':
        sudo('dropdb %(database_name)s' % env, user='postgres')
        create_db()
        mgmt('syncdb', '--migrate')
    else:
        abort('Aborting...')


@task
def link_config_files():
    """Include the nginx and supervisor config files via the Ubuntu standard inclusion directories"""

    require('environment', provided_by=env.environments)
    with settings(warn_only=True):
        sudo('rm /etc/nginx/sites-enabled/default')
        sudo('rm /etc/nginx/sites-enabled/%(project)s-*.conf' % env)
        sudo('rm /etc/supervisor/conf.d/%(project)s-*.conf' % env)
    sudo('ln -s /home/%(deploy_user)s/services/nginx/%(environment)s.conf /etc/nginx/sites-enabled/%(project)s-%(environment)s.conf' % env)
    sudo('ln -s /home/%(deploy_user)s/services/supervisor/%(environment)s.conf /etc/supervisor/conf.d/%(project)s-%(environment)s.conf' % env)


@task
def create_webserver_user():
    """Create a user for gunicorn, celery, etc."""

    require('environment', provided_by=env.environments)
    if env.webserver_user != env.deploy_user: # deploy_user already exists
        sudo('useradd --system %(webserver_user)s' % env)


@task
def setup_server():
    """Set up a server for the first time in preparation for deployments."""

    require('environment', provided_by=env.environments)
    upgrade_packages()
    # Install required system packages for deployment, plus some extras
    # Install pip, and use it to install virtualenv
    install_packages()
    sudo("easy_install -i http://d.pypi.python.org/simple -U pip")
    sudo("pip install -i http://d.pypi.python.org/simple -U virtualenv")
    create_postgis_template()
    create_db_user()
    create_db()
    create_webserver_user()


@task
def clone_repo():
    """ clone a new copy of the hg repository """

    with cd(env.root):
        sudo('git clone %(repo)s %(code_root)s' % env, user=env.deploy_user)


@task
def setup_dirs():
    """ create (if necessary) and make writable uploaded media, log, etc. directories """

    require('environment', provided_by=env.environments)
    sudo('mkdir -p %(log_dir)s' % env, user=env.deploy_user)
    sudo('chmod a+w %(log_dir)s' % env )
    sudo('mkdir -p %(services)s/nginx' % env, user=env.deploy_user)
    sudo('mkdir -p %(services)s/supervisor' % env, user=env.deploy_user)
    sudo('mkdir -p %(services)s/gunicorn' % env, user=env.deploy_user)
    sudo('mkdir -p %(media_root)s' % env)
    sudo('chown %(webserver_user)s %(media_root)s' % env)
    sudo('mkdir -p %(static_root)s' % env)
    sudo('chown %(webserver_user)s %(static_root)s' % env)


@task
def _upload_template(filename, destination, **kwargs):
    """Upload template and chown to given user"""
    user = kwargs.pop('user')
    kwargs['use_sudo'] = True
    upload_template(filename, destination, **kwargs)
    sudo('chown %(user)s:%(user)s %(dest)s' % {'user': user, 'dest': destination})


@task
def upload_supervisor_conf():
    """Upload Supervisor configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'supervisor.conf')
    destination = os.path.join(env.services, 'supervisor', '%(environment)s.conf' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)
    supervisor.supervisor_command('update')


@task
def upload_nginx_conf():
    """Upload Nginx configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'nginx.conf')
    destination = os.path.join(env.services, 'nginx', '%(environment)s.conf' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)
    restart_nginx()


@task
def upload_gunicorn_conf():
    """Upload Gunicorn configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'gunicorn.conf')
    destination = os.path.join(env.services, 'gunicorn', '%(environment)s.py' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)


@task
def update_services():
    """ upload changes to services configurations as nginx """

    upload_supervisor_conf()
    upload_nginx_conf()
    upload_gunicorn_conf()


@task
def create_virtualenv():
    """ setup virtualenv on remote host """

    require('virtualenv_root', provided_by=env.environments)
    args = '--clear --distribute --no-site-packages'
    sudo('virtualenv %s %s' % (args, env.virtualenv_root),
         user=env.deploy_user)


@task
def update_requirements():
    """ update external dependencies on remote host """

    require('code_root', provided_by=env.environments)
    requirements = os.path.join(env.code_root, 'requirements')
    sdists = os.path.join(requirements, 'sdists')
    base_cmd = ['pip install']
    base_cmd += ['-q -E %(virtualenv_root)s' % env]
    base_cmd += ['--no-index --find-links=file://%s' % sdists]
    # install GDAL by hand, before anything else that might depend on it
    cmd = base_cmd + ['--no-install "GDAL==1.6.1"']
    sudo(' '.join(cmd), user=env.deploy_user)
    # this directory won't exist if GDAL was already installed
    if files.exists('%(virtualenv_root)s/build/GDAL' % env):
        sudo('rm -f %(virtualenv_root)s/build/GDAL/setup.cfg' % env, user=env.deploy_user)
        with cd('%(virtualenv_root)s/build/GDAL' % env):
            sudo('%(virtualenv_root)s/bin/python setup.py build_ext '
                 '--gdal-config=gdal-config '
                 '--library-dirs=/usr/lib '
                 '--libraries=gdal1.6.0 '
                 '--include-dirs=/usr/include/gdal '
                 'install' % env, user=env.deploy_user)
    # force reinstallation of OpenBlock every time
    with settings(warn_only=True):
        sudo('pip uninstall -y -E %(virtualenv_root)s ebpub ebdata obadmin' % env)
    for file_name in ['ebpub.txt', 'ebdata.txt', 'obadmin.txt', 'openrural.txt']:
        apps = os.path.join(requirements, file_name)
        cmd = base_cmd + ['--requirement %s' % apps]
        sudo(' '.join(cmd), user=env.deploy_user)


@task
def create_local_settings():
    """ create local_settings.py on the remote host """

    require('environment', provided_by=env.environments)
    _load_passwords(['database_password'])
    template = os.path.join(env.templates_dir, 'local_settings.py')
    destination = os.path.join(env.project_root, 'local_settings.py')
    _upload_template(template, destination, context=env, user=env.deploy_user)


@task
def bootstrap():
    """ initialize remote host environment (virtualenv, deploy, update) """

    require('environment', provided_by=env.environments)
    sudo('mkdir -p %(root)s' % env, user=env.deploy_user)
    clone_repo()
    setup_dirs()
    link_config_files()
    update_services()
    create_virtualenv()
    update_requirements()
    create_local_settings()


@task
def update_source():
    """Checkout the latest code from repo."""

    require('environment', provided_by=env.environments)
    with cd(env.code_root):
        sudo('git pull', user=env.deploy_user)
        sudo('git checkout %(branch)s' % env, user=env.deploy_user)


@task
def mgmt(command, *args):
    """Run the given management command on the remote server."""

    require('environment', provided_by=env.environments)
    env.command = command
    env.command_args = ' '.join(args)
    cmd = 'PYTHONPATH=%(code_root)s '\
          'DJANGO_SETTINGS_MODULE=openrural.local_settings '\
          '%(virtualenv_root)s/bin/django-admin.py %(command)s %(command_args)s' % env
    with cd(env.project_root):
        sudo(cmd, user=env.deploy_user)


@task
def import_locations(type_slug, zip_url):
    """Import locations of the specified location type from the given URL."""

    require('environment', provided_by=env.environments)
    locations_dir = '/tmp/fab_location_importer'
    if files.exists(locations_dir):
        sudo('rm -rf %s' % locations_dir, user=env.deploy_user)
    sudo('mkdir %s' % locations_dir, user=env.deploy_user)
    cmd = 'PYTHONPATH=%(code_root)s '\
          'DJANGO_SETTINGS_MODULE=openrural.local_settings '\
          '%(virtualenv_root)s/bin/import_locations' % env
    with cd(locations_dir):
        sudo('wget -O locations.zip %s' % zip_url, user=env.deploy_user)
        sudo('unzip -d locations locations.zip', user=env.deploy_user)
        sudo(' '.join([cmd, type_slug, 'locations']), user=env.deploy_user)


@task
def restart_nginx():
    """Restart Nginx."""

    require('environment', provided_by=env.environments)
    system.restart_service('nginx')


@task
def restart_server():
    """Restart gunicorn server."""

    require('environment', provided_by=env.environments)
    command = 'restart %(environment)s:%(environment)s-server' % env
    supervisor.supervisor_command(command)


@task
def restart_supervisor():
    """Restart all Supervisor controlled processes."""

    require('environment', provided_by=env.environments)
    supervisor.supervisor_command('restart %(environment)s:*' % env)


@task
def restart_all():
    """Restart Nginx and Supervisor controlled processes."""

    restart_nginx()
    restart_supervisor()


@task
def deploy():
    """Deploy to a given environment."""

    require('environment', provided_by=env.environments)
    update_source()
    update_requirements()
    mgmt('syncdb', '--migrate')
    restart_supervisor()


@task
def update_openblock():
    """Update local sdists to latest OpenBlock version"""

    tf = tempfile.mktemp(suffix='-openblock')
    local('git clone git://github.com/openplans/openblock.git {0}'.format(tf))
    dest = os.path.join(PROJECT_ROOT, 'requirements', 'sdists')
    for name in ('obadmin', 'ebdata', 'ebpub'):
        package = os.path.join(tf, name)
        os.chdir(package)
        local('pip install -e {source} -d {dest}'.format(source=package,
                                                         dest=dest))
    shutil.rmtree(tf)


@task
def develop(repo, no_index=False):
    repo = os.path.abspath(repo)
    sdists = os.path.join(PROJECT_ROOT, 'requirements', 'sdists')
    sdists = '--no-index --find-links=file://%s' % sdists
    for name in ('ebpub', 'ebdata', 'obadmin'):
        print(yellow('Installing {0}'.format(name)))
        package = os.path.join(repo, name)
        os.chdir(package)
        cmd = ['pip install']
        if no_index:
            cmd.append(sdists)
        cmd.append('-r requirements.txt')
        local(' '.join(cmd))
        local('python setup.py develop --no-deps')
