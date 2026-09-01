"""
auth.py - session-based authentication helpers.

Login state is kept in Flask's signed session cookie (server-side secret,
tamper-proof, no separate token store needed). Two decorators are exposed:

  @login_required   -> any logged-in user (admin or subadmin)
  @admin_required   -> logged-in user whose role is 'admin'
"""

import functools

from flask import session, redirect, url_for, flash, request


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("That page is restricted to admin users.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped