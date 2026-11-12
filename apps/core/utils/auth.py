def is_admin(user) -> bool:
    return (
        getattr(user, "role", None) == "admin"
        or user.is_staff
        or user.is_superuser
    )