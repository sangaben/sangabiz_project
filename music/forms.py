from django import forms
from .models import Song, Genre

class SongUploadForm(forms.ModelForm):
    duration_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Minutes',
            'min': '0',
            'max': '59'
        })
    )
    duration_seconds = forms.IntegerField(
        min_value=0,
        max_value=59,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Seconds',
            'min': '0',
            'max': '59'
        })
    )

    class Meta:
        model = Song
        fields = ['title', 'genre', 'audio_file', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter song title'
            }),
            'genre': forms.Select(attrs={
                'class': 'form-select'
            }),
            'audio_file': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.mp3,.wav,.m4a,.ogg'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'file-input', 
                'accept': '.jpg,.jpeg,.png,.webp'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['genre'].queryset = Genre.objects.all()
        self.fields['genre'].empty_label = "Select Genre"
    
    def clean(self):
        cleaned_data = super().clean()
        minutes = cleaned_data.get('duration_minutes')
        seconds = cleaned_data.get('duration_seconds')
        
        if minutes is not None and seconds is not None:
            total_seconds = (minutes * 60) + seconds
            if total_seconds <= 0:
                raise forms.ValidationError("Duration must be greater than 0 seconds.")
            cleaned_data['duration'] = total_seconds
        
        return cleaned_data
    
    def save(self, commit=True):
        song = super().save(commit=False)
        minutes = self.cleaned_data.get('duration_minutes')
        seconds = self.cleaned_data.get('duration_seconds')
        
        if minutes is not None and seconds is not None:
            song.duration = (minutes * 60) + seconds
        
        if commit:
            song.save()
        return song
    
    # ... keep your existing clean_audio_file and clean_cover_image methods ...
    
    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            # Validate file size (50MB)
            if audio_file.size > 50 * 1024 * 1024:
                raise forms.ValidationError("Audio file size must be less than 50MB.")
            
            # Validate file type
            allowed_types = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/ogg']
            if audio_file.content_type not in allowed_types:
                raise forms.ValidationError("Please upload a valid audio file (MP3, WAV, M4A, or OGG).")
        
        return audio_file
    
    def clean_cover_image(self):
        cover_image = self.cleaned_data.get('cover_image')
        if cover_image:
            # Validate file size (10MB)
            if cover_image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Cover image size must be less than 10MB.")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if cover_image.content_type not in allowed_types:
                raise forms.ValidationError("Please upload a valid image file (JPG, PNG, or WebP).")
        
        return cover_image