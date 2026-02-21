"""
FleetFlow - seed_demo management command.

Populates the database with realistic demo data for showcasing all system features.
Run with: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds FleetFlow database with demo data for development/presentation."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(">>> Seeding FleetFlow demo data..."))

        from apps.users.models import Role, UserProfile
        from apps.fleet.models import Vehicle, FuelLog
        from apps.dispatch.models import Driver, Trip, TripAssignment, Cargo
        from apps.maintenance.models import MaintenanceLog
        from apps.finance.models import Expense, Invoice

        # -- Roles ---------------------------------------------------------------
        manager_role, _ = Role.objects.get_or_create(name=Role.RoleName.MANAGER)
        dispatcher_role, _ = Role.objects.get_or_create(name=Role.RoleName.DISPATCHER)
        safety_role, _ = Role.objects.get_or_create(name=Role.RoleName.SAFETY_OFFICER)
        self.stdout.write("  [OK] Roles created")

        # -- Users ---------------------------------------------------------------
        manager, _ = User.objects.get_or_create(
            email="manager@fleetflow.com",
            defaults={"username": "fleet_manager", "first_name": "Arjun", "last_name": "Mehta", "role": manager_role},
        )
        manager.set_password("manager123")
        manager.save()
        UserProfile.objects.get_or_create(user=manager, defaults={"phone": "9876543210", "department": "Operations"})

        dispatcher, _ = User.objects.get_or_create(
            email="dispatcher@fleetflow.com",
            defaults={"username": "dispatch_lead", "first_name": "Priya", "last_name": "Sharma", "role": dispatcher_role},
        )
        dispatcher.set_password("dispatcher123")
        dispatcher.save()
        UserProfile.objects.get_or_create(user=dispatcher, defaults={"phone": "9876543211", "department": "Dispatch"})

        safety, _ = User.objects.get_or_create(
            email="safety@fleetflow.com",
            defaults={"username": "safety_officer", "first_name": "Ravi", "last_name": "Kumar", "role": safety_role},
        )
        safety.set_password("safety123")
        safety.save()
        self.stdout.write("  [OK] Users created")

        # -- Vehicles ------------------------------------------------------------
        v1, _ = Vehicle.objects.get_or_create(
            plate_number="MH12AB1234",
            defaults={
                "make": "Tata", "model": "407", "year": 2021,
                "fuel_type": Vehicle.FuelType.DIESEL,
                "max_capacity_kg": Decimal("2500.00"),
                "odometer_km": Decimal("45200.50"),
                "created_by": manager,
            },
        )
        v2, _ = Vehicle.objects.get_or_create(
            plate_number="MH12CD5678",
            defaults={
                "make": "Ashok Leyland", "model": "Dost", "year": 2020,
                "fuel_type": Vehicle.FuelType.DIESEL,
                "max_capacity_kg": Decimal("1800.00"),
                "odometer_km": Decimal("62100.00"),
                "status": Vehicle.Status.IN_MAINTENANCE,
                "created_by": manager,
            },
        )
        v3, _ = Vehicle.objects.get_or_create(
            plate_number="MH12EF9012",
            defaults={
                "make": "Force", "model": "Trump 40", "year": 2022,
                "fuel_type": Vehicle.FuelType.DIESEL,
                "max_capacity_kg": Decimal("3500.00"),
                "odometer_km": Decimal("28000.00"),
                "created_by": manager,
            },
        )
        self.stdout.write("  [OK] Vehicles created")

        # -- Driver users --------------------------------------------------------
        d1_user, _ = User.objects.get_or_create(
            email="driver1@fleetflow.com",
            defaults={"username": "vikram_driver", "first_name": "Vikram", "last_name": "Singh"},
        )
        d1_user.set_password("driver123")
        d1_user.save()

        d2_user, _ = User.objects.get_or_create(
            email="driver2@fleetflow.com",
            defaults={"username": "suresh_driver", "first_name": "Suresh", "last_name": "Patil"},
        )
        d2_user.set_password("driver123")
        d2_user.save()

        driver1, _ = Driver.objects.get_or_create(
            user=d1_user,
            defaults={
                "license_number": "MH2023001234",
                "license_expires_on": datetime.date(2027, 6, 30),
                "license_class": "HMV",
                "experience_years": 7,
                "phone": "9876543212",
            },
        )
        driver2, _ = Driver.objects.get_or_create(
            user=d2_user,
            defaults={
                "license_number": "MH2022005678",
                "license_expires_on": datetime.date(2028, 3, 15),
                "license_class": "LMV",
                "experience_years": 4,
                "phone": "9876543213",
            },
        )
        self.stdout.write("  [OK] Drivers created")

        # -- Open Maintenance Log (for v2) ----------------------------------------
        MaintenanceLog.objects.get_or_create(
            vehicle=v2,
            service_type=MaintenanceLog.ServiceType.REPAIR,
            defaults={
                "logged_by": safety,
                "description": "Engine cooling system overhaul",
                "start_date": timezone.now().date() - datetime.timedelta(days=3),
                "cost": Decimal("18500.00"),
                "vendor": "AutoCare Workshop, Pune",
            },
        )
        self.stdout.write("  [OK] Maintenance log created")

        # -- Completed Trip with assignment, cargo, expenses, invoice -------------
        trip1, created = Trip.objects.get_or_create(
            trip_number="TRP-DEMO0001",
            defaults={
                "status": Trip.Status.COMPLETED,
                "origin": "Pune, Maharashtra",
                "destination": "Mumbai, Maharashtra",
                "scheduled_at": timezone.now() - datetime.timedelta(days=2),
                "dispatched_at": timezone.now() - datetime.timedelta(days=2, hours=-1),
                "completed_at": timezone.now() - datetime.timedelta(days=1),
                "distance_km": Decimal("148.00"),
                "created_by": dispatcher,
            },
        )
        if created:
            TripAssignment.objects.create(
                trip=trip1, vehicle=v1, driver=driver1, assigned_by=dispatcher
            )
            Cargo.objects.create(
                trip=trip1, description="Industrial Machinery Parts",
                weight_kg=Decimal("1200.00"), quantity=3,
            )
            Expense.objects.create(
                trip=trip1, category=Expense.Category.FUEL,
                amount=Decimal("3200.00"), date=timezone.now().date() - datetime.timedelta(days=2),
                added_by=manager,
            )
            Expense.objects.create(
                trip=trip1, category=Expense.Category.TOLL,
                amount=Decimal("450.00"), date=timezone.now().date() - datetime.timedelta(days=2),
                added_by=manager,
            )
            Invoice.objects.create(
                trip=trip1, client_name="Industrial Tech Pvt. Ltd.",
                amount_charged=Decimal("18000.00"),
                status=Invoice.Status.PAID,
                issued_at=timezone.now().date() - datetime.timedelta(days=1),
                paid_at=timezone.now(),
            )

        # -- Active dispatched trip -----------------------------------------------
        trip2, created = Trip.objects.get_or_create(
            trip_number="TRP-DEMO0002",
            defaults={
                "status": Trip.Status.DISPATCHED,
                "origin": "Pune, Maharashtra",
                "destination": "Nashik, Maharashtra",
                "scheduled_at": timezone.now(),
                "dispatched_at": timezone.now(),
                "distance_km": Decimal("210.00"),
                "created_by": dispatcher,
            },
        )
        if created:
            # Use driver2 + v3 (driver1 + v1 are already ON_TRIP from trip1)
            driver2.status = Driver.Status.ON_TRIP
            driver2.save(update_fields=["status"])
            v3.status = Vehicle.Status.ON_TRIP
            v3.save(update_fields=["status"])
            TripAssignment.objects.create(
                trip=trip2, vehicle=v3, driver=driver2, assigned_by=dispatcher
            )
            Cargo.objects.create(
                trip=trip2, description="FMCG Goods",
                weight_kg=Decimal("800.00"), quantity=50,
            )

        # -- Planned but unassigned trip ------------------------------------------
        Trip.objects.get_or_create(
            trip_number="TRP-DEMO0003",
            defaults={
                "status": Trip.Status.PLANNED,
                "origin": "Pune, Maharashtra",
                "destination": "Aurangabad, Maharashtra",
                "scheduled_at": timezone.now() + datetime.timedelta(days=1),
                "distance_km": Decimal("235.00"),
                "created_by": dispatcher,
            },
        )

        self.stdout.write("  [OK] Trips, cargo, expenses, invoices created")
        self.stdout.write(self.style.SUCCESS("\n[DONE] Demo data seeded successfully!\n"))
        self.stdout.write("Credentials:")
        self.stdout.write("  Manager:          manager@fleetflow.com / manager123")
        self.stdout.write("  Dispatcher:       dispatcher@fleetflow.com / dispatcher123")
        self.stdout.write("  Safety Officer:   safety@fleetflow.com / safety123")
