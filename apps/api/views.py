from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from agents.models import Agent
from calls.models import Call
from client_dashboard.services import get_user_monthly_consumption
from .serializers import AgentSerializer, CallSerializer, UserConsumptionSerializer


class AgentListCreateView(generics.ListCreateAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own agents
        return Agent.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AgentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)


class CallListView(generics.ListAPIView):
    serializer_class = CallSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see calls belonging to their agents
        return Call.objects.filter(agent__user=self.request.user).select_related('agent')


class CallRetrieveView(generics.RetrieveAPIView):
    serializer_class = CallSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Call.objects.filter(agent__user=self.request.user).select_related('agent')


class ConsumptionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consumption = get_user_monthly_consumption(request.user)
        # Add the user's monthly limit to the response
        consumption['limit'] = request.user.monthly_minutes_limit
        serializer = UserConsumptionSerializer(consumption)
        return Response(serializer.data)