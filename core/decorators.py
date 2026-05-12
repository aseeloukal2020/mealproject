# للتحقق من الموافقة على المستخدم 
# core/decorators.py
from functools import wraps
from django.shortcuts import redirect


def approved_required(view_func):
    """
    يتحقق إن المستخدم مسجل دخول + معتمد من الأدمن.
    لو مش معتمد، يوديه لصفحة "بانتظار الموافقة".
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not request.user.is_approved and not request.user.is_superuser:
            return redirect('pending_approval')

        return view_func(request, *args, **kwargs)

    return wrapper