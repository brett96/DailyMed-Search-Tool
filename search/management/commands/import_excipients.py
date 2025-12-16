"""
Management command to import excipient categories from Excel file.
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from search.models import ExcipientCategory, Excipient


# Define the 12 categories with their display order
CATEGORY_ORDER = {
    'Alcohols (Ethyl, Isopropyl, Benzyl, etc.)': 1,
    'Anti-adherents / Lubricants / Glidants': 2,
    'Antimicrobial Agents': 3,
    'Binders / Fillers': 4,
    'Coatings': 5,
    'Colorants / Dyes': 6,
    'Disintegrants': 7,
    'Flavorings / Sweeteners': 8,
    'Fragrances / Odorants': 9,
    'Other-2': 10,
    'Preservatives': 11,
    'Solubilizing Agents': 12,
}


class Command(BaseCommand):
    help = 'Import excipient categories and excipients from Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Path to the Excel file containing excipient data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing excipient data before importing'
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        clear_existing = options['clear']
        
        self.stdout.write(f'Reading Excel file: {excel_file}')
        
        try:
            # Read the Excel file
            df = pd.read_excel(excel_file)
            
            # Verify required columns exist
            required_columns = ['INGREDIENT_NAME', 'Category']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.stdout.write(
                    self.style.ERROR(f'Missing required columns: {missing_columns}')
                )
                return
            
            # Filter out rows without category
            df = df[df['Category'].notna()]
            
            self.stdout.write(f'Found {len(df)} rows with categories')
            
            # Clear existing data if requested
            if clear_existing:
                self.stdout.write('Clearing existing excipient data...')
                Excipient.objects.all().delete()
                ExcipientCategory.objects.all().delete()
            
            # Create categories and import excipients
            with transaction.atomic():
                # Create or get all categories
                category_objects = {}
                for category_name in CATEGORY_ORDER.keys():
                    category, created = ExcipientCategory.objects.get_or_create(
                        name=category_name,
                        defaults={
                            'display_order': CATEGORY_ORDER[category_name]
                        }
                    )
                    category_objects[category_name] = category
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created category: {category_name}')
                        )
                    else:
                        # Update display order if it changed
                        if category.display_order != CATEGORY_ORDER[category_name]:
                            category.display_order = CATEGORY_ORDER[category_name]
                            category.save()
                
                # Import excipients
                imported_count = 0
                skipped_count = 0
                
                for _, row in df.iterrows():
                    ingredient_name = str(row['INGREDIENT_NAME']).strip()
                    category_name = str(row['Category']).strip()
                    
                    if not ingredient_name or not category_name:
                        skipped_count += 1
                        continue
                    
                    # Skip if category is not in our list
                    if category_name not in category_objects:
                        skipped_count += 1
                        continue
                    
                    category = category_objects[category_name]
                    
                    # Create or update excipient
                    # Note: We allow multiple entries with same ingredient_name
                    # if they have different routes/forms, but for simplicity,
                    # we'll create one entry per ingredient_name per category
                    excipient, created = Excipient.objects.get_or_create(
                        ingredient_name=ingredient_name,
                        category=category,
                        defaults={
                            'route': str(row.get('ROUTE', '')).strip() if pd.notna(row.get('ROUTE')) else None,
                            'dosage_form': str(row.get('DOSAGE_FORM', '')).strip() if pd.notna(row.get('DOSAGE_FORM')) else None,
                            'cas_number': str(row.get('CAS_NUMBER', '')).strip() if pd.notna(row.get('CAS_NUMBER')) else None,
                            'unii': str(row.get('UNII', '')).strip() if pd.notna(row.get('UNII')) else None,
                            'potency_amount': str(row.get('POTENCY_AMOUNT', '')).strip() if pd.notna(row.get('POTENCY_AMOUNT')) else None,
                            'potency_unit': str(row.get('POTENCY_UNIT', '')).strip() if pd.notna(row.get('POTENCY_UNIT')) else None,
                            'maximum_daily_exposure': str(row.get('MAXIMUM_DAILY_EXPOSURE', '')).strip() if pd.notna(row.get('MAXIMUM_DAILY_EXPOSURE')) else None,
                            'maximum_daily_exposure_unit': str(row.get('MAXIMUM_DAILY_EXPOSURE_UNIT', '')).strip() if pd.notna(row.get('MAXIMUM_DAILY_EXPOSURE_UNIT')) else None,
                            'common_technical_name': str(row.get('Common_Technical_Name', '')).strip() if pd.notna(row.get('Common_Technical_Name')) else None,
                            'common_trade_or_consumer_name': str(row.get('Common_Trade_or_Consumer_Name', '')).strip() if pd.notna(row.get('Common_Trade_or_Consumer_Name')) else None,
                            'notes': str(row.get('Notes', '')).strip() if pd.notna(row.get('Notes')) else None,
                        }
                    )
                    
                    if created:
                        imported_count += 1
                    else:
                        # Update fields if they're empty
                        updated = False
                        if not excipient.route and pd.notna(row.get('ROUTE')):
                            excipient.route = str(row.get('ROUTE', '')).strip()
                            updated = True
                        if not excipient.dosage_form and pd.notna(row.get('DOSAGE_FORM')):
                            excipient.dosage_form = str(row.get('DOSAGE_FORM', '')).strip()
                            updated = True
                        if not excipient.cas_number and pd.notna(row.get('CAS_NUMBER')):
                            excipient.cas_number = str(row.get('CAS_NUMBER', '')).strip()
                            updated = True
                        if not excipient.unii and pd.notna(row.get('UNII')):
                            excipient.unii = str(row.get('UNII', '')).strip()
                            updated = True
                        if updated:
                            excipient.save()
                            imported_count += 1
                        else:
                            skipped_count += 1
                    
                    if imported_count % 100 == 0:
                        self.stdout.write(f'Imported {imported_count} excipients...')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nImport complete!\n'
                        f'  - Imported/Updated: {imported_count} excipients\n'
                        f'  - Skipped: {skipped_count} rows\n'
                        f'  - Categories: {len(category_objects)}'
                    )
                )
                
                # Print summary by category
                self.stdout.write('\nSummary by category:')
                for category_name, category in sorted(category_objects.items(), key=lambda x: x[1].display_order):
                    count = category.excipients.count()
                    self.stdout.write(f'  {category_name}: {count} excipients')
        
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'File not found: {excel_file}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing data: {e}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())


