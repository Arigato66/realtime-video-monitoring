import os

# Get the absolute path to the app directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -------------------------------------- profile_detection ---------------------------------------
detect_frontal_face = os.path.join(APP_DIR, 'services', 'profile_detection', 'haarcascades', 'haarcascade_frontalface_alt.xml')
detect_perfil_face = os.path.join(APP_DIR, 'services', 'profile_detection', 'haarcascades', 'haarcascade_profileface.xml')

# -------------------------------------- emotion_detection ---------------------------------------
# modelo de deteccion de emociones
path_model = os.path.join(APP_DIR, 'services', 'emotion_detection', 'Modelos', 'model_dropout.hdf5')
# Parametros del modelo, la imagen se debe convertir a una de tamaño 48x48 en escala de grises
w,h = 48,48
rgb = False
labels = ['angry','disgust','fear','happy','neutral','sad','surprise']