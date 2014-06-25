import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.sqlite'
from doc_builder import loading
from doc_builder.state import CoreState, SettingsState, VCSState, BuildState 
from filesystem import FilesystemProject, SphinxVersion

project_obj = FilesystemProject(
	root='/Users/eric/projects/django-kong', 
	slug='kong',
	checkout_path='/Users/eric/projects/django-kong', 
)
version_obj = SphinxVersion(project=project_obj, slug='latest')

vcs = VCSState(repo='https://github.com/username/repo.git', branch='master')

cstate = CoreState(
    language = 'en',
    downloads =[],
    versions = [],
    name = None,
    version = None,
    analytics_code = None,
    canonical_url = None,
    single_version = None,
    virtualenv = True,
    interpreter = 'python2',
    system_packages = False,
    documentation_type = 'sphinx',
    requirements_file = '',
    config_path = '',
)

sstate = SettingsState(
    static_path = None,
    template_path = None,
    api_host = None,
    media_url = None,
    production_domain = None,
)

state = BuildState(fs=version_obj, vcs=vcs, core=cstate, settings=sstate)

BuilderClass = loading.get('sphinx')
builder = BuilderClass(state=state)
print builder.setup_environment()
print builder.append_conf()
print builder.build()
