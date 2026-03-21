def publish_user_registered(*, user_id: int, email: str, verification_required: bool) -> None:
    # Contract hook for post-commit side effects such as verification email dispatch.
    return None
