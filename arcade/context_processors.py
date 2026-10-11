from .models import Competition


def arcade_visible(request):
    """Navbar her sayfada var; oyun bağlantısı yalnızca oyun açıkken görünür."""
    return {"arcade_visible": Competition.current() is not None}
