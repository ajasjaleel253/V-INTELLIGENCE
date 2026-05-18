import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import cv2

# Load ESRGAN model ONCE
ESRGAN_MODEL_URL = "https://tfhub.dev/captain-pool/esrgan-tf2/1"
esrgan_model = hub.load(ESRGAN_MODEL_URL)


def upscale_plate_opencv(cropped_plate):
    """
    Takes OpenCV BGR image → returns upscaled OpenCV BGR image
    """

    # Convert BGR → RGB
    img_rgb = cv2.cvtColor(cropped_plate, cv2.COLOR_BGR2RGB)

    # Make dimensions divisible by 4
    h, w, _ = img_rgb.shape
    h = (h // 4) * 4
    w = (w // 4) * 4
    img_rgb = img_rgb[:h, :w]

    # Convert to Tensor
    img_tensor = tf.convert_to_tensor(img_rgb, dtype=tf.float32)
    img_tensor = tf.expand_dims(img_tensor, axis=0)

    # Super Resolution
    sr_tensor = esrgan_model(img_tensor)
    sr_tensor = tf.squeeze(sr_tensor)

    # Normalize and convert back to uint8
    sr_image = tf.clip_by_value(sr_tensor, 0, 255)
    sr_image = tf.cast(sr_image, tf.uint8).numpy()

    # RGB → BGR (for OpenCV + EasyOCR)
    sr_bgr = cv2.cvtColor(sr_image, cv2.COLOR_RGB2BGR)

    return sr_bgr
