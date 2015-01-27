import json
import os
import os.path
import shutil
import uuid
import re

from django.test import TestCase
from django.contrib.auth.models import User

from projects import tasks
from projects.models import Project
from builds.models import Version
from doc_builder.environments import (DockerEnvironment, DockerBuildCommand,
                                      BuildCommand)
from rtd_tests.utils import make_test_git
from rtd_tests.base import RTDTestCase

from doc_builder.loader import loading
from doc_builder.state import CoreState, SettingsState, VCSState, BuildState, StateEncoder
from filesystem import FilesystemProject, SphinxVersion


class TestState(TestCase):

    def setUp(self):

        root = '/Users/eric/checkouts/django-kong/'

        project_obj = FilesystemProject(
            root=root,
            slug='kong',
            checkout_path=root,
            artifact_path=root + 'rtd-artifact',
            env_path=root + 'rtd-env',
        )

        version_obj = SphinxVersion(project=project_obj, slug='latest')

        vcs = VCSState(repo='https://github.com/username/repo.git', branch='master')

        cstate = CoreState(
            language='en',
            downloads=[],
            versions=[],
            name=None,
            version='latest',
            project='Kong',
            analytics_code=None,
            canonical_url=None,
            single_version=None,
            virtualenv=True,
            interpreter='python2',
            system_packages=False,
            documentation_type='sphinx',
            requirements_file='',
            config_path='',
        )

        sstate = SettingsState()
        self.state = BuildState(fs=version_obj, vcs=vcs, core=cstate, settings=sstate)

    def test_json_encoding(self):
        ret = self.state.json()
        self.assertEqual(
            ret, '{"core": {"requirements_file": "", "virtualenv": true, "name": null, "language": "en", "documentation_type": "sphinx", "downloads": [], "config_path": "", "project": "Kong", "analytics_code": null, "version": "latest", "versions": [], "interpreter": "python2", "canonical_url": null, "system_packages": false, "single_version": null}, "fs": {"project": {"artifact_path": "/Users/eric/checkouts/django-kong/rtd-artifact", "doc_path": "/Users/eric/checkouts/django-kong/kong", "env_path": "/Users/eric/checkouts/django-kong/rtd-env", "checkout_path": "/Users/eric/checkouts/django-kong/", "root": "/Users/eric/checkouts/django-kong/", "slug": "kong"}, "checkout_path": "/Users/eric/checkouts/django-kong/", "slug": "latest"}, "vcs": {"repo": "https://github.com/username/repo.git", "display_bitbucket": false, "display_github": false, "branch": "master"}, "settings": {}}'
        )

    def test_update_config(self):
        obj = {
            'core': {
                'analytics_code': 'Wootles'
            }
        }
        tasks.update_config_from_yaml(self.state, yaml_obj=obj)
        self.assertEqual(self.state.core.analytics_code, 'Wootles')


class TestDockerEnvironment(TestState):

    '''Test docker build environment'''

    fixtures = ['test_data']

    def test_container_id(self):
        '''Test docker build command'''
        docker = DockerEnvironment(self.state)
        self.assertEqual(docker.container_id(), 'latest-of-kong')


class TestBuildCommand(TestCase):

    '''Test build command creation'''

    def test_command_env(self):
        '''Test build command env vars'''
        env = {'FOOBAR': 'foobar',
               'PATH': 'foobar'}
        cmd = BuildCommand('echo', environment=env)
        for key in env.keys():
            self.assertEqual(cmd.environment[key], env[key])

    def test_result(self):
        '''Test result of output using unix true/false commands'''
        cmd = BuildCommand('true')
        with cmd:
            cmd.run()
        self.assertTrue(cmd.successful())

        cmd = BuildCommand('false')
        with cmd:
            cmd.run()
        self.assertTrue(cmd.failed())

    def test_missing_command(self):
        '''Test missing command'''
        path = os.path.join('non-existant', str(uuid.uuid4()))
        self.assertFalse(os.path.exists(path))
        cmd = BuildCommand('/non-existant/foobar')
        with cmd:
            cmd.run()
        missing_re = re.compile(r'(?:No such file or directory|not found)')
        self.assertRegexpMatches(cmd.error, missing_re)

    def test_input(self):
        '''Test input to command'''
        cmd = BuildCommand('/bin/cat')
        with cmd:
            cmd.run(cmd_input="FOOBAR")
        self.assertEqual(cmd.output, "FOOBAR")

    def test_output(self):
        '''Test output command'''
        cmd = BuildCommand('/bin/bash -c "echo -n FOOBAR"')
        with cmd:
            cmd.run()
        self.assertEqual(cmd.output, "FOOBAR")

    def test_error_output(self):
        '''Test error output from command'''
        cmd = BuildCommand('/bin/bash -c "echo -n FOOBAR 1>&2"')
        with cmd:
            cmd.run()
        self.assertEqual(cmd.output, "")
        self.assertEqual(cmd.error, "FOOBAR")


class TestDockerBuildCommand(TestCase):

    '''Test docker build commands'''

    def test_command_build(self):
        '''Test building of command'''
        cmd = DockerBuildCommand('/home/docs/run.sh pip')
        with cmd:
            self.assertEqual(
                cmd.get_command(),
                'docker run -i --rm=true rtfd-build /home/docs/run.sh pip')

        cmd = DockerBuildCommand(['/home/docs/run.sh', 'pip'])
        with cmd:
            self.assertEqual(
                cmd.get_command(),
                'docker run -i --rm=true rtfd-build /home/docs/run.sh pip')

        cmd = DockerBuildCommand(
            ['/home/docs/run.sh', 'pip'],
            name='swayze-express',
            mounts=[('/some/path/checkouts',
                     '/home/docs/checkouts')]
        )
        with cmd:
            self.assertEqual(
                cmd.get_command(),
                ('docker run -i -v /some/path/checkouts:/home/docs/checkouts '
                 '--name=swayze-express --rm=true rtfd-build '
                 '/home/docs/run.sh pip')
            )

        cmd = DockerBuildCommand(
            ['/home/docs/run.sh', 'pip'],
            user='pswayze',
            image='swayze-express',
        )
        with cmd:
            self.assertEqual(
                cmd.get_command(),
                ('docker run -i --user=pswayze --rm=true swayze-express '
                 '/home/docs/run.sh pip')
            )

        cmd = DockerBuildCommand(
            ['/home/docs/run.sh', 'pip'],
            user='pswayze',
            image='swayze-express',
            remove=False,
        )
        with cmd:
            self.assertEqual(
                cmd.get_command(),
                ('docker run -i --user=pswayze swayze-express '
                 '/home/docs/run.sh pip')
            )

    def test_command_exception(self):
        '''Test exception in context manager'''
        cmd = DockerBuildCommand('echo test')

        def _inner():
            with cmd:
                raise Exception('FOOBAR EXCEPTION')

        self.assertRaises(Exception, _inner)
        self.assertIn('FOOBAR EXCEPTION', cmd.error)
