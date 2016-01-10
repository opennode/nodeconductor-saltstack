import django_filters

from . import models


class ContactFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_type='icontains')
    email = django_filters.CharFilter(lookup_type='icontains')
    first_name = django_filters.CharFilter(lookup_type='icontains')
    last_name = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = models.Contact
        fields = [
            'name',
            'email',
            'first_name',
            'last_name',
        ]


class GroupFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_type='icontains')
    username = django_filters.CharFilter(lookup_type='icontains')
    tenant_domain = django_filters.CharFilter(name='tenant__domain')

    class Meta(object):
        model = models.Group
        fields = [
            'name',
            'username',
            'tenant_domain'
        ]


class UserFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_type='icontains')
    email = django_filters.CharFilter(lookup_type='icontains')
    first_name = django_filters.CharFilter(lookup_type='icontains')
    last_name = django_filters.CharFilter(lookup_type='icontains')
    username = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = models.User
        fields = [
            'name',
            'email',
            'username',
            'first_name',
            'last_name',
            'mailbox_size',
        ]
        order_by = [
            'name',
            'email',
            'username',
            'first_name',
            'last_name',
            'mailbox_size',
            # desc
            '-name',
            '-email',
            '-username',
            '-first_name',
            '-last_name',
            '-mailbox_size',
        ]
