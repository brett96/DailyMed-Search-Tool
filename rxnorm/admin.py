from django.contrib import admin
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.template.response import TemplateResponse
from .models import (
    Rxnatomarchive, Rxnconso, Rxncui, Rxncuichanges,
    Rxndoc, Rxnrel, Rxnsab, Rxnsat, Rxnsty
)

class RxNormAdminMixin:
    """Mixin to handle RxNorm database connection failures gracefully."""
    
    def changelist_view(self, request, extra_context=None):
        try:
            return super().changelist_view(request, extra_context)
        except OperationalError as e:
            if "connection to server" in str(e) and "failed" in str(e):
                # Database connection failed - show friendly error message
                context = {
                    'title': 'RxNorm Database Unavailable',
                    'error_message': 'The RxNorm database is currently unavailable. Please try again later.',
                    'details': str(e),
                    'opts': self.model._meta,
                    'cl': None,
                    'media': self.media,
                }
                return TemplateResponse(
                    request,
                    'admin/rxnorm_database_error.html',
                    context,
                    status=503
                )
            else:
                # Re-raise other operational errors
                raise

@admin.register(Rxnatomarchive)
class RxnatomarchiveAdmin(RxNormAdminMixin, admin.ModelAdmin):
    # show all fields in list display
    list_display = [f.name for f in Rxnatomarchive._meta.fields]

@admin.register(Rxnconso)
class RxnconsoAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxnconso._meta.fields]

@admin.register(Rxncui)
class RxncuiAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxncui._meta.fields]

@admin.register(Rxncuichanges)
class RxncuichangesAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxncuichanges._meta.fields]

@admin.register(Rxndoc)
class RxndocAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxndoc._meta.fields]

@admin.register(Rxnrel)
class RxnrelAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxnrel._meta.fields]

@admin.register(Rxnsab)
class RxnsabAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxnsab._meta.fields]

@admin.register(Rxnsat)
class RxnsatAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxnsat._meta.fields]

@admin.register(Rxnsty)
class RxnstyAdmin(RxNormAdminMixin, admin.ModelAdmin):
    list_display = [f.name for f in Rxnsty._meta.fields]

