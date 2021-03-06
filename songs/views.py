import zipfile
import os
import boto3
import logging
import uuid

from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers
from django.core.files.base import File
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import redirect
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from shutil import rmtree
from tempfile import mkdtemp

from .s3 import S3TrackUploadClient, S3TrackRequestUploadClient
from .notifications import NotificationTypes
from .licenses import license
from .models import Song, SongStats, Track, TrackRequest
from .mixins import HasAccessToSongMixin, HasAccessToTrack, MediaPlayerMixin, SongMixin


class BaseSongUpdate(LoginRequiredMixin,
                     HasAccessToSongMixin,
                     MediaPlayerMixin,
                     generic.UpdateView):
    model = Song
    fields = ["title", 'description']
    context_object_name = 'song'

    def get_success_url(self):
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class BaseContributorCreate(LoginRequiredMixin,
                            HasAccessToSongMixin,
                            SongMixin,
                            generic.CreateView):
    model = Track
    fields = ['instrument']

    def form_valid(self, form):
        song = Song.objects.get(pk=self.kwargs['pk'])

        form.instance.created_by = self.request.user
        form.instance.song = song
        form.instance.uuid = uuid.uuid4()
        form.instance.public = True
        form.instance.audio_url = None
        form.instance.audio_name = None
        form.instance.audio_content_type = None
        form.instance.audio_size = None

        return super().form_valid(form)


class BaseTrackCreate(LoginRequiredMixin,
                      HasAccessToSongMixin,
                      SongMixin,
                      generic.CreateView):
    model = Track
    fields = ['instrument']

    def form_valid(self, form):
        audio_file = self.request.FILES.get('audio')
        song = Song.objects.get(pk=self.kwargs['pk'])

        track_uuid = uuid.uuid4()

        form.instance.created_by = self.request.user
        form.instance.song = song
        form.instance.uuid = track_uuid

        form.instance.public = False

        if audio_file:
            s3_track_upload_client = S3TrackUploadClient(song, track_uuid, audio_file.content_type)
            form.instance.audio_url = s3_track_upload_client.get_upload_url()
            form.instance.audio_name = audio_file.name
            form.instance.audio_content_type = audio_file.content_type
            form.instance.audio_size = audio_file.size
            s3_track_upload_client.upload_file_obj(audio_file)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class BaseTrackDelete(LoginRequiredMixin,
                      HasAccessToTrack,
                      SongMixin,
                      generic.DeleteView):
    model = Track
    context_object_name = 'track'
    pk_url_kwarg = 'track_id'

    def get_success_url(self):
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class SongIndex(LoginRequiredMixin,
                generic.ListView):
    model = Song
    context_object_name = 'song_list'

    def get_queryset(self):
        accepting_contributions = self.request.GET.get('accepting_contributions')

        if accepting_contributions:
            return Song.objects.exclude(created_by=self.request.user).filter(track__public=True).distinct("id")
        else:
            return Song.objects.all()


class SongDetail(MediaPlayerMixin,
                 generic.DetailView):
    model = Song
    context_object_name = 'song'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        song = context['song']

        song.songstats.views += 1
        song.songstats.save()

        return context


class SongUpdate(BaseSongUpdate):
    template_name = 'songs/song_update.html'

    def get_success_url(self):
        messages.success(self.request, 'Updated %s.' % self.object.title)
        return super().get_success_url()


class SongDelete(LoginRequiredMixin,
                 HasAccessToSongMixin,
                 generic.DeleteView):
    model = Song
    template_name = 'songs/song_confirm_delete.html'
    context_object_name = 'song'

    def get_success_url(self):
        messages.success(self.request, 'Deleted %s.' % self.object.title)
        return reverse('users:detail', kwargs={
            'username': self.request.user
        })


class WizardCreate(LoginRequiredMixin,
                   SongMixin,
                   generic.CreateView):
    model = Song
    fields = ['title', 'description']
    template_name = 'songs/song_wizard_detail.html'

    def get_license_information(self):
        return license[self.license]

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        SongStats.objects.create(song=self.object)
        return reverse('songs:wizard_create_confirm', kwargs={
            'pk': self.object.pk
        })


class WizardCreateConfirm(BaseSongUpdate):
    template_name = 'songs/song_wizard_detail_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['tracks'] = context['song'].track_set.filter(public=False)
        context['contributor_tracks'] = context['song'].track_set.filter(public=True)
        return context

    def get_success_url(self):
        return reverse('songs:wizard_create_confirm', kwargs={
            'pk': self.object.pk
        })


class WizardTrackCreate(BaseTrackCreate):
    template_name = 'songs/song_wizard_track_create.html'

    def get_success_url(self):
        return reverse('songs:wizard_track_create', kwargs={
            'pk': self.kwargs['pk']
        })


class WizardTrackDelete(BaseTrackDelete):
    def get_success_url(self):
        return self.request.POST.get('next')


class WizardContributorCreate(BaseContributorCreate):
    template_name = 'songs/song_wizard_contributor_create.html'

    def get_success_url(self):
        return reverse('songs:wizard_contributor_create', kwargs={
            'pk': self.kwargs['pk']
        })


class WizardContributorDelete(BaseTrackDelete):
    def get_success_url(self):
        return self.request.POST.get('next')


# Redirect the user to song edit once song creation is complete.
@login_required
def wizard_complete(request, pk):
    song = Song.objects.get(pk=pk)
    messages.success(request, '"%s" has been created.' % song.title)
    return HttpResponseRedirect(reverse('songs:edit', kwargs={
        'pk': song.pk
    }))


class TrackDelete(BaseTrackDelete):
    template_name = 'songs/track_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, 'Deleted track - %s.' % self.object.instrument)
        return super().get_success_url()


class TrackCreate(BaseTrackCreate):
    template_name = 'songs/track_create.html'

    def get_success_url(self):
        messages.success(self.request, 'Created track - %s.' % self.object.instrument)
        return super().get_success_url()


class TrackUpdate(LoginRequiredMixin,
                  HasAccessToTrack,
                  SongMixin,
                  generic.UpdateView):
    model = Track
    fields = ['instrument']
    template_name = 'songs/track_update.html'
    context_object_name = 'track'
    pk_url_kwarg = 'track_id'

    def form_valid(self, form):
        audio_file = self.request.FILES.get('audio')
        song = Song.objects.get(pk=self.kwargs['pk'])

        form.instance.public = False

        if audio_file:
            s3_track_upload_client = S3TrackUploadClient(song, self.object.uuid, audio_file.content_type)
            form.instance.audio_url = s3_track_upload_client.get_upload_url()
            form.instance.audio_name = audio_file.name
            form.instance.audio_content_type = audio_file.content_type
            form.instance.audio_size = audio_file.size
            s3_track_upload_client.upload_file_obj(audio_file)

        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Updated track - %s.' % self.object.instrument)
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class ContributorCreate(BaseContributorCreate):
    template_name = 'songs/contributor_create.html'

    def get_success_url(self):
        messages.success(self.request, 'Created contributor - %s.' % self.object.instrument)
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class ContributorUpdate(LoginRequiredMixin,
                        HasAccessToTrack,
                        SongMixin,
                        generic.UpdateView):
    model = Track
    fields = ['instrument']
    template_name = 'songs/contributor_update.html'
    context_object_name = 'track'
    pk_url_kwarg = 'track_id'

    def form_valid(self, form):
        form.instance.public = True
        form.instance.audio_url = None
        form.instance.audio_name = None
        form.instance.audio_content_type = None
        form.instance.audio_size = None

        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Updated contributor - %s.' % self.object.instrument)
        return reverse('songs:edit', kwargs={
            'pk': self.kwargs['pk']
        })


class ContributorDelete(BaseTrackDelete):
    template_name = 'songs/contributor_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, 'Deleted contributor - %s.' % self.object.instrument)
        return super().get_success_url()


class TrackRequestCreate(LoginRequiredMixin,
                         SongMixin,
                         generic.CreateView):
    model = TrackRequest
    fields = []
    template_name = 'songs/track_request_create.html'

    def form_valid(self, form):
        audio_file = self.request.FILES.get('audio')
        song = Song.objects.get(pk=self.kwargs['pk'])
        track_request_uuid = uuid.uuid4()

        s3_track_request_upload_client = S3TrackRequestUploadClient(song, track_request_uuid, audio_file.content_type)

        form.instance.uuid = track_request_uuid
        form.instance.created_by = self.request.user
        form.instance.track_id = self.kwargs['track_id']
        form.instance.audio_url = s3_track_request_upload_client.get_upload_url()
        form.instance.audio_name = audio_file.name
        form.instance.audio_content_type = audio_file.content_type
        form.instance.audio_size = audio_file.size

        s3_track_request_upload_client.upload_file_obj(audio_file)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['track'] = Track.objects.get(pk=self.kwargs['track_id'])
        return context

    def get_success_url(self):
        messages.success(self.request, 'Created track request')
        NotificationTypes.track_request_pending(self.request.user,
                                                recipient=self.object.track.song.created_by,
                                                action_object=self.object,
                                                target=self.object.track.song)

        return reverse('songs:detail', kwargs={
            'pk': self.kwargs['pk']
        })


class TrackRequestDetail(LoginRequiredMixin,
                         SongMixin,
                         generic.DetailView):
    model = TrackRequest
    template_name = 'songs/track_request_detail.html'
    context_object_name = 'track_request'
    pk_url_kwarg = 'track_request_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # only grab confirmed tracks and the track which is being viewed for a request
        context['tracks'] = context['song'].track_set.filter(Q(public=False) | Q(pk=self.kwargs['track_id']))
        context['tracks_json'] = serializers.serialize("json", context['tracks'])
        context['track_request_json'] = serializers.serialize("json", [context['track_request'], ])
        return context


@login_required()
@require_http_methods(["POST"])
@csrf_protect
def approve_track_request(request, *args, **kwargs):
    track_request = TrackRequest.objects.get(pk=kwargs['track_request_id'])
    track = track_request.track

    # TODO: move s3 resource as well
    track.audio_content_type = track_request.audio_content_type
    track.audio_name = track_request.audio_name
    track.audio_size = track_request.audio_size
    track.audio_url = track_request.audio_url
    track.public = False
    track.contributed_by = track_request.created_by
    track.save()

    track_request.status = 'approved'
    track_request.save()

    messages.success(request, 'Track request approved')
    NotificationTypes.track_request_approved(request.user, recipient=track_request.created_by,
                                             action_object=track_request)

    return redirect(reverse('songs:track_request_detail', kwargs=kwargs))


@login_required()
@require_http_methods(["POST"])
@csrf_protect
def decline_track_request(request, *args, **kwargs):
    track_request = TrackRequest.objects.get(pk=kwargs['track_request_id'])

    track_request.status = 'declined'
    track_request.save()

    messages.success(request, 'Track request declined')
    NotificationTypes.track_request_declined(request.user, recipient=track_request.created_by,
                                             action_object=track_request)

    return redirect(reverse('users:track_requests', kwargs={
        'username': request.user.username
    }))


@login_required()
@require_http_methods(["GET"])
def download_song(request, pk):
    s3_bucket = os.environ.get('S3_BUCKET')
    s3_client = boto3.client('s3')

    song = Song.objects.get(pk=pk)
    downloadable_tracks = song.track_set.exclude(public=True)

    temp_download_dir = mkdtemp()

    archive_file_name = '%s.zip' % song.title
    archive_file_path = '%s/%s' % (temp_download_dir, archive_file_name)

    archive = zipfile.ZipFile(archive_file_path, 'w')

    logging.info('download song: [%s] with title: [%s]' % (song.id, song.title))

    for track in downloadable_tracks:
        s3_track_file_path = '%s/songs/%s/tracks/%s' % (song.created_by, song.uuid, track.audio_name)
        temp_download_file_path = os.path.join(temp_download_dir, track.audio_name)
        logging.info('downloading track [%s] to [%s]' % (s3_track_file_path, temp_download_file_path))

        s3_client.download_file(
            Bucket=s3_bucket,
            Key=s3_track_file_path,
            Filename=temp_download_file_path)

        archive.write(temp_download_file_path, track.audio_name)

    # add license to the download zip
    # archive.writestr('LICENSE.txt', license[song.license]['text'])

    logging.info('zip file created name: [%s] at path: [%s]' % (archive_file_name, archive_file_path))
    archive.close()

    with File(open(archive_file_path, 'rb')) as f:
        response = HttpResponse(f.chunks())

    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = 'attachment; filename=%s' % archive_file_name

    logging.info('clean up temporary download directory [%s]' % temp_download_dir)

    rmtree(temp_download_dir)

    return response
