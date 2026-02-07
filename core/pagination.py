"""
Pagination classes for OIUEEI API.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination with configurable page size.

    - Default page size: 20
    - Max page size: 100 (prevents DoS via large page requests)
    - Client can request specific page size via 'page_size' query param
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
