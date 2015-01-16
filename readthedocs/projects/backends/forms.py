'''
Project forms loaded by configuration settings

'''

from django.utils.module_loading import import_by_path
from django.conf import settings


# Project Import Wizard
GitHubImportForm = import_by_path(getattr(
    settings,
    'PROJECT_GITHUB_FORM',
    'projects.forms.ProjectBasicsForm'
))
