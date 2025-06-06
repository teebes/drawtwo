from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

# Import your models and serializers when you create them
# from .models import Project, Canvas, Layer
# from .serializers import ProjectSerializer, CanvasSerializer, LayerSerializer

User = get_user_model()

# Your builder views will go here
# Examples:

# class ProjectViewSet(viewsets.ModelViewSet):
#     """ViewSet for managing drawing projects."""
#     serializer_class = ProjectSerializer
#     permission_classes = [IsAuthenticated]
#
#     def get_queryset(self):
#         """Return projects for the current user."""
#         return Project.objects.filter(owner=self.request.user)
#
#     def perform_create(self, serializer):
#         """Set the owner to the current user when creating."""
#         serializer.save(owner=self.request.user)
#
#     @action(detail=True, methods=['post'])
#     def duplicate(self, request, pk=None):
#         """Create a copy of an existing project."""
#         project = self.get_object()
#         # Implementation for duplicating a project
#         return Response({'status': 'Project duplicated'})

# class CanvasViewSet(viewsets.ModelViewSet):
#     """ViewSet for managing canvases within projects."""
#     serializer_class = CanvasSerializer
#     permission_classes = [IsAuthenticated]
#
#     def get_queryset(self):
#         """Return canvases for projects owned by the current user."""
#         return Canvas.objects.filter(project__owner=self.request.user)
#
#     @action(detail=True, methods=['post'])
#     def save_data(self, request, pk=None):
#         """Save canvas drawing data."""
#         canvas = self.get_object()
#         canvas.data = request.data.get('data', {})
#         canvas.save()
#         return Response({'status': 'Canvas data saved'})

# Example function-based view
# from rest_framework.decorators import api_view, permission_classes

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def project_stats(request):
#     """Get statistics about the user's projects."""
#     user_projects = Project.objects.filter(owner=request.user)
#     stats = {
#         'total_projects': user_projects.count(),
#         'public_projects': user_projects.filter(is_public=True).count(),
#         'private_projects': user_projects.filter(is_public=False).count(),
#     }
#     return Response(stats)
