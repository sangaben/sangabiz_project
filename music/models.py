from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

class Genre(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6c5ce7')  # Hex color
    
    def __str__(self):
        return self.name

class ArtistManager(models.Manager):
    def verified(self):
        return self.filter(is_verified=True)
    
    def with_stats(self):
        return self.annotate(
            total_songs=models.Count('songs'),
            total_plays=models.Sum('songs__plays'),
            total_downloads=models.Sum('songs__downloads')
        )

class Artist(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='artist_profile'
    )
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='artists/', blank=True, null=True)
    genre = models.ForeignKey('Genre', on_delete=models.SET_NULL, null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ArtistManager()
    
    class Meta:
        # Add unique constraint explicitly
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_artist_user')
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_plays(self):
        return sum(song.plays for song in self.songs.all())
    
    @property
    def total_downloads(self):
        return sum(song.downloads for song in self.songs.all())
    
    @property
    def total_songs(self):
        return self.songs.count()

class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='songs')
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    audio_file = models.FileField(
        upload_to='songs/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg'])]
    )
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    upload_date = models.DateTimeField(auto_now_add=True)
    plays = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=False)  # For moderation
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.title} - {self.artist.name}"
    
    def increment_plays(self):
        self.plays += 1
        self.save()
    
    def increment_downloads(self):
        self.downloads += 1
        self.save()
    
    @property
    def formatted_duration(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"

class Playlist(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    songs = models.ManyToManyField(Song, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='playlist_covers/', blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']

class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('listener', 'Listener'),
        ('artist', 'Artist'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='listener')
    favorite_genres = models.ManyToManyField(Genre, blank=True)
    liked_songs = models.ManyToManyField('Song', related_name='liked_by', blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username
    
    @property
    def is_artist(self):
        return self.user_type == 'artist'
    
    @property
    def artist_profile(self):
        if self.is_artist:
            try:
                return self.user.artist_profile
            except Artist.DoesNotExist:
                # Auto-correct if artist profile doesn't exist
                self.user_type = 'listener'
                self.save()
                return None
        return None

class SongPlay(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    played_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    duration_played = models.PositiveIntegerField(default=0)  # Seconds played
    
    class Meta:
        ordering = ['-played_at']

class SongDownload(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-downloaded_at']

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'song']
        ordering = ['-liked_at']

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='followers')
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'artist']
        ordering = ['-followed_at']

# FIXED Signal handlers - Use get_or_create to avoid duplicates
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except ObjectDoesNotExist:
        UserProfile.objects.get_or_create(user=instance)

# Safe utility function for creating artist profiles
def create_artist_profile(user, **kwargs):
    """
    Safely create an artist profile for a user
    Returns (artist, created) tuple
    """
    try:
        # Check if artist profile already exists
        if hasattr(user, 'artist_profile'):
            artist = user.artist_profile
            # Update existing artist with new data
            for key, value in kwargs.items():
                if hasattr(artist, key):
                    setattr(artist, key, value)
            artist.save()
            return artist, False
        else:
            # Create new artist profile
            artist = Artist.objects.create(user=user, **kwargs)
            # Update user profile
            profile = user.userprofile
            profile.user_type = 'artist'
            profile.save()
            return artist, True
    except Exception as e:
        print(f"Error creating artist profile: {e}")
        return None, False