import os
import shutil
import codecs
import pickle
from glob import glob
import logging
import zipfile

from django.template import Template, Context, loader as template_loader
from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from builds import utils as version_utils
from doc_builder.base import BaseBuilder, restoring_chdir
from projects.utils import run
from tastyapi import apiv2

log = logging.getLogger(__name__)

TEMPLATE_DIR = '%s/readthedocs/templates/sphinx' % settings.SITE_ROOT
STATIC_DIR = '%s/_static' % TEMPLATE_DIR

class BaseSphinx(BaseBuilder):
    """
    The parent for most sphinx builders.
    """

    def __init__(self, *args, **kwargs):
        super(BaseSphinx, self).__init__(*args, **kwargs)
        self.old_artifact_path = os.path.join(self.state.fs.conf_dir, self.sphinx_build_dir)

    @restoring_chdir
    def build(self, **kwargs):
        os.chdir(self.state.fs.conf_dir)
        force_str = " -E "
        build_command = "%s %s -b %s -D language=%s . %s " % (
            self.state.fs.env_bin(bin='sphinx-build'),
            force_str,
            self.sphinx_builder,
            self.state.core.language,
            self.sphinx_build_dir,
        )
        results = run(build_command, shell=True)
        return results



    def append_conf(self, **kwargs):
        """Modify the given ``conf.py`` file from a whitelisted user's project.
        """
        outfile = codecs.open(self.state.fs.conf_file, encoding='utf-8', mode='a')
        outfile.write("\n")

        rtd_ctx = Context({
            'state': self.state,
            'json_state': pickle.dumps(self.state),
            # 'versions': project.api_versions(),
            # 'downloads': self.version.get_downloads(pretty=True),
            # 'current_version': self.version.slug,
            # 'project': project,
            # 'settings': settings,
            # 'static_path': STATIC_DIR,
            # 'template_path': TEMPLATE_DIR,
            # 'conf_py_path': conf_py_path,
            # 'downloads': apiv2.version(self.version.pk).downloads.get()['downloads'],
            # 'api_host': getattr(settings, 'SLUMBER_API_HOST', 'https://readthedocs.org'),
            # # GitHub
            # 'github_user': github_info[0],
            # 'github_repo': github_info[1],
            # 'github_version':  remote_version,
            # 'display_github': display_github,
            # # BitBucket
            # 'bitbucket_user': bitbucket_info[0],
            # 'bitbucket_repo': bitbucket_info[1],
            # 'bitbucket_version':  remote_version,
            # 'display_bitbucket': display_bitbucket,
        })
        rtd_string = template_loader.get_template('doc_builder/conf.py.tmpl').render(rtd_ctx)
        outfile.write(rtd_string)


class HtmlBuilder(BaseSphinx):
    type = 'sphinx'
    sphinx_builder = 'readthedocs'
    sphinx_build_dir = '_build/html'


class HtmlDirBuilder(HtmlBuilder):
    type = 'sphinx_htmldir'
    sphinx_builder = 'readthedocsdirhtml'


class SingleHtmlBuilder(HtmlBuilder):
    type = 'sphinx_singlehtml'
    sphinx_builder = 'readthedocssinglehtml'


class SearchBuilder(BaseSphinx):
    type = 'sphinx_search'
    sphinx_builder = 'json'
    sphinx_build_dir = '_build/json'

    
class LocalMediaBuilder(BaseSphinx):
    type = 'sphinx_localmedia'
    sphinx_builder = 'readthedocssinglehtmllocalmedia'
    sphinx_build_dir = '_build/localmedia'

    @restoring_chdir
    def move(self, **kwargs):
        log.info("Creating zip file from %s" % self.old_artifact_path)
        target_file = os.path.join(self.target, '%s.zip' % self.version.project.slug)
        if not os.path.exists(self.target):
            os.makedirs(self.target)
        if os.path.exists(target_file):
            os.remove(target_file)

        # Create a <slug>.zip file
        os.chdir(self.old_artifact_path)
        archive = zipfile.ZipFile(target_file, 'w')
        for root, subfolders, files in os.walk('.'):
            for file in files:
                to_write = os.path.join(root, file)
                archive.write(
                    filename=to_write,
                    arcname=os.path.join("%s-%s" % (self.version.project.slug,
                                                    self.version.slug),
                                         to_write)
                )
        archive.close()


class EpubBuilder(BaseSphinx):
    type = 'sphinx_epub'
    sphinx_builder = 'epub'
    sphinx_build_dir = '_build/epub'

    def move(self, **kwargs):
        from_globs = glob(os.path.join(self.old_artifact_path, "*.epub"))
        if not os.path.exists(self.target):
            os.makedirs(self.target)
        if from_globs:
            from_file = from_globs[0]
            to_file = os.path.join(self.target, "%s.epub" % self.version.project.slug)
            run('mv -f %s %s' % (from_file, to_file))

class PdfBuilder(BaseSphinx):
    type = 'sphinx_pdf'
    sphinx_build_dir = '_build/latex'

    @restoring_chdir
    def build(self, **kwargs):
        project = self.version.project
        os.chdir(project.conf_dir(self.version.slug))
        #Default to this so we can return it always.
        results = {}
        if project.use_virtualenv:
            latex_results = run('%s -b latex -D language=%s -d _build/doctrees . _build/latex'
                                % (project.env_bin(version=self.version.slug,
                                                   bin='sphinx-build'), project.language))
        else:
            latex_results = run('sphinx-build -b latex -D language=%s -d _build/doctrees '
                                '. _build/latex' % project.language)

        if latex_results[0] == 0:
            os.chdir('_build/latex')
            tex_files = glob('*.tex')

            if tex_files:
                # Run LaTeX -> PDF conversions
                pdflatex_cmds = [('pdflatex -interaction=nonstopmode %s'
                                 % tex_file) for tex_file in tex_files]
                # Run twice because of https://github.com/rtfd/readthedocs.org/issues/749
                pdf_results = run(*pdflatex_cmds)
                pdf_results = run(*pdflatex_cmds)
            else:
                pdf_results = (0, "No tex files found", "No tex files found")

            results = [
                latex_results[0] + pdf_results[0],
                latex_results[1] + pdf_results[1],
                latex_results[2] + pdf_results[2],
            ]
        else:
            results = latex_results
        return results

    def move(self, **kwargs):
        if not os.path.exists(self.target):
            os.makedirs(self.target)

        exact = os.path.join(self.old_artifact_path, "%s.pdf" % self.version.project.slug)
        exact_upper = os.path.join(self.old_artifact_path, "%s.pdf" % self.version.project.slug.capitalize())

        if os.path.exists(exact):
            from_file = exact
        elif os.path.exists(exact_upper):
            from_file = exact_upper
        else:
            from_globs = glob(os.path.join(self.old_artifact_path, "*.pdf"))
            if from_globs:
                from_file = from_globs[0]
            else:
                from_file = None
        if from_file:
            to_file = os.path.join(self.target, "%s.pdf" % self.version.project.slug)
            run('mv -f %s %s' % (from_file, to_file))

