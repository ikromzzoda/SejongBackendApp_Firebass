from rest_framework import serializers

STATUS_CHOICES = ('Student', 'Teacher', 'Admin', 'Guest')
VERIFICATION_CHOICES = ('Pending', 'Approved', 'Rejected')


class GroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class GroupMemberSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    fullname = serializers.CharField()
    email = serializers.CharField()
    phone_number = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    verification_status = serializers.ChoiceField(choices=VERIFICATION_CHOICES)
    group = serializers.CharField()


class AdminListGroupsResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    has_more = serializers.BooleanField()
    groups = GroupSerializer(many=True)


class AdminCreateGroupRequestSerializer(serializers.Serializer):
    name = serializers.CharField()


class AdminCreateGroupResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    group = GroupSerializer()


class AdminRenameGroupRequestSerializer(serializers.Serializer):
    name = serializers.CharField()


class AdminListGroupMembersResponseSerializer(serializers.Serializer):
    group = GroupSerializer()
    total = serializers.IntegerField()
    members = GroupMemberSerializer(many=True)


class AdminAssignGroupRequestSerializer(serializers.Serializer):
    group_id = serializers.CharField()


class AdminGroupMemberActionResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = GroupMemberSerializer()
