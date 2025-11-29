from django.shortcuts import redirect
from django.urls import reverse

class GroupRequiredMiddleware:
    """
    ログイン後、グループ未設定ユーザーは強制的に group/create へリダイレクトする
    """
    EXEMPT_URLS = [
        'login',
        'logout',
        'signup',
        'create_group',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # 未ログインはスルー
        if not user.is_authenticated:
            return self.get_response(request)

        # 静的ファイル等はスルー
        if request.path.startswith('/static/'):
            return self.get_response(request)

        # 招待リンク経由のサインアップはスルー
        if "invite=" in request.get_full_path():
            return self.get_response(request)

        # 例外URLはスルー
        for exempt in self.EXEMPT_URLS:
            if request.path.startswith(reverse(exempt)):
                return self.get_response(request)

        # ★ ここが本体：グループがないなら group/create へ強制
        if user.group is None:
            return redirect('create_group')

        # それ以外は正常
        return self.get_response(request)