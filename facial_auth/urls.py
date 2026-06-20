from django.urls import path
from .views import EnrollFaceView, VerifyFaceView

urlpatterns = [
    path('enroll/', EnrollFaceView.as_view(), name='face_enroll'),
    path('verify/', VerifyFaceView.as_view(), name='face_verify'),
]
