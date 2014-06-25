import re
import logging
import yaml

from projects.forms import ImportProjectForm
from projects.tasks import LOG_TEMPLATE

log = logging.getLogger(__name__)


class CoreState(object):
    language = 'en'
    downloads =[]
    versions = []
    name = None
    project = None
    version = None
    analytics_code = None
    canonical_url = None
    single_version = None

    virtualenv = True
    interpreter = 'python2'
    system_packages = False

    documentation_type = 'sphinx'
    requirements_file = ''
    config_path = ''

    def __init__(self, **kwargs):
        pass

class SettingsState(object):
    API_HOST = 'https://readthedocs.org'
    MEDIA_URL = 'https://media.readthedocs.org'
    PRODUCTION_DOMAIN = 'https://readthedocs.org'
    STATIC_PATH = '/static/'
    TEMPLATE_PATH = None

    def __init__(self, **kwargs):
        pass


class VCSState(object):

    GH_REGEXS = [
        re.compile('github.com/(.+)/(.+)(?:\.git){1}'),
        re.compile('github.com/(.+)/(.+)'),
        re.compile('github.com:(.+)/(.+).git'),
    ]

    BB_REGEXS = [
        re.compile('bitbucket.org/(.+)/(.+)/'),
        re.compile('bitbucket.org/(.+)/(.+)'),
        re.compile('bitbucket.org:(.+)/(.+)\.git'),
    ]


    def __init__(self, repo, branch):
        self.repo = repo
        self.branch = branch
        self.display_github = False
        self.display_bitbucket = False

    @property
    def username_repo(self):
        if 'github' in self.repo:
            matches = self.GH_REGEXS
            self.display_github = True
        elif 'bitbucket' in self.repo:
            matches = self.BB_REGEXS
            self.display_bitbucket = True
        for regex in matches:
            match = regex.search(self.repo)
            if match:
                return match.groups()
        return (None, None)

class BuildState(object):
    """
    An object that maintains the state for the build happening on Read the Docs.

    It's tied to a specific version, 
    and will either come from a YAML file in the repo,
    or from the database.
    """

    def __init__(self, fs, vcs, core, settings):
        self.fs = fs
        self.vcs = vcs
        self.core = core
        self.settings = settings

    # def get_build_state(self, path):
    #     """
    #     Generate the build state for a version.
    #     """
    #     log.debug("Checking for json config")
    #     try:
    #         rtd_yaml = open(path)
    #         yaml_obj = yaml.load(rtd_yaml)
    #         for key in yaml_obj.keys():
    #             # Treat the defined fields on the Import form as
    #             # the canonical list of allowed user editable fields.
    #             # This is in essense just another UI for that form.
    #             if key not in ImportProjectForm._meta.fields:
    #                 del yaml_obj[key]
    #         log.debug("Updated from JSON.")
    #     except IOError:
    #         log.debug("No .readthedocs.yml found.")
    #     return self.__class__(**yaml_obj)
