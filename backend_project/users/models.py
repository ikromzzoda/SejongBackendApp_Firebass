import fireo
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

    username      = TextField(required=True, unique=True)
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
    
    VERIFICATION_CHOICES = (
        ('Pending', 'Pending'),   # Только зарегистрировался, ждет проверки
        ('Approved', 'Approved'), # Админ подтвердил
        ('Rejected', 'Rejected'), # Админ отклонил
    )
    verification_status = TextField(choices=VERIFICATION_CHOICES, default='Pending')

    class Meta:
        collection_name = 'users'


class Group(Model):
    name       = TextField(required=True)
    created_at = DateTime(auto=True)

    class Meta:
        collection_name = 'groups'


class BlacklistedToken(Model):
    # Document ID = JTI, поэтому поиск O(1) без query-сканирования
    created_at = DateTime(auto=True)

    class Meta:
        collection_name = 'blacklisted_tokens'
