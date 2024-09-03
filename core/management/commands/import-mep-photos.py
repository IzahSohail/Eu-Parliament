from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import MEP
import os

class Command(BaseCommand):
    help = 'Update MEP instances with photos from the mep_photos folder'

    def handle(self, *args, **kwargs):
        photos_path = os.path.join(settings.BASE_DIR, 'mep_photos')
        if not os.path.exists(photos_path):
            self.stderr.write(f"The folder {photos_path} does not exist.")
            return

        for filename in os.listdir(photos_path):
            if filename.endswith(('.jpg')):
                mep_id = os.path.splitext(filename)[0]
                mep_id = int(mep_id)
                mep_instance = MEP.objects.get(mep_id=mep_id)

                with open(os.path.join(photos_path, filename), 'rb') as photo_file:
                    mep_instance.photo = photo_file.read()
                    mep_instance.save()
 
        self.stdout.write(f"Successfully updated MEP photos.")