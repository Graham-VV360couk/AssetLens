"""
Seed 5 test/demo users directly into the database.
These users bypass Stripe entirely — subscription_status is set to 'active'
with no stripe_customer_id, so they are never billed.

Usage:
    docker-compose exec backend python scripts/seed_test_users.py

Or locally:
    python scripts/seed_test_users.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.models.base import SessionLocal
from backend.models.user import User, UserProfile
from backend.auth.manager import hash_password

TEST_USERS = [
    {
        'email': 'investor@assetlens.test',
        'password': 'TestInvestor2026!',
        'full_name': 'Test Investor',
        'role': 'investor',
        'subscription_status': 'active',
        'subscription_tier': 'investor',
        'is_verified': True,
    },
    {
        'email': 'auction@assetlens.test',
        'password': 'TestAuction2026!',
        'full_name': 'Test Auction House',
        'company_name': 'Demo Auctions Ltd',
        'role': 'auction_house',
        'subscription_status': 'active',
        'subscription_tier': 'auction_house',
        'is_verified': True,
    },
    {
        'email': 'dealer@assetlens.test',
        'password': 'TestDealer2026!',
        'full_name': 'Test Deal Source',
        'company_name': 'Demo Deals Ltd',
        'role': 'deal_source',
        'subscription_status': 'active',
        'subscription_tier': 'deal_source',
        'is_verified': True,
    },
    {
        'email': 'whitelabel@assetlens.test',
        'password': 'TestWhiteLabel2026!',
        'full_name': 'Test White Label',
        'company_name': 'Premium Auctions Ltd',
        'role': 'auction_house',
        'subscription_status': 'active',
        'subscription_tier': 'white_label',
        'is_verified': True,
    },
    {
        'email': 'admin@assetlens.test',
        'password': 'TestAdmin2026!',
        'full_name': 'AssetLens Admin',
        'role': 'admin',
        'subscription_status': 'active',
        'subscription_tier': 'admin',
        'is_superuser': True,
        'is_verified': True,
    },
]


def seed():
    db = SessionLocal()
    created = 0
    skipped = 0

    try:
        for u in TEST_USERS:
            existing = db.query(User).filter(User.email == u['email']).first()
            if existing:
                print(f"  SKIP  {u['email']} (already exists, id={existing.id})")
                skipped += 1
                continue

            user = User(
                email=u['email'],
                hashed_password=hash_password(u['password']),
                full_name=u['full_name'],
                company_name=u.get('company_name'),
                role=u['role'],
                subscription_status=u['subscription_status'],
                subscription_tier=u['subscription_tier'],
                is_superuser=u.get('is_superuser', False),
                is_verified=u.get('is_verified', False),
                is_active=True,
                trial_property_views=0,
                trial_ai_views=0,
                # No stripe_customer_id — these users are never billed
            )
            db.add(user)
            db.flush()

            profile = UserProfile(user_id=user.id)
            db.add(profile)

            print(f"  CREATE  {u['email']} (id={user.id}, tier={u['subscription_tier']})")
            created += 1

        db.commit()
        print(f"\nDone: {created} created, {skipped} skipped")
        print("\n--- Test credentials ---")
        for u in TEST_USERS:
            print(f"  {u['email']:35s}  {u['password']:25s}  [{u['subscription_tier']}]")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("Seeding test users...\n")
    seed()
