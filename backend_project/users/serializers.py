from rest_framework import serializers

STATUS_CHOICES = ('Student', 'Teacher', 'Admin', 'Guest')
VERIFICATION_CHOICES = ('Pending', 'Approved', 'Rejected')


# ---------------------------------------------------------------------------
# Response objects
# ---------------------------------------------------------------------------

class UserSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    fullname = serializers.CharField()
    email = serializers.CharField()
    phone_number = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES)
    group_id = serializers.CharField()
    group = serializers.CharField()
    avatar = serializers.CharField()
    date_joined = serializers.CharField()


class UserDetailSerializer(UserSerializer):
    date_of_birth = serializers.CharField()
    device_token = serializers.CharField()


class ProfileSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    fullname = serializers.CharField()
    email = serializers.CharField()
    phone_number = serializers.CharField()
    date_of_birth = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES)
    group_id = serializers.CharField()
    avatar = serializers.CharField()
    date_joined = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES)
    avatar = serializers.CharField()
    fcm_topic = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token = serializers.CharField()
    refresh_token = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES)


class TokenRefreshResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refresh_token = serializers.CharField()


class VerifyResetCodeResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    reset_token = serializers.CharField()


class AdminListUsersResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    users = UserSerializer(many=True)


class AdminGetUserResponseSerializer(serializers.Serializer):
    user = UserDetailSerializer()


class AdminEditUserResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    user = UserSerializer()


class AdminVerifyUserResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()


class AdminSetStatusResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()


class AdminCreateUserResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()


class UpdateProfileResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    token = serializers.CharField()


class ChangeAvatarResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    avatar = serializers.CharField()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RegisterRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    email = serializers.CharField()
    phone_number = serializers.CharField(help_text="Формат: +992XXXXXXXXX")
    fullname = serializers.CharField(required=False)
    date_of_birth = serializers.CharField(required=False)
    avatar = serializers.FileField(required=False, help_text="JPEG/PNG/WEBP, до 3 МБ")


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    device_token = serializers.CharField()


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.CharField()


class VerifyResetCodeRequestSerializer(serializers.Serializer):
    email = serializers.CharField()
    code = serializers.CharField(help_text="6-значный код из письма")


class ResetPasswordRequestSerializer(serializers.Serializer):
    reset_token = serializers.CharField(help_text="Токен из ответа verify-code")
    new_password = serializers.CharField()


class UpdateProfileRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False, help_text="Формат: +992XXXXXXXXX")
    password = serializers.CharField(required=False)
    check_password = serializers.CharField(required=False, help_text="Текущий пароль — обязателен при смене пароля")


class ChangeAvatarRequestSerializer(serializers.Serializer):
    avatar = serializers.FileField(help_text="JPEG/PNG/WEBP, до 3 МБ")


class AdminEditUserRequestSerializer(serializers.Serializer):
    fullname = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    date_of_birth = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES, required=False)
    group_id = serializers.CharField(required=False)
    group = serializers.CharField(required=False, help_text="Имя группы (альтернатива group_id)")
    password = serializers.CharField(required=False)


class AdminVerifyUserRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=('approve', 'reject'))


class AdminSetStatusRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=STATUS_CHOICES)


class AdminCreateUserRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    email = serializers.CharField()
    phone_number = serializers.CharField()
    fullname = serializers.CharField(required=False)
    date_of_birth = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False, default='Student')
    group_id = serializers.CharField(required=False)
    group = serializers.CharField(required=False, help_text="Имя группы (альтернатива group_id)")
    avatar = serializers.CharField(required=False)


class BulkImportRequestSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Excel-файл (.xlsx) со списком студентов")
