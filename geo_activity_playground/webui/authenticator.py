import functools
from typing import Callable

from flask import flash
from flask import redirect
from flask import session
from flask import url_for

from geo_activity_playground.core.config import Config


class Authenticator:
    def __init__(self, config: Config) -> None:
        self._config = config

    def is_authenticated(self) -> bool:
        print(
            f"Password={self._config.upload_password}, Session={session.get('is_authenticated', False)}"
        )
        return not self._config.upload_password or session.get(
            "is_authenticated", False
        )

    def authenticate(self, password: str) -> None:
        if password == self._config.upload_password:
            session["is_authenticated"] = True
            session.permanent = True
            flash("Login successful.", category="success")
        else:
            flash("Incorrect password.", category="warning")

    def logout(self) -> None:
        session["is_authenticated"] = False
        flash("Logout successful.", category="success")


def needs_authentication(authenticator: Authenticator) -> Callable:
    def decorator(route: Callable) -> Callable:
        @functools.wraps(route)
        def wrapped_route(*args, **kwargs):
            if authenticator.is_authenticated():
                return route(*args, **kwargs)
            else:
                flash("You need to be logged in to view that site.", category="Warning")
                return redirect(url_for("auth.index"))

        return wrapped_route

    return decorator