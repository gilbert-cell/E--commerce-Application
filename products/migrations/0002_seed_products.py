from decimal import Decimal

from django.db import migrations


PRODUCTS = [
    {
        'category': 'Electronics',
        'name': 'SecurePay Smart Wallet',
        'description': 'Encrypted NFC wallet with biometric unlock and fraud alerts.',
        'price': Decimal('89.99'),
        'stock': 18,
        'image': 'https://picsum.photos/seed/wallet/600/400',
    },
    {
        'category': 'Electronics',
        'name': 'PrivacyCam HD',
        'description': 'Webcam with physical privacy shutter and low-light face verification support.',
        'price': Decimal('64.50'),
        'stock': 25,
        'image': 'https://picsum.photos/seed/webcam/600/400',
    },
    {
        'category': 'Accessories',
        'name': 'RFID Shield Card Holder',
        'description': 'Slim card holder that blocks unauthorized RFID scans.',
        'price': Decimal('24.99'),
        'stock': 42,
        'image': 'https://picsum.photos/seed/cardholder/600/400',
    },
    {
        'category': 'Accessories',
        'name': 'USB-C Security Key',
        'description': 'Hardware authentication key for phishing-resistant account protection.',
        'price': Decimal('39.00'),
        'stock': 31,
        'image': 'https://picsum.photos/seed/usbkey/600/400',
    },
    {
        'category': 'Home Security',
        'name': 'Smart Door Sensor Kit',
        'description': 'Connected entry sensors with tamper alerts and mobile notifications.',
        'price': Decimal('119.99'),
        'stock': 12,
        'image': 'https://picsum.photos/seed/doorsensor/600/400',
    },
    {
        'category': 'Home Security',
        'name': 'Encrypted Motion Camera',
        'description': 'Indoor motion camera with encrypted local storage and face-aware alerts.',
        'price': Decimal('149.95'),
        'stock': 9,
        'image': 'https://picsum.photos/seed/motioncam/600/400',
    },
]


def seed_products(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')

    for item in PRODUCTS:
        category, _ = Category.objects.get_or_create(name=item['category'])
        Product.objects.get_or_create(
            name=item['name'],
            defaults={
                'category': category,
                'description': item['description'],
                'price': item['price'],
                'stock': item['stock'],
                'is_active': True,
            },
        )


def remove_seed_products(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')

    Product.objects.filter(name__in=[item['name'] for item in PRODUCTS]).delete()
    for category_name in {item['category'] for item in PRODUCTS}:
        Category.objects.filter(name=category_name, products__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_products, remove_seed_products),
    ]
