from django.urls import path
from . import views

urlpatterns = [
    path('agents/', views.AgentListCreateView.as_view(), name='agent-list'),
    path('agents/<int:pk>/', views.AgentRetrieveUpdateDestroyView.as_view(), name='agent-detail'),
    path('calls/', views.CallListView.as_view(), name='call-list'),
    path('calls/<int:pk>/', views.CallRetrieveView.as_view(), name='call-detail'),
    path('consumption/', views.ConsumptionView.as_view(), name='consumption'),
]