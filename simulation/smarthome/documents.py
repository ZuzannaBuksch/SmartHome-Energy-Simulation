from django_elasticsearch_dsl import (
    Document,
    fields,
)
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import connections

from .models import DeviceRaport, Device

from config.settings import ELASTICSEARCH_CONNECTION

connections.create_connection(**ELASTICSEARCH_CONNECTION)

@registry.register_document
class DeviceRaportDocument(Document):
    device = fields.ObjectField(properties={
            'name' : fields.TextField(),
            'id' : fields.IntegerField(attr='id'),
    })

    class Index:
        name = 'device_raports'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    
    class Django:
        model = DeviceRaport
        fields = [
            'turned_on',
            'turned_off',
        ]
    
    def get_queryset(self):
        return super(DeviceRaportDocument, self).get_queryset().select_related(
            'device'
        )

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Device):
            return related_instance.device_raports.all()
