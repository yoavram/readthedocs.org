import json

from .backend import DjangoStorage
from .session import UnsafeSessionAuthentication

from django.core import serializers
from django.shortcuts import render_to_response
from django.template import RequestContext
from sphinx.websupport import WebSupport

from rest_framework import permissions, status
from rest_framework.renderers import JSONRenderer, JSONPRenderer, BrowsableAPIRenderer
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    renderer_classes,
)
from rest_framework.response import Response
from comments.models import DocumentComment, DocumentNode, NodeSnapshot, DocumentCommentSerializer,\
    DocumentNodeSerializer
from projects.models import Project

storage = DjangoStorage()

support = WebSupport(
    srcdir='/Users/eric/projects/readthedocs.org/docs',
    builddir='/Users/eric/projects/readthedocs.org/docs/_build/websupport',
    datadir='/Users/eric/projects/readthedocs.org/docs/_build/websupport/data',
    storage=storage,
    docroot='websupport',
)


########
# called by javascript
########

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
@renderer_classes((JSONRenderer, JSONPRenderer, BrowsableAPIRenderer))
def get_comments(request):
    node_id = request.GET.get('node', '')
    node = get_node_from_request(request=request, hash=node_id)
    ret_comments = []
    for comment in node.comments.all():
        json_data = json.loads(serializers.serialize("json", [comment]))[0]
        fields = json_data['fields']
        fields['pk'] = json_data['pk']
        ret_comments.append(
            fields
        )

    data = {'source': '',
            'comments': ret_comments}
    if data:
        return Response(data)
    else:
        return Response(status=404)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
@renderer_classes((JSONRenderer, JSONPRenderer, BrowsableAPIRenderer))
def get_options(request):
    return Response(support.base_comment_opts)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
@renderer_classes((JSONRenderer, JSONPRenderer, BrowsableAPIRenderer))
def get_metadata(request):
    """
    Check for get_metadata
    GET: page
    """
    document = request.GET.get('page', '')
    return Response(storage.get_metadata(docname=document))


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([UnsafeSessionAuthentication])
@renderer_classes((JSONRenderer, JSONPRenderer))
def add_comment(request):
    try:
        hash = request.POST['node']
        commit = request.POST['commit']
    except KeyError:
        return Response("You must provide a node (hash) and initial commit.",
                        status=status.HTTP_400_BAD_REQUEST)
    node = get_node_from_request(request=request, hash=hash)
    if not node:
        project = Project.objects.get(slug=request.DATA['project'])
        version = project.versions.get(slug=request.DATA['version'])
        node = DocumentNode.objects.create(project=project,
                                           version=version,
                                           hash=hash,
                                           commit=commit,
                                           )
        created = True

    text = request.POST.get('text', '')
    comment = DocumentComment.objects.create(text=text,
                                             node=node,
                                             user=request.user)

    serialized_comment = DocumentCommentSerializer(comment)
    return Response(serialized_comment.data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([UnsafeSessionAuthentication])
@renderer_classes((JSONRenderer, JSONPRenderer))
def attach_comment(request):
    comment_id = request.POST.get('comment', '')
    comment = DocumentComment.objects.get(pk=comment_id)

    node_id = request.POST.get('node', '')
    snapshot = NodeSnapshot.objects.get(hash=node_id)
    comment.node = snapshot.node

    serialized_comment = DocumentCommentSerializer(comment)
    serialized_comment.data
    return Response(serialized_comment.data)


#######
# Normal Views
#######

def build(request):
    support.build()


def serve_file(request, file):
    document = support.get_document(file)

    return render_to_response('doc.html',
                              {'document': document},
                              context_instance=RequestContext(request))

######
# Called by Builder
######


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def has_node(request):
    """
    Checks to see if a node exists.
    GET: node_id - The node's ID to check
    """
    node_id = request.GET.get('node_id', '')
    exists = storage.has_node(node_id)
    return Response({'exists': exists})


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([UnsafeSessionAuthentication])
@renderer_classes((JSONRenderer,))
def add_node(request):
    post_data = request.DATA
    page = post_data.get('document', '')
    id = post_data.get('id', '')
    project = post_data.get('project', '')
    version = post_data.get('version', '')
    commit = post_data.get('commit', '')
    created = storage.add_node(id, page, project=project, version=version, commit=commit)
    return Response({'created': created})


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([UnsafeSessionAuthentication])
@renderer_classes((JSONRenderer,))
def update_node(request):
    post_data = request.DATA
    old_hash = post_data.get('old_hash')
    node = get_node_from_request(request=request, hash=old_hash)
    try:
        new_hash = post_data['new_hash']
        node.update_hash(new_hash, commit)
        return Response(DocumentNodeSerializer(node).data)
    except KeyError:
        return Response("You must include new_hash and commit in POST payload to this view.",
                        status.HTTP_400_BAD_REQUEST)


def get_node_from_request(request, hash):
    post_data = request.DATA
    if not post_data:
        post_data = request.QUERY_PARAMS
    project = post_data.get('project', '')
    version = post_data.get('version', '')
    page = post_data.get('page', '')

    project_obj = Project.objects.get(slug=project)
    version_obj = project_obj.versions.get(slug=version)

    node = DocumentNode.objects.from_hash(project=project_obj, version=version_obj, page=page, hash=hash)
    return node
