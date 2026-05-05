"""
URL consistency tests to prevent 301 redirect issues.

These tests ensure all URL patterns follow the trailing slash convention
and that test client calls use consistent URLs.
"""

from django.test import SimpleTestCase, TestCase
from django.urls import get_resolver, reverse
from django.contrib.auth import get_user_model


User = get_user_model()


class URLTrailingSlashConsistencyTests(SimpleTestCase):
    """Verify all URL patterns end with trailing slashes to prevent 301 redirects."""

    def test_all_url_patterns_end_with_trailing_slash(self):
        """All URL patterns (except empty root paths) must end with /."""
        resolver = get_resolver()
        violations = []

        for pattern in resolver.url_patterns:
            self._check_pattern(pattern, violations)

        if violations:
            self.fail(
                f"The following URL patterns do not end with a trailing slash:\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nAll patterns must end with / to prevent 301 redirects."
            )

    def _check_pattern(self, pattern, violations, prefix=""):
        """Recursively check URL patterns for trailing slash compliance."""
        from django.urls.resolvers import RoutePattern, URLResolver

        if hasattr(pattern, "pattern"):
            route = str(pattern.pattern)

            # Skip empty root paths (path(""))
            # Skip regex patterns (Django admin internals, catch-alls)
            # Skip paths starting with ^ (regex patterns)
            if route and route != "" and not route.startswith("^"):
                # Skip Django admin internal patterns
                if "admin/" in route or route.startswith("^(?P<app_label>"):
                    return

                # Check if it's a concrete path (not a parameter-only path like "<int:pk>/")
                # Parameter paths should still end with /
                if not route.endswith("/"):
                    full_path = prefix + route
                    violations.append(full_path)

            # Recursively check included URLconfs
            if isinstance(pattern, URLResolver):
                new_prefix = prefix + route
                for sub_pattern in pattern.url_patterns:
                    self._check_pattern(sub_pattern, violations, new_prefix)

    def test_root_url_patterns_have_trailing_slashes(self):
        """Verify root URLconf patterns all end with /."""
        from config import urls

        violations = []
        for pattern in urls.urlpatterns:
            route = str(pattern.pattern)
            # Skip the debug catch-all pattern
            if route and not route.startswith("^") and not route.endswith("/"):
                violations.append(route)

        if violations:
            self.fail(
                f"Root URL patterns missing trailing slashes:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )

    def test_no_hardcoded_urls_without_trailing_slashes_in_tests(self):
        """Ensure test files don't use hardcoded URLs without trailing slashes."""
        import os
        import re
        from pathlib import Path

        test_dir = Path(__file__).parent.parent
        violations = []

        # Pattern to match self.client.get/post/put/delete with hardcoded URLs
        # that don't have trailing slashes
        pattern = re.compile(
            r'self\.client\.(get|post|put|delete)\(\s*["\'](/[^"\']*)["\']'
        )

        for test_file in test_dir.rglob("tests.py"):
            content = test_file.read_text()
            for match in pattern.finditer(content):
                url = match.group(2)
                # Skip URLs that end with /
                if not url.endswith("/"):
                    # Find line number
                    line_num = content[:match.start()].count("\n") + 1
                    violations.append(f"{test_file.relative_to(test_dir.parent)}:{line_num} - {url}")

        if violations:
            self.fail(
                f"The following test URLs are missing trailing slashes:\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nAll hardcoded URLs in tests must end with / to prevent 301 redirects."
            )


class RedirectBehaviorTests(TestCase):
    """Test that URLs without trailing slashes cause 301 redirects (the core issue)."""

    def test_url_without_trailing_slash_causes_301_redirect(self):
        """Verify that accessing URLs without trailing slash returns 301 redirect.
        
        This is the core issue from GitHub #26 - tests fail because they expect
        200/302/403/404 but get 301 instead when URL is missing trailing slash.
        """
        # Test a few key URLs without trailing slashes
        urls_without_slash = [
            '/settings',
            '/users',
            '/items',
            '/stock',
            '/receiving',
            '/distribution',
            '/reports',
        ]
        
        for url in urls_without_slash:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 301,
                f"Expected 301 redirect for '{url}' (missing trailing slash), "
                f"got {response.status_code}"
            )
            # Verify it redirects to the URL with trailing slash
            self.assertTrue(
                response.url.endswith('/'),
                f"Redirect URL '{response.url}' should end with trailing slash"
            )

    def test_url_with_trailing_slash_works_correctly(self):
        """Verify that URLs with trailing slashes work as expected (no 301)."""
        # Test that URLs with trailing slashes don't cause 301
        urls_with_slash = [
            '/settings/',
            '/users/',
            '/items/',
            '/stock/',
            '/receiving/',
            '/distribution/',
            '/reports/',
        ]
        
        for url in urls_with_slash:
            response = self.client.get(url)
            self.assertNotEqual(
                response.status_code, 301,
                f"URL '{url}' should NOT return 301 (it has trailing slash), "
                f"got {response.status_code}"
            )
            # Should be 302 (redirect to login) or 200/403 depending on auth
            self.assertIn(
                response.status_code, [200, 302, 403],
                f"URL '{url}' should return 200/302/403, got {response.status_code}"
            )

    def test_reverse_urls_have_trailing_slashes(self):
        """Verify that reverse() generates URLs with trailing slashes."""
        url_names = [
            'dashboard',
            'settings',
            'users:user_list',
            'items:item_list',
            'stock:stock_list',
            'receiving:receiving_list',
            'distribution:distribution_list',
            'reports:index',
        ]
        
        for url_name in url_names:
            url = reverse(url_name)
            self.assertTrue(
                url.endswith('/'),
                f"reverse('{url_name}') = '{url}' should end with trailing slash"
            )

    def test_authenticated_user_avoids_301_on_valid_urls(self):
        """Test that authenticated users don't get 301 on properly formed URLs."""
        user = User.objects.create_user(
            username='url-test-user',
            password='TestPassword123!'
        )
        self.client.force_login(user)
        
        # These should NOT return 301
        response = self.client.get('/settings/')
        self.assertNotEqual(
            response.status_code, 301,
            "Authenticated user should not get 301 on '/settings/'"
        )
        
        response = self.client.get('/users/')
        self.assertNotEqual(
            response.status_code, 301,
            "Authenticated user should not get 301 on '/users/'"
        )

    def test_hardcoded_url_without_slash_fails_test_expectations(self):
        """Demonstrate the exact issue from GitHub #26.
        
        If a test uses self.client.get('/settings') without trailing slash,
        it expects 403 (permission denied) but gets 301 (redirect) instead.
        """
        user = User.objects.create_user(
            username='url-test-user-2',
            password='TestPassword123!'
        )
        self.client.force_login(user)
        
        # WITHOUT trailing slash - gets 301 (this would cause test failures)
        response_without_slash = self.client.get('/settings')
        self.assertEqual(response_without_slash.status_code, 301)
        
        # WITH trailing slash - gets 403 as expected (permission denied for non-admin)
        response_with_slash = self.client.get('/settings/')
        self.assertEqual(response_with_slash.status_code, 403)
        
        # This demonstrates why tests fail: they expect 403 but get 301
        self.assertNotEqual(
            response_without_slash.status_code,
            response_with_slash.status_code,
            "URL without slash (301) should differ from URL with slash (403)"
        )
