from django.db import models

from nodeconductor.quotas.models import QuotaModelMixin
from nodeconductor.structure import models as structure_models

from ..saltstack.models import SaltStackServiceProjectLink


class ExchangeTenant(QuotaModelMixin, structure_models.Resource, structure_models.PaidResource):
    service_project_link = models.ForeignKey(
        SaltStackServiceProjectLink, related_name='exchange_tenants', on_delete=models.PROTECT)

    domain = models.CharField(max_length=255)
    max_users = models.PositiveSmallIntegerField(help_text='Maximum number of mailboxes')
    mailbox_size = models.PositiveSmallIntegerField(help_text='Maximum size of single mailbox, MB')

    QUOTAS_NAMES = [
        'user_count',  # tenant users count
        'global_mailbox_size',  # size of all tenant mailboxes together
    ]

    @classmethod
    def get_url_name(cls):
        return 'exchange-tenants'

    def get_backend(self):
        from .backend import ExchangeBackend
        return super(ExchangeTenant, self).get_backend(backend_class=ExchangeBackend, tenant=self)


class Group(structure_models.GeneralServiceProperty):
    tenant = models.ForeignKey(ExchangeTenant, related_name='groups')
    username = models.CharField(max_length=255)
    manager_email = models.EmailField(max_length=255)


class Contact(structure_models.GeneralServiceProperty):
    tenant = models.ForeignKey(ExchangeTenant, related_name='contacts')
    email = models.EmailField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)


class User(structure_models.GeneralServiceProperty):
    tenant = models.ForeignKey(ExchangeTenant, related_name='users')
    username = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    mailbox_size = models.PositiveSmallIntegerField(help_text='Maximum size of mailbox, MB')
