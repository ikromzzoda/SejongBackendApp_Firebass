import getpass
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from users.models import User


class Command(BaseCommand):
    help = 'Создаёт первого администратора системы'

    def handle(self, *args, **kwargs):
        existing = list(User.collection.filter('status', '==', 'Admin').fetch(1))
        if existing:
            self.stdout.write(self.style.WARNING('Администратор уже существует. Команда отменена.'))
            return

        self.stdout.write('Создание первого администратора')

        username = input('Username: ').strip()
        if not username:
            self.stdout.write(self.style.ERROR('Username не может быть пустым.'))
            return

        taken = list(User.collection.filter('username', '==', username).fetch(1))
        if taken:
            self.stdout.write(self.style.ERROR(f'Пользователь "{username}" уже существует.'))
            return

        fullname = input('Полное имя (необязательно): ').strip()
        email = input('Email: ').strip()
        phone = input('Номер телефона (+992XXXXXXXXX): ').strip()

        password = getpass.getpass('Пароль: ')
        password_confirm = getpass.getpass('Подтвердите пароль: ')
        if password != password_confirm:
            self.stdout.write(self.style.ERROR('Пароли не совпадают.'))
            return

        user = User()
        user.username = username
        user.fullname = fullname
        user.email = email
        user.phone_number = phone
        user.password = make_password(password)
        user.status = 'Admin'
        user.verification_status = 'Approved'
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Администратор "{username}" успешно создан.'))
