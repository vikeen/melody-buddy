from django.contrib.auth.models import User
from django.views import generic
from songs.models import Song, TrackRequest

from .mixins import ProfileMixin, HasAccessToRestrictedUserProfile
from .models import Skill


class Detail(ProfileMixin, generic.DetailView):
    model = User
    template_name = 'users/user_detail_overview.html'
    context_object_name = 'view_user'

    def get_object(self, queryset=None):
        return User.objects.get(username=self.kwargs['username'])


class SongIndex(ProfileMixin, generic.ListView):
    template_name = 'users/user_detail_song_list.html'
    context_object_name = 'song_list'

    def get_queryset(self):
        song_list_filter = {
            'created_by__username': self.kwargs['username']
        }

        title = self.request.GET.get('title')

        if title:
            song_list_filter['title__icontains'] = self.request.GET.get('title')

        return Song.objects.filter(**song_list_filter)


class SkillIndex(ProfileMixin, generic.ListView):
    model = Skill
    template_name = 'users/user_detail_skill_list.html'
    context_object_name = 'skill_list'

    def get_queryset(self):
        skill_list_filter = {}

        name = self.request.GET.get('name')

        if name:
            skill_list_filter['name__icontains'] = self.request.GET.get('name')

        return Skill.objects.filter(user__username=self.kwargs['username'], **skill_list_filter)


class TrackRequestIndex(HasAccessToRestrictedUserProfile,
                        ProfileMixin,
                        generic.ListView):
    model = TrackRequest
    template_name = 'users/user_detail_track_request_list.html'
    context_object_name = 'pending_track_request_list'

    def get_queryset(self):
        return TrackRequest.objects.filter(track__song__created_by=self.request.user, status='pending')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['approved_track_request_list'] = TrackRequest.objects.filter(
            track__song__created_by=self.request.user, status='approved')
        context['declined_track_request_list'] = TrackRequest.objects.filter(
            track__song__created_by=self.request.user, status='declined')

        return context


class ContributionIndex(ProfileMixin,
                        generic.ListView):
    model = TrackRequest
    template_name = 'users/user_detail_contribution_list.html'
    context_object_name = 'pending_contribution_list'

    def get_queryset(self):
        return TrackRequest.objects.filter(created_by__username=self.kwargs['username'], status='pending')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['approved_contribution_list'] = TrackRequest.objects.filter(
            created_by__username=self.kwargs['username'], status='approved')
        context['declined_contribution_list'] = TrackRequest.objects.filter(
            created_by__username=self.kwargs['username'], status='declined')

        return context
