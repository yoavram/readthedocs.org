import fnmatch
import os

from doc_builder.constants import BuildException


class FilesystemProject(object):

    """
    FilesystemProject takes a root path on the filesystem,
    and a slug for the project.
    """

    doc_path = None
    checkout_path = None
    env_path = None
    artifact_path = None

    def __init__(self, root, slug, **kwargs):
        self.root = root
        self.slug = slug
        self.doc_path = os.path.join(self.root, self.slug)
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)

    def get_artifact_path(self, version, type):
        return os.path.join(self.doc_path, "artifacts", version, type)


class ReadTheDocsProject(FilesystemProject):

    def __init__(self, *args, **kwargs):
        super(ReadTheDocsProject, self).__init__(*args, **kwargs)
        self.checkout_path = os.path.join(self.doc_path, 'checkouts')
        self.env_path = os.path.join(self.doc_path, 'envs')
        self.artifact_path = os.path.join(self.doc_path, 'artifacts')

        if not os.path.exists(self.doc_path):
            os.makedirs(self.doc_path)
        if not os.path.exists(self.checkout_path):
            os.makedirs(self.checkout_path)
        if not os.path.exists(self.env_path):
            os.makedirs(self.env_path)
        if not os.path.exists(self.artifact_path):
            os.makedirs(self.artifact_path)


class Version(object):

    def __init__(self, project, slug):
        """
        Pass an optional conf_file.
        Otherwise we will guess where one is dynamically.
        """
        self.project = project
        self.slug = slug
        self.checkout_path = self.project.checkout_path
        #self.checkout_path = os.path.join(self.project.checkout_path, self.slug)

    @property
    def full_doc_path(self):
        """
        The path to the documentation root in the project.
        """
        for possible_path in ['docs', 'doc', 'Doc']:
            full_possible_path = os.path.join(
                self.checkout_path, '%s' % possible_path)
            if os.path.exists(full_possible_path):
                return full_possible_path
        return self.checkout_path

    def find(self, file):
        """
        A balla API to find files inside of a projects dir.
        """
        matches = []
        for root, dirnames, filenames in os.walk(self.full_doc_path):
            for filename in fnmatch.filter(filenames, file):
                matches.append(os.path.join(root, filename))
        return matches

    def full_find(self, file):
        """
        A balla API to find files inside of a projects dir.
        """
        matches = []
        print "Checking %s for conf.py" % self.checkout_path
        for root, dirnames, filenames in os.walk(self.checkout_path):
            for filename in fnmatch.filter(filenames, file):
                matches.append(os.path.join(root, filename))
        return matches

    def artifact_path(self, type):
        """
        The path to the build html docs in the project.
        """
        return os.path.join(self.project.artifact_path, self.slug, type)

    def env_bin(self, bin):
        return os.path.join(self.project.env_path, 'bin', bin)


class SphinxVersion(Version):

    """
    SphinxVersion represents a Sphinx version on the filesystem.
    """
    conf = None

    @property
    def conf_file(self):
        if self.conf:
            return os.path.join(self.checkout_path, self.conf)
        files = self.find('conf.py')
        if not files:
            files = self.full_find('conf.py')
        if len(files) == 1:
            return files[0]
        elif len(files) > 1:
            for file in files:
                if file.find('doc', 70) != -1:
                    return file
        else:
            # Having this be translatable causes this odd error:
            # ProjectImportError(<django.utils.functional.__proxy__ object at
            # 0x1090cded0>,)
            raise BuildException(
                u"Conf File Missing. Please make sure you have a conf.py in your project."
            )

    @property
    def conf_dir(self):
        if self.conf_file:
            return self.conf_file.replace('/conf.py', '')
