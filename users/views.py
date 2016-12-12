from django.contrib.auth.models import User
from django.views import generic
from songs.models import Song, TrackRequest
from .mixins import ProfileMixin


class ProfileDetail(ProfileMixin, generic.DetailView):
    model = User
    template_name = 'users/user_detail_overview.html'
    context_object_name = 'view_user'

    def get_object(self, queryset=None):
        return User.objects.get(username=self.kwargs['username'])


class ProfileSongIndex(ProfileMixin, generic.ListView):
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


class ProfileSkillIndex(ProfileMixin, generic.ListView):
    template_name = 'users/user_detail_skill_list.html'
    context_object_name = 'skill_list'

    def get_queryset(self):
        return User.objects.get(username=self.kwargs['username']).skill_set.all()


class ProfileTrackRequestIndex(ProfileMixin, generic.ListView):
    model = TrackRequest
    template_name = 'users/user_detail_track_request_list.html'
    context_object_name = 'track_request_list'

    def get_queryset(self):
        return TrackRequest.objects.filter(track__song__created_by__username=self.kwargs['username'])