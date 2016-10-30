import os
import boto3

from django.core import serializers
from django.core.urlresolvers import reverse_lazy
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from songs.models import Song, Track


class SongsView(generic.ListView):
    template_name = 'users/songs.html'
    context_object_name = 'published_song_list'

    def get_queryset(self):
        return Song.objects.filter(created_by__username=self.kwargs['username'], published=True)

    def get_context_data(self, **kwargs):
        context = super(SongsView, self).get_context_data(**kwargs)
        context['unpublished_song_list'] = Song.objects.filter(created_by__username=self.kwargs['username'],
                                                               published=False)

        return context


class SongTrackUpdate(LoginRequiredMixin, generic.UpdateView):
    model = Track
    fields = ['instrument', 'public']
    template_name = 'users/song_track_update.html'
    context_object_name = 'track'

    def form_valid(self, form):
        audio_file = self.request.FILES.get('audio')
        user = self.request.user
        song = Song.objects.get(pk=self.kwargs['song_id'])
        requesting_tracks = form.instance.public

        if requesting_tracks:
            form.instance.public = True
            form.instance.audio_url = None
            form.instance.audio_name = None
            form.instance.audio_content_type = None
            form.instance.audio_size = None
        else:
            form.instance.public = False

            if audio_file:
                s3_bucket = os.environ.get('S3_BUCKET')
                s3_client = boto3.client('s3')
                s3_track_file_path = '%s/songs/%s/tracks/%s' % (user, song.uuid, audio_file.name)

                form.instance.audio_url = 'https://s3-us-west-2.amazonaws.com/%s/%s' % (s3_bucket, s3_track_file_path)
                form.instance.audio_name = audio_file.name
                form.instance.audio_content_type = audio_file.content_type
                form.instance.audio_size = audio_file.size

                # TODO: try catch here
                s3_client.upload_fileobj(audio_file, s3_bucket, s3_track_file_path, ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': audio_file.content_type
                })

        form.instance.created_by = user

        return super(SongTrackUpdate, self).form_valid(form)

    def get_object(self, queryset=None):
        return Track.objects.get(pk=self.kwargs['track_id'])

    def get_context_data(self, **kwargs):
        context = super(SongTrackUpdate, self).get_context_data(**kwargs)
        context['song'] = Song.objects.get(id=self.kwargs['song_id'])
        context['track_json'] = serializers.serialize("json", [context['track'], ])
        context['song_json'] = serializers.serialize("json", [context['song'], ])
        return context

    def get_success_url(self):
        return reverse_lazy('songs:edit', kwargs={
            'pk': self.kwargs['song_id']
        })
