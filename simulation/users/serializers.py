from djoser.serializers import UserCreateSerializer as BaseUserRegistrationSerializer
from rest_framework import serializers

class UserRegistrationSerializer(BaseUserRegistrationSerializer):
    id = serializers.IntegerField(required=False)
    class Meta(BaseUserRegistrationSerializer.Meta):
        fields = ('email', 'name', 'password', 'id')
