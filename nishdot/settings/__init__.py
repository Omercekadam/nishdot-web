# ==============================================================================
# Nishdot Web Platform — Settings Package Initializer
# ==============================================================================
#
# Bu dosya, DJANGO_SETTINGS_MODULE ortam değişkenine göre doğru ayar
# dosyasının yüklenmesini sağlar.
#
# Çalışma mantığı:
#   1. manage.py veya wsgi.py, DJANGO_SETTINGS_MODULE'ü ayarlar
#   2. Django bu paketi import eder
#   3. İlgili modül (development.py veya production.py) yüklenir
#
# Eğer DJANGO_SETTINGS_MODULE tanımlı değilse, güvenli tarafta kalarak
# development ayarlarına düşer.
# ==============================================================================
