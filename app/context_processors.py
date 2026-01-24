from .models import Message

def unread_message_count(request):
    if not request.user.is_authenticated:
        return {}

    count = Message.objects.filter(
        receiver=request.user,
        is_read=False
    ).count()

    return {
        "unread_message_count": count
    }