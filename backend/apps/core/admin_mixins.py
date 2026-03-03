"""Mixin for ImportExportModelAdmin that adds CSV column reference guide."""


class ImportGuideMixin:
    """Adds a CSV column reference table to the import page.

    Usage: Set `import_guide` on the admin class as a dict with:
        - title: str
        - description: str (optional)
        - columns: list of dicts with 'name', 'required', 'description'
    """

    import_guide = None
    import_template_name = 'admin/import_with_guide.html'

    def get_import_context_data(self, **kwargs):
        context = super().get_import_context_data(**kwargs)
        if self.import_guide:
            context['column_guide_title'] = self.import_guide.get('title', '')
            context['column_guide_description'] = self.import_guide.get('description', '')
            context['column_guide'] = self.import_guide.get('columns', [])
        return context
