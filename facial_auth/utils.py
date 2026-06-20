import base64
import logging
import numpy as np
from django.conf import settings
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def get_cipher():
    return Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)


def encrypt_embedding(embedding: list) -> bytes:
    data = np.array(embedding).tobytes()
    return get_cipher().encrypt(data)


def decrypt_embedding(encrypted: bytes) -> np.ndarray:
    data = get_cipher().decrypt(encrypted)
    return np.frombuffer(data, dtype=np.float64)


def decode_image_from_base64(b64_string: str):
    import cv2
    try:
        logger.debug("Face image payload received: %s", bool(b64_string))
        img_data = base64.b64decode(b64_string.split(',')[-1])
        arr = np.frombuffer(img_data, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        logger.debug("Decoded face image shape: %s", None if image is None else image.shape)
        return image
    except Exception:
        logger.exception("Failed to decode face image from base64 payload")
        return None


def _check_image_quality(image_array: np.ndarray, face_location: tuple) -> str | None:
    """Return an error string if quality checks fail, else None."""
    import cv2
    h, w = image_array.shape[:2]
    top, right, bottom, left = face_location
    face_h, face_w = bottom - top, right - left

    if (face_h * face_w) / (h * w) < 0.20:
        return 'Face too small. Move closer to the camera.'

    cx, cy = (left + right) / 2, (top + bottom) / 2
    if abs(cx / w - 0.5) > 0.30 or abs(cy / h - 0.5) > 0.35:
        return 'Face not centred. Please centre your face in the frame.'

    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    face_gray = gray[top:bottom, left:right]

    if face_gray.mean() < 50:
        return 'Image too dark. Improve lighting and try again.'

    if cv2.Laplacian(face_gray, cv2.CV_64F).var() < 60:
        return 'Image too blurry. Hold the camera steady and try again.'

    return None


def get_face_embedding(image_array: np.ndarray):
    if settings.DEBUG:
        logger.warning("DEBUG face auth bypass: using test embedding")
        return np.zeros(128, dtype=np.float64), None

    import face_recognition
    logger.debug("Face recognition input shape: %s", getattr(image_array, "shape", None))
    rgb = image_array[:, :, ::-1].copy()  # BGR to RGB (copy avoids negative-stride issue)
    locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=1, model='hog')
    logger.debug("Detected face locations: %s", locations)

    if not locations:
        return None, 'No face detected. Ensure good lighting and look directly at the camera.'
    if len(locations) > 1:
        return None, 'Multiple faces detected. Please use a single face in the frame.'

    quality_error = _check_image_quality(image_array, locations[0])
    if quality_error:
        logger.debug("Face image quality rejected: %s", quality_error)
        return None, quality_error

    encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    logger.debug("Face encoding count: %s", len(encodings))
    if not encodings:
        return None, 'Unable to encode face. Please try again with better lighting and positioning.'

    return encodings[0], None


def compare_faces(stored_embedding: bytes, live_embedding: np.ndarray, tolerance: float = 0.5) -> bool:
    stored = decrypt_embedding(stored_embedding)
    distance = np.linalg.norm(stored - live_embedding)
    return distance <= tolerance
