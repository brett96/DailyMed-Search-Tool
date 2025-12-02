
class RxNormRouter:
    """
    Routes reads for any model in the 'rxnorm_app' to DATABASES['rxnorm'],
    and prevents writes.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'rxnorm':
            return 'rxnorm'
        return None

    def db_for_write(self, model, **hints):
        # read-only
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # never run migrations on rxnorm
        if db == 'rxnorm':
            return False
        return None

