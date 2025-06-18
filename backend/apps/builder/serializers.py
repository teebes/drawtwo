from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Title

# Import your models when you create them
# from .models import Project, Canvas, Layer

User = get_user_model()

# Your builder serializers will go here
# Examples:

# class ProjectSerializer(serializers.ModelSerializer):
#     """Serializer for Project model."""
#     owner = serializers.StringRelatedField(read_only=True)
#     canvas_count = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Project
#         fields = ['id', 'name', 'description', 'owner', 'is_public',
#                  'created_at', 'updated_at', 'canvas_count']
#         read_only_fields = ['id', 'created_at', 'updated_at']
#
#     def get_canvas_count(self, obj):
#         """Return the number of canvases in this project."""
#         return obj.canvases.count()

# class CanvasSerializer(serializers.ModelSerializer):
#     """Serializer for Canvas model."""
#     project_name = serializers.CharField(source='project.name', read_only=True)
#     layer_count = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Canvas
#         fields = ['id', 'project', 'project_name', 'name', 'width', 'height',
#                  'data', 'created_at', 'updated_at', 'layer_count']
#         read_only_fields = ['id', 'created_at', 'updated_at']
#
#     def get_layer_count(self, obj):
#         """Return the number of layers in this canvas."""
#         return obj.layers.count()

# class LayerSerializer(serializers.ModelSerializer):
#     """Serializer for Layer model."""
#     canvas_name = serializers.CharField(source='canvas.name', read_only=True)
#
#     class Meta:
#         model = Layer
#         fields = ['id', 'canvas', 'canvas_name', 'name', 'order', 'visible',
#                  'opacity', 'data', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'created_at', 'updated_at']

# Nested serializers for detailed views
# class CanvasDetailSerializer(CanvasSerializer):
#     """Detailed serializer for Canvas with layers."""
#     layers = LayerSerializer(many=True, read_only=True)
#
#     class Meta(CanvasSerializer.Meta):
#         fields = CanvasSerializer.Meta.fields + ['layers']

# class ProjectDetailSerializer(ProjectSerializer):
#     """Detailed serializer for Project with canvases."""
#     canvases = CanvasSerializer(many=True, read_only=True)
#
#     class Meta(ProjectSerializer.Meta):
#         fields = ProjectSerializer.Meta.fields + ['canvases']

class TitleSerializer(serializers.ModelSerializer):
    """Serializer for Title model."""
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Title
        fields = ['id', 'slug', 'version', 'is_latest', 'name', 'description',
                 'author', 'author_username', 'status', 'published_at',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']