from rest_framework import serializers
from agents.models import Agent
from calls.models import Call
from users.models import User


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'name', 'agent_id', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CallSerializer(serializers.ModelSerializer):
    agent_name = serializers.ReadOnlyField(source='agent.name')
    
    class Meta:
        model = Call
        fields = [
            'id', 'call_id', 'agent', 'agent_name', 'duration_seconds', 'status',
            'cost', 'termination_reason', 'language', 'started_at', 'ended_at',
            'minutes_consumed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserConsumptionSerializer(serializers.Serializer):
    total_seconds = serializers.IntegerField()
    total_minutes = serializers.IntegerField()
    total_calls = serializers.IntegerField()
    percentage_used = serializers.FloatField(allow_null=True)
    limit = serializers.IntegerField(source='user.monthly_minutes_limit', read_only=True)