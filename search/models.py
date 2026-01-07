from django.db import models


class ExcipientCategory(models.Model):
    """
    Represents one of the 12 excipient categories.
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(default=0, help_text="Order for display in UI")
    
    class Meta:
        verbose_name = "Excipient Category"
        verbose_name_plural = "Excipient Categories"
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Excipient(models.Model):
    """
    Represents an excipient (inactive ingredient) with its category mapping.
    Matches are done based on Ingredient_Name.
    """
    ingredient_name = models.CharField(max_length=500, db_index=True, help_text="The ingredient name as it appears in FDA data")
    category = models.ForeignKey(ExcipientCategory, on_delete=models.CASCADE, related_name='excipients')
    
    # Additional fields from Excel that might be useful
    route = models.CharField(max_length=200, blank=True, null=True)
    dosage_form = models.CharField(max_length=200, blank=True, null=True)
    cas_number = models.CharField(max_length=50, blank=True, null=True)
    unii = models.CharField(max_length=50, blank=True, null=True)
    potency_amount = models.CharField(max_length=50, blank=True, null=True)
    potency_unit = models.CharField(max_length=50, blank=True, null=True)
    maximum_daily_exposure = models.CharField(max_length=50, blank=True, null=True)
    maximum_daily_exposure_unit = models.CharField(max_length=50, blank=True, null=True)
    common_technical_name = models.CharField(max_length=500, blank=True, null=True)
    common_trade_or_consumer_name = models.CharField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Excipient"
        verbose_name_plural = "Excipients"
        indexes = [
            models.Index(fields=['ingredient_name']),
            models.Index(fields=['category']),
        ]
        # Allow same ingredient name in different categories if needed
        # (though typically one ingredient maps to one category)
    
    def __str__(self):
        return f"{self.ingredient_name} ({self.category.name})"







