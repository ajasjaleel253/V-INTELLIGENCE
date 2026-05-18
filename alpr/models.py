from django.db import models

class VideoUpload(models.Model):
    video_file = models.FileField(upload_to='videos/')
    processed_video = models.FileField(upload_to='processed_videos/', null=True, blank=True)
    csv_file = models.FileField(upload_to='csvs/', null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def status(self):
        if self.is_processed:
            return "Analysis Complete"
        return "Processing..."

    def __str__(self):
        return f"Video {self.id}"
    

