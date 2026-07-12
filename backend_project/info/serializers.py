from rest_framework import serializers

VALID_CLASSROOMS = (301, 303, 306, 307, 308)
VALID_STATUSES = ('Guest', 'Student', 'Teacher', 'Admin')


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

class ScheduleSerializer(serializers.Serializer):
    id = serializers.CharField()
    day = serializers.IntegerField(min_value=0, max_value=6, help_text="0 = Monday ... 6 = Sunday")
    day_name = serializers.CharField()
    start_time = serializers.CharField(help_text="HH:MM")
    end_time = serializers.CharField(help_text="HH:MM")
    classroom = serializers.ChoiceField(choices=VALID_CLASSROOMS)
    group_name = serializers.CharField()
    teacher_name = serializers.CharField()
    book = serializers.IntegerField(min_value=1, max_value=8)
    created_at = serializers.CharField()


class AdminCreateScheduleRequestSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6, help_text="0 = Monday ... 6 = Sunday")
    start_time = serializers.CharField(help_text="HH:MM")
    end_time = serializers.CharField(help_text="HH:MM")
    classroom = serializers.ChoiceField(choices=VALID_CLASSROOMS)
    group_name = serializers.CharField()
    teacher_name = serializers.CharField(help_text="ФИО учителя (должен иметь статус Teacher)")
    book = serializers.IntegerField(min_value=1, max_value=8)


class AdminEditScheduleRequestSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6, required=False)
    start_time = serializers.CharField(required=False, help_text="HH:MM")
    end_time = serializers.CharField(required=False, help_text="HH:MM")
    classroom = serializers.ChoiceField(choices=VALID_CLASSROOMS, required=False)
    group_name = serializers.CharField(required=False)
    teacher_name = serializers.CharField(required=False)
    book = serializers.IntegerField(min_value=1, max_value=8, required=False)


class AdminCreateScheduleResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    schedule = ScheduleSerializer()


class AdminEditScheduleResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    schedule = ScheduleSerializer()


class AdminGetScheduleResponseSerializer(serializers.Serializer):
    schedule = ScheduleSerializer()


class ScheduleLessonSerializer(serializers.Serializer):
    id = serializers.CharField(help_text="ID записи расписания")
    day = serializers.IntegerField(min_value=0, max_value=6, help_text="0 = Monday ... 6 = Sunday")
    day_name = serializers.CharField()
    start_time = serializers.CharField(help_text="HH:MM")
    end_time = serializers.CharField(help_text="HH:MM")
    classroom = serializers.ChoiceField(choices=VALID_CLASSROOMS)


class GroupedScheduleSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    group_name = serializers.CharField()
    teacher_name = serializers.CharField()
    book = serializers.IntegerField(min_value=1, max_value=8)
    lessons = ScheduleLessonSerializer(many=True)


class AdminListSchedulesResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Кол-во групп")
    schedules = GroupedScheduleSerializer(many=True)


class GroupScheduleResponseSerializer(serializers.Serializer):
    group_name = serializers.CharField()
    schedules = ScheduleSerializer(many=True)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationImageSerializer(serializers.Serializer):
    file_id = serializers.CharField()
    url = serializers.CharField()


class NotificationSerializer(serializers.Serializer):
    id = serializers.CharField()
    title_taj = serializers.CharField()
    title_rus = serializers.CharField()
    title_eng = serializers.CharField()
    title_kor = serializers.CharField()
    content_taj = serializers.CharField()
    content_rus = serializers.CharField()
    content_eng = serializers.CharField()
    content_kor = serializers.CharField()
    image_url = serializers.CharField()
    images = NotificationImageSerializer(many=True)
    target_statuses = serializers.ListField(child=serializers.ChoiceField(choices=VALID_STATUSES))
    created_at = serializers.CharField()


class AdminCreateNotificationRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    image_url = serializers.CharField(required=False)
    target_statuses = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_STATUSES),
        help_text="Кому отправлять push-уведомление",
    )
    images = serializers.ListField(
        child=serializers.FileField(), required=False,
        help_text="До 10 файлов, JPEG/PNG/WEBP, до 2 МБ каждый",
    )


class AdminEditNotificationRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    image_url = serializers.CharField(required=False)
    target_statuses = serializers.ListField(child=serializers.ChoiceField(choices=VALID_STATUSES), required=False)
    images = serializers.ListField(
        child=serializers.FileField(), required=False,
        help_text="Заменяет все текущие изображения (до 10 файлов, JPEG/PNG/WEBP, до 2 МБ каждый)",
    )


class AdminCreateNotificationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    notification = NotificationSerializer()


class AdminEditNotificationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    notification = NotificationSerializer()


class AdminGetNotificationResponseSerializer(serializers.Serializer):
    notification = NotificationSerializer()


class ListNotificationsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    notifications = NotificationSerializer(many=True)


# ---------------------------------------------------------------------------
# Privacy Policy
# ---------------------------------------------------------------------------

class PrivacySectionSerializer(serializers.Serializer):
    id = serializers.CharField()
    title_taj = serializers.CharField()
    title_rus = serializers.CharField()
    title_eng = serializers.CharField()
    title_kor = serializers.CharField()
    content_taj = serializers.CharField()
    content_rus = serializers.CharField()
    content_eng = serializers.CharField()
    content_kor = serializers.CharField()
    order = serializers.IntegerField()
    updated_at = serializers.CharField()


class AdminCreatePrivacySectionRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    order = serializers.IntegerField(required=False, default=0)


class AdminEditPrivacySectionRequestSerializer(serializers.Serializer):
    title_taj = serializers.CharField(required=False)
    title_rus = serializers.CharField(required=False)
    title_eng = serializers.CharField(required=False)
    title_kor = serializers.CharField(required=False)
    content_taj = serializers.CharField(required=False)
    content_rus = serializers.CharField(required=False)
    content_eng = serializers.CharField(required=False)
    content_kor = serializers.CharField(required=False)
    order = serializers.IntegerField(required=False)


class AdminCreatePrivacySectionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    section = PrivacySectionSerializer()


class AdminEditPrivacySectionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())
    section = PrivacySectionSerializer()


class ListPrivacySectionsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    sections = PrivacySectionSerializer(many=True)
