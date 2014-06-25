from functools import wraps
import os
import logging
import shutil

from projects.utils import run

log = logging.getLogger(__name__)


def restoring_chdir(fn):
    #XXX:dc: This would be better off in a neutral module
    @wraps(fn)
    def decorator(*args, **kw):
        try:
            path = os.getcwd()
            return fn(*args, **kw)
        finally:
            os.chdir(path)
    return decorator


class BaseBuilder(object):
    """
    The Base for all Builders. Defines the API for subclasses.

    Expects subclasses to define ``old_artifact_path``,
    which points at the directory where artifacts should be copied from.
    """

    _force = False
    # old_artifact_path = ..

    def __init__(self, state):
        self.state = state
        self.target = self.state.fs.artifact_path(type=self.type)

    def setup_environment(self):
        """
        Build the virtualenv and install the project into it.
        """
        ret_dict = {}
        if self.state.core.virtualenv:
            build_dir = os.path.join(self.state.fs.project.env_path, 'build')
            if os.path.exists(build_dir):
                log.info(LOG_TEMPLATE.format(project=self.state.core.project, version=self.state.core.version, msg='Removing existing build dir'))
                shutil.rmtree(build_dir)

            if self.state.core.system_packages:
                site_packages = '--system-site-packages'
            else:
                site_packages = '--no-site-packages'

            venv_cmd = 'virtualenv-2.7 -p %s' % self.state.core.interpreter
            ret_dict['env'] = run(
                '{cmd} {site_packages} {path}'.format(
                    cmd=venv_cmd,
                    site_packages=site_packages,
                    path=self.state.fs.project.env_path)
            )
            # Other code expects sphinx-build to be installed inside the
            # virtualenv.  Using the -I option makes sure it gets installed
            # even if it is already installed system-wide (and
            # --system-site-packages is used)
            if self.state.core.system_packages:
                ignore_option = '-I'
            else:
                ignore_option = ''
            ret_dict['sphinx'] = run(
                ('{cmd} install -U {ignore_option} sphinx==1.2.2 ' 
                 'virtualenv==1.9.1 docutils==0.11 git+git://github.com/ericholscher/readthedocs-sphinx-ext#egg=readthedocs_ext').format(
                    cmd=self.state.fs.env_bin('pip'),
                    ignore_option=ignore_option))

            if self.state.core.requirements_file:
                os.chdir(self.state.fs.checkout_path)
                ret_dict['requirements'] = run(
                    '{cmd} install --exists-action=w -r {requirements}'.format(
                        cmd=self.state.fs.env_bin('pip'),
                        requirements=self.state.core.requirements_file))

            os.chdir(self.state.fs.checkout_path)
            if os.path.isfile("setup.py"):
                ret_dict['install'] = run(
                    '{cmd} setup.py install --force'.format(
                        cmd=self.state.fs.env_bin('python')))
        return ret_dict


    def force(self, **kwargs):
        """
        An optional step to force a build even when nothing has changed.
        """
        log.info("Forcing a build")
        self._force = True

    def build(self, id=None, **kwargs):
        """
        Do the actual building of the documentation.
        """
        raise NotImplementedError

    def move(self, **kwargs):
        """
        Move the documentation from it's generated place to its artifact directory.
        """
        if os.path.exists(self.old_artifact_path):
            if os.path.exists(self.target):
                shutil.rmtree(self.target)
            log.info("Copying %s on the local filesystem" % self.type)
            shutil.copytree(self.old_artifact_path, self.target)
        else:
            log.warning("Not moving docs, because the build dir is unknown.")
