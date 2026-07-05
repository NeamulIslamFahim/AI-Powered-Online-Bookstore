def build_pagination(*, total: int, page: int, limit: int) -> dict:
    total_pages = total // limit + (1 if total % limit else 0)
    return {
        "total": total,
        "page": page,
        "pages": max(total_pages, 1),
        "limit": limit,
        "total_pages": max(total_pages, 1),
    }
