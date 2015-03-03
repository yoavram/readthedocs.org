import logging
import fileinput
import json

from django.core.management.base import BaseCommand

from projects import tasks
from tastyapi import api

from doc_builder.state import BuildState

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """Trigger build for project version"""

    args = '<files>'

    def handle(self, files=None, *args, **options):

        def _return_json(output):
            return json.dumps(output)

        output = None
        try:
            input_data = self._get_input(files)
            state_obj = json.loads(input_data)
            state = BuildState()
            state.from_json(state_obj)
            log.info('Building %s', state.core.version)
            output = _return_json(tasks.docker_build(state))
        except Exception as e:
            log.exception('Error starting docker build')
            output = _return_json(
                {'doc_builder': (-1, '', '{0}: {1}'.format(type(e).__name__,
                                                           str(e)))})
        finally:
            print(output)

    def _get_input(self, files=None):
        if files is None:
            files = '-'
        fh = fileinput.FileInput(files)
        return ''.join([line for line in fh])
