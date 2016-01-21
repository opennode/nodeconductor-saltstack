from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_200_OK

from nodeconductor.structure import views as structure_views

from . import filters, models, serializers
from ..saltstack.views import BasePropertyViewSet, track_exceptions


class TenantViewSet(structure_views.BaseOnlineResourceViewSet):
    queryset = models.ExchangeTenant.objects.all()
    serializer_class = serializers.TenantSerializer

    def perform_provision(self, serializer):
        resource = serializer.save()
        backend = resource.get_backend()
        backend.provision(resource)

    def get_serializer_class(self):
        serializer = super(TenantViewSet, self).get_serializer_class()
        if self.action == 'domain':
            serializer = serializers.ExchangeDomainSerializer
        return serializer

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


class UserViewSet(BasePropertyViewSet):
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer
    filter_class = filters.UserFilter
    backend_name = 'users'

    def post_create(self, user, backend_user):
        user.password = backend_user.password
        user.save()

    # XXX: put was added as portal has a temporary bug with widget update
    @detail_route(methods=['post', 'put'])
    @track_exceptions
    def password(self, request, pk=None, **kwargs):
        user = self.get_object()
        backend = self.get_backend(user.tenant)
        response = backend.reset_password(id=user.backend_id)
        user.password = response.password
        user.save()
        data = serializers.UserPasswordSerializer(instance=user, context={'request': request}).data
        return Response(data, status=HTTP_200_OK)


class ContactViewSet(BasePropertyViewSet):
    queryset = models.Contact.objects.all()
    serializer_class = serializers.ContactSerializer
    filter_class = filters.ContactFilter
    backend_name = 'contacts'


class GroupViewSet(BasePropertyViewSet):
    queryset = models.Group.objects.all()
    serializer_class = serializers.GroupSerializer
    filter_class = filters.GroupFilter
    backend_name = 'groups'

    # XXX: put was added as portal has a temporary bug with widget update
    @detail_route(methods=['get', 'post', 'put'])
    @track_exceptions
    def members(self, request, pk=None, **kwargs):
        group = self.get_object()
        backend = self.get_backend(group.tenant)
        user_ids = [u.id for u in backend.list_members(id=group.backend_id)]
        exist_users = models.User.objects.filter(backend_id__in=user_ids)

        if request.method in ('POST', 'PUT'):
            serializer = serializers.GroupMemberSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            users = serializer.validated_data['users']
            for exist_user in exist_users:
                if exist_user not in users:
                    backend.del_member(id=group.backend_id, user_id=exist_user.backend_id)

            new_users = [user for user in users if user not in exist_users]
            if new_users:
                backend.add_member(id=group.backend_id, user_id=','.join([u.backend_id for u in new_users]))

            data = serializers.UserSerializer(
                instance=users, context={'request': request}, many=True).data

            return Response(data, status=HTTP_201_CREATED)

        else:
            data = serializers.UserSerializer(instance=exist_users, many=True, context={'request': request}).data
            return Response(data)
