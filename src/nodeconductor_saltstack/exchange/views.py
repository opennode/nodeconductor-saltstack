from cStringIO import StringIO
from django.http import HttpResponse

from rest_framework.decorators import detail_route
from rest_framework.exceptions import APIException, NotAcceptable
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_200_OK, HTTP_400_BAD_REQUEST

from nodeconductor.core.tasks import send_task
from nodeconductor.core.csv import UnicodeDictReader, UnicodeDictWriter
from nodeconductor.structure import views as structure_views

from . import filters, models, serializers
from ..saltstack.views import BasePropertyViewSet, track_exceptions


class TenantViewSet(structure_views.BaseOnlineResourceViewSet):
    queryset = models.ExchangeTenant.objects.all()
    serializer_class = serializers.TenantSerializer
    filter_class = filters.TenantFilter

    def perform_provision(self, serializer):
        resource = serializer.save()
        backend = resource.get_backend()
        backend.provision(resource)

    # XXX: put was added as portal has a temporary bug with widget update
    @detail_route(methods=['get', 'post', 'put'])
    @track_exceptions
    def domain(self, request, pk=None, **kwargs):
        tenant = self.get_object()
        backend = tenant.get_backend()

        if request.method in ('POST', 'PUT'):
            domain_serializer = serializers.ExchangeDomainSerializer(instance=tenant, data=request.data)
            domain_serializer.is_valid(raise_exception=True)
            new_domain = domain_serializer.validated_data['domain']
            if new_domain != tenant.domain:
                backend.tenants.change(domain=new_domain)
                tenant.domain = new_domain
                tenant.save()
            data = serializers.ExchangeDomainSerializer(instance=tenant, context={'request': request}).data
            return Response(data, status=HTTP_200_OK)
        elif request.method == 'GET':
            data = serializers.ExchangeDomainSerializer(instance=tenant, context={'request': request}).data
            return Response(data)

    # XXX: put was added as portal has a temporary bug with widget update
    @detail_route(methods=['get', 'post', 'put'])
    @track_exceptions
    def users(self, request, pk=None, **kwargs):
        tenant = self.get_object()

        if request.method in ('POST', 'PUT'):
            if 'csv' not in request.data:
                return Response("Expecting 'csv' parameter as a file or JSON string",
                                status=HTTP_400_BAD_REQUEST)

            csvfile = request.data['csv']
            if isinstance(csvfile, basestring):
                csvfile = StringIO(csvfile.encode('utf-8'))

            reader = UnicodeDictReader(csvfile)
            tenant_url = self.get_serializer(instance=tenant).data['url']
            data = [dict(tenant=tenant_url, **row) for row in reader]

            serializer = serializers.UserSerializer(data=data, many=True, context={'request': request})
            serializer.is_valid(raise_exception=True)

            for user in serializer.validated_data:
                del user['tenant']
                send_task('exchange', 'create_user')(
                    tenant_uuid=tenant.uuid.hex,
                    notify=user.pop('notify'),
                    **user)

            return Response("%s users scheduled for creation" % len(serializer.validated_data))

        elif request.method == 'GET':
            users = models.User.objects.filter(tenant=tenant)
            serializer = serializers.UserSerializer(instance=users, many=True, context={'request': request})

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="%s_users.csv"' % tenant.backend_id

            exclude = ('url', 'tenant', 'tenant_uuid', 'tenant_domain', 'manager', 'notify')
            headers = [f for f in serializers.UserSerializer.Meta.fields if f not in exclude]
            writer = UnicodeDictWriter(response, fieldnames=headers)
            writer.writeheader()
            writer.writerows(serializer.data)
            return response


class ExchangePropertyViewSet(BasePropertyViewSet):

    def manage_members(self, add_method=None, del_method=None):
        obj = self.get_object()
        request = self.request
        backend = self.get_backend(obj.tenant)

        serializer = serializers.MemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        users = serializer.validated_data['users']

        if not users:
            raise NotAcceptable("Empty users list")

        if request.method == 'POST':
            if add_method is None:
                raise APIException("Add method is not defined")

            add_func = getattr(backend, add_method)
            add_func(id=obj.backend_id, user_id=','.join(u.backend_id for u in users))

            data = serializers.UserSerializer(
                instance=users, context={'request': request}, many=True).data

            return Response(data, status=HTTP_201_CREATED)

        elif request.method == 'DELETE':
            if del_method is None:
                raise APIException("Delete method is not defined")

            del_func = getattr(backend, del_method)
            for user in users:
                del_func(id=obj.backend_id, user_id=user.backend_id)

            return Response(status=HTTP_204_NO_CONTENT)


class UserViewSet(ExchangePropertyViewSet):
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer
    filter_class = filters.UserFilter
    backend_name = 'users'

    def get_serializer_class(self):
        serializer_class = super(UserViewSet, self).get_serializer_class()
        if self.action == 'password':
            serializer_class = serializers.UserPasswordSerializer
        return serializer_class

    def post_create(self, user, serializer, backend_user):
        user.password = backend_user.password
        user.save()

        if serializer.validated_data.get('notify'):
            user.notify()

    # XXX: put was added as portal has a temporary bug with widget update
    @detail_route(methods=['post', 'put'])
    @track_exceptions
    def password(self, request, pk=None, **kwargs):
        user = self.get_object()
        backend = self.get_backend(user.tenant)
        response = backend.reset_password(id=user.backend_id)
        user.password = response.password
        user.save()

        serializer_class = serializers.UserPasswordSerializer
        serializer = serializer_class(instance=user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get('notify'):
            user.notify()

        return Response(serializer.data, status=HTTP_200_OK)

    @detail_route(methods=['post', 'delete'])
    @track_exceptions
    def sendonbehalf(self, request, pk=None, **kwargs):
        return self.manage_members(add_method='add_send_on_behalf', del_method='del_send_on_behalf')

    @detail_route(methods=['post', 'delete'])
    @track_exceptions
    def sendas(self, request, pk=None, **kwargs):
        return self.manage_members(add_method='add_send_as', del_method='del_send_as')


class ContactViewSet(BasePropertyViewSet):
    queryset = models.Contact.objects.all()
    serializer_class = serializers.ContactSerializer
    filter_class = filters.ContactFilter
    backend_name = 'contacts'


class GroupViewSet(ExchangePropertyViewSet):
    queryset = models.Group.objects.all()
    serializer_class = serializers.GroupSerializer
    filter_class = filters.GroupFilter
    backend_name = 'groups'

    def post_create(self, group, serializer, backend_group):
        backend = self.get_backend(group.tenant)
        members = group.members.values_list('backend_id', flat=True)
        if members:
            backend.add_member(id=group.backend_id, user_id=','.join(members))

    def post_update(self, group, serializer):
        backend = self.get_backend(group.tenant)
        new_members = set(u.backend_id for u in serializer.validated_data['members'])
        cur_members = set(group.members.values_list('backend_id', flat=True))

        new_users = new_members - cur_members
        if new_users:
            backend.add_member(id=group.backend_id, user_id=','.join(new_users))

        for old_user in cur_members - new_members:
            backend.del_member(id=group.backend_id, user_id=old_user)

    @detail_route(methods=['get'])
    def members(self, request, pk=None, **kwargs):
        group = self.get_object()

        return Response(serializers.UserSerializer(
            group.members.all(), many=True, context={'request': request}).data, status=HTTP_200_OK)
