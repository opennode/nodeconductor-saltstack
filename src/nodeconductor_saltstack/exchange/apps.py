from django.apps import AppConfig

from nodeconductor.cost_tracking import CostTrackingRegister
from nodeconductor.template import TemplateRegistry


class SaltStackConfig(AppConfig):
    name = 'nodeconductor_saltstack.exchange'
    verbose_name = "NodeConductor SaltStack Exchange"
    service_name = 'SaltStack'

    def ready(self):
        from .cost_tracking import SaltStackCostTrackingBackend
        CostTrackingRegister.register(self.label, SaltStackCostTrackingBackend)

        # template
        from .template import TenantProvisionTemplateForm
        TemplateRegistry.register(TenantProvisionTemplateForm)

        # import it here in order to register as SaltStack backend
        from .backend import ExchangeBackend
