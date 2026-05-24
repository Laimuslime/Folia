from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import ForumGroup, ForumCategory, ForumThread, ForumPost, ForumPostRevision
from .serializers import (
    ForumGroupSerializer, ForumCategorySerializer,
    ForumThreadSerializer, ForumThreadDetailSerializer,
    ForumPostSerializer,
)
from folia.wiki.parser import render_wikidot_markup


class ForumGroupViewSet(viewsets.ModelViewSet):
    serializer_class = ForumGroupSerializer

    def get_queryset(self):
        site = getattr(self.request, "current_site", None)
        if site:
            return ForumGroup.objects.filter(site=site, visible=True).prefetch_related("categories")
        return ForumGroup.objects.none()


class ForumThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ForumThreadSerializer

    def get_queryset(self):
        site = getattr(self.request, "current_site", None)
        if not site:
            return ForumThread.objects.none()
        qs = ForumThread.objects.filter(site=site).select_related("user", "category")
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ForumThreadDetailSerializer
        return ForumThreadSerializer

    def perform_create(self, serializer):
        site = self.request.current_site
        thread = serializer.save(
            user=self.request.user,
            user_string=self.request.user.username,
            site=site,
        )

        # Create first post
        content = self.request.data.get("content", "")
        ForumPost.objects.create(
            thread=thread,
            user=self.request.user,
            user_string=self.request.user.username,
            title=thread.title,
            text=content,
            site=site,
        )

        # Update counts
        thread.category.number_threads += 1
        thread.category.number_posts += 1
        thread.category.save()

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        thread = self.get_object()
        posts = thread.posts.select_related("user").order_by("date_posted")
        return Response(ForumPostSerializer(posts, many=True).data)


class ForumPostViewSet(viewsets.ModelViewSet):
    serializer_class = ForumPostSerializer

    def get_queryset(self):
        site = getattr(self.request, "current_site", None)
        if not site:
            return ForumPost.objects.none()
        return ForumPost.objects.filter(site=site).select_related("user", "thread")

    def perform_create(self, serializer):
        site = self.request.current_site
        post = serializer.save(
            user=self.request.user,
            user_string=self.request.user.username,
            site=site,
        )

        # Update thread
        thread = post.thread
        thread.number_posts += 1
        thread.last_post = post
        thread.save()

        # Update category
        thread.category.number_posts += 1
        thread.category.last_post = post
        thread.category.save()

    def perform_update(self, serializer):
        post = self.get_object()
        # Save revision before editing
        ForumPostRevision.objects.create(
            post=post,
            user=post.user,
            user_string=post.user_string,
            text=post.text,
            title=post.title,
        )
        serializer.save(
            date_last_edited=timezone.now(),
            edited_user=self.request.user,
            edited_user_string=self.request.user.username,
            revision_number=post.revision_number + 1,
        )
