from fireo.models import Model
from fireo.fields import TextField, DateTime


DEFAULT_AVATAR = "https://drive.google.com/uc?id=1FCfMdEvghunhDuKd1PWQqty_ZPZelqim"


class User(Model):

    STATUS_CHOICES = (
        ('Student', 'Student'),
        ('Teacher', 'Teacher'),
        ('Admin',   'Admin'),
        ('Guest',   'Guest'),
    )

    username      = TextField(required=True)
    password      = TextField(required=True)
    fullname      = TextField()
    email         = TextField()
    phone_number  = TextField()
    date_of_birth = TextField()
    status        = TextField(default='Guest')
    group         = TextField()
    avatar        = TextField(default=DEFAULT_AVATAR)
    avatar_id     = TextField()
    date_joined   = DateTime(auto=True)
    device_token   = TextField()

    VERIFICATION_CHOICES = (
        ('Pending',  'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )
    verification_status  = TextField(default='Pending')
    refresh_token_jti    = TextField()

    class Meta:
        collection_name = 'users'


class BlacklistedToken(Model):
    # Document ID = JTI, поэтому поиск O(1) без query-сканирования
    created_at = DateTime(auto=True)

    class Meta:
        collection_name = 'blacklisted_tokens'
