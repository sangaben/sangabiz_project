from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Sum
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
import json
import os
from .models import Song, Genre, Playlist, UserProfile, SongPlay, SongDownload, Artist
from .forms import SongUploadForm

# Authentication Views
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_artist = request.POST.get('is_artist') == 'on'
        artist_name = request.POST.get('artist_name', '')
        bio = request.POST.get('bio', '')
        genre_id = request.POST.get('genre')
        website = request.POST.get('website', '')

        # Basic validation
        errors = []
        
        if not username or not email or not password1:
            errors.append('All required fields must be filled.')
        
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        # Artist-specific validation
        if is_artist:
            if not artist_name:
                errors.append('Artist name is required when signing up as an artist.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'signup.html')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # Update user profile
            profile = user.userprofile
            if is_artist:
                profile.user_type = 'artist'
                profile.save()
                
                # Create artist profile
                artist_data = {
                    'user': user,
                    'name': artist_name,
                    'bio': bio,
                    'website': website if website else None
                }
                
                # Add genre if provided and exists
                if genre_id:
                    try:
                        genre = Genre.objects.get(id=genre_id)
                        artist_data['genre'] = genre
                    except Genre.DoesNotExist:
                        # Continue without genre if it doesn't exist
                        pass
                
                Artist.objects.create(**artist_data)
                messages.success(request, 'Artist account created successfully!')
            else:
                messages.success(request, 'Account created successfully!')
            
            # Login user and redirect
            login(request, user)
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            # If user was created but failed later, delete it
            if 'user' in locals():
                user.delete()
    
    return render(request, 'signup.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('home')

def home(request):
    # Get featured songs (most played)
    featured_songs = Song.objects.all().order_by('-plays')[:8]
    
    # Get most played songs for charts
    most_played = Song.objects.all().order_by('-plays')[:5]
    most_downloaded = Song.objects.all().order_by('-downloads')[:5]
    
    # Get genres with song counts
    genres = Genre.objects.annotate(song_count=Count('song'))
    
    # Get total stats
    total_songs = Song.objects.count()
    total_plays = Song.objects.aggregate(total=Sum('plays'))['total'] or 0
    total_downloads = Song.objects.aggregate(total=Sum('downloads'))['total'] or 0
    
    # Get recent plays for authenticated users
    recent_plays = []
    if request.user.is_authenticated:
        recent_plays = SongPlay.objects.filter(user=request.user).select_related('song').order_by('-played_at')[:5]
    
    context = {
        'featured_songs': featured_songs,
        'most_played': most_played,
        'most_downloaded': most_downloaded,
        'genres': genres,
        'total_songs': total_songs,
        'total_plays': total_plays,
        'total_downloads': total_downloads,
        'recent_plays': recent_plays,
    }
    return render(request, 'home.html', context)
def discover(request):
    songs = Song.objects.all().order_by('-upload_date')
    genres = Genre.objects.all()
    
    context = {
        'songs': songs,
        'genres': genres,
    }
    return render(request, 'discover.html', context)

@login_required
def library(request):
    user_profile = UserProfile.objects.get(user=request.user)
    liked_songs = user_profile.liked_songs.all()
    playlists = Playlist.objects.filter(user=request.user)
    
    context = {
        'liked_songs': liked_songs,
        'playlists': playlists,
    }
    return render(request, 'library.html', context)

@login_required
def playlists(request):
    playlists = Playlist.objects.filter(user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Playlist.objects.create(name=name, user=request.user)
            messages.success(request, 'Playlist created successfully!')
            return redirect('playlists')
    
    context = {
        'playlists': playlists,
    }
    return render(request, 'playlists.html', context)

@login_required
def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        if song_id:
            song = get_object_or_404(Song, id=song_id)
            playlist.songs.add(song)
            messages.success(request, 'Song added to playlist!')
    
    context = {
        'playlist': playlist,
    }
    return render(request, 'playlist_detail.html', context)

def genres(request):
    genres = Genre.objects.all()
    
    context = {
        'genres': genres,
    }
    return render(request, 'genres.html', context)

def genre_songs(request, genre_id):
    genre = get_object_or_404(Genre, id=genre_id)
    songs = Song.objects.filter(genre=genre)
    
    context = {
        'genre': genre,
        'songs': songs,
    }
    return render(request, 'genre_songs.html', context)

# Song Actions
@csrf_exempt
def play_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    
    # Increment play count
    song.increment_plays()
    
    # Record play in SongPlay model
    SongPlay.objects.create(
        song=song,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request)
    )
    
    return JsonResponse({
        'id': song.id,
        'title': song.title,
        'artist': song.artist.name,
        'cover': song.cover_image.url if song.cover_image else '/static/images/default-cover.jpg',
        'audio': song.audio_file.url,
        'duration': song.duration,
        'plays': song.plays
    })

@login_required
def like_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    user_profile = UserProfile.objects.get(user=request.user)
    
    if song in user_profile.liked_songs.all():
        user_profile.liked_songs.remove(song)
        liked = False
    else:
        user_profile.liked_songs.add(song)
        liked = True
    
    return JsonResponse({'liked': liked})

def search(request):
    query = request.GET.get('q', '')
    songs = Song.objects.filter(
        title__icontains=query, 
        is_approved=True
    ) | Song.objects.filter(
        artist__name__icontains=query
    )
    
    context = {
        'songs': songs,
        'query': query,
    }
    return render(request, 'search.html', context)

@login_required
def download_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    
    # Increment download count
    song.increment_downloads()
    
    # Record download in SongDownload model
    SongDownload.objects.create(
        song=song,
        user=request.user,
        ip_address=get_client_ip(request)
    )
    
    # Serve the file for download
    file_path = song.audio_file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="audio/mpeg")
            response['Content-Disposition'] = f'attachment; filename="{song.title} - {song.artist.name}.mp3"'
            return response
    else:
        return JsonResponse({'error': 'File not found'}, status=404)

@login_required
def upload_music(request):
    # Check if user is an artist
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_artist:
        messages.error(request, "You need to be an artist to upload music.")
        return redirect('discover')
    
    try:
        artist_profile = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        messages.error(request, "Artist profile not found.")
        return redirect('discover')
    
    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.artist = artist_profile
            song.plays = 0
            song.downloads = 0
            song.is_approved = False
            
            song.save()
            messages.success(request, "Your song has been uploaded successfully and is pending review!")
            return redirect('my_uploads')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SongUploadForm()
    
    # Get all genres to pass to template
    genres = Genre.objects.all()
    
    context = {
        'form': form,
        'genres': genres,  # Add this line
    }
    return render(request, 'upload_music.html', context)

@login_required
def my_uploads(request):
    # Check if user is an artist
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_artist:
        messages.error(request, "You need to be an artist to view uploads.")
        return redirect('discover')
    
    try:
        artist_profile = Artist.objects.get(user=request.user)
        songs = Song.objects.filter(artist=artist_profile).order_by('-upload_date')
    except Artist.DoesNotExist:
        messages.error(request, "Artist profile not found.")
        songs = []
    
    context = {
        'songs': songs,
    }
    return render(request, 'my_uploads.html', context)

@login_required
def artist_dashboard(request):
    # Check if user is an artist
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_artist:
        messages.error(request, "You need to be an artist to access the dashboard.")
        return redirect('discover')
    
    try:
        artist_profile = Artist.objects.get(user=request.user)
        songs = Song.objects.filter(artist=artist_profile)
        
        # Calculate stats
        total_plays = songs.aggregate(total=Sum('plays'))['total'] or 0
        total_downloads = songs.aggregate(total=Sum('downloads'))['total'] or 0
        total_songs = songs.count()
        
        # Recent plays (last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        recent_plays = SongPlay.objects.filter(
            song__artist=artist_profile,
            played_at__gte=week_ago
        ).count()
        
    except Artist.DoesNotExist:
        messages.error(request, "Artist profile not found.")
        return redirect('discover')
    
    context = {
        'artist': artist_profile,
        'total_plays': total_plays,
        'total_downloads': total_downloads,
        'total_songs': total_songs,
        'recent_plays': recent_plays,
        'songs': songs,
    }
    return render(request, 'artist_dashboard.html', context)

# Analytics Views
@login_required
def song_analytics(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    
    # Check if user owns the song
    if not request.user.userprofile.is_artist or song.artist.user != request.user:
        messages.error(request, "You don't have permission to view these analytics.")
        return redirect('my_uploads')
    
    # Get play history (last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_plays = SongPlay.objects.filter(song=song, played_at__gte=thirty_days_ago)
    
    # Get download history
    recent_downloads = SongDownload.objects.filter(song=song, downloaded_at__gte=thirty_days_ago)
    
    context = {
        'song': song,
        'recent_plays': recent_plays,
        'recent_downloads': recent_downloads,
        'total_plays': song.plays,
        'total_downloads': song.downloads,
    }
    return render(request, 'analytics/song_analytics.html', context)

@login_required
def top_songs(request):
    # Get top played songs
    top_played = Song.objects.filter(is_approved=True).order_by('-plays')[:10]
    
    # Get top downloaded songs
    top_downloaded = Song.objects.filter(is_approved=True).order_by('-downloads')[:10]
    
    context = {
        'top_played': top_played,
        'top_downloaded': top_downloaded,
    }
    return render(request, 'analytics/top_songs.html', context)

# Utility Functions
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_song_stats(request, song_id):
    """Get current song statistics"""
    song = get_object_or_404(Song, id=song_id)
    return JsonResponse({
        'plays': song.plays,
        'downloads': song.downloads
    })

# API Views
@csrf_exempt
@login_required
def add_to_playlist(request, song_id):
    if request.method == 'POST':
        song = get_object_or_404(Song, id=song_id)
        playlist_id = request.POST.get('playlist_id')
        
        if playlist_id:
            playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
            playlist.songs.add(song)
            return JsonResponse({'success': True})
        
    return JsonResponse({'success': False})

@login_required
def remove_from_playlist(request, playlist_id, song_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    song = get_object_or_404(Song, id=song_id)
    
    playlist.songs.remove(song)
    messages.success(request, 'Song removed from playlist!')
    return redirect('playlist_detail', playlist_id=playlist_id)

@login_required
def delete_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist.delete()
    messages.success(request, 'Playlist deleted!')
    return redirect('playlists')

# Error Handlers
def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)
