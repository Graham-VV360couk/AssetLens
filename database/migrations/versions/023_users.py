"""Create users and user_profiles tables.

Revision ID: 023
Revises: 022
"""
from alembic import op
import sqlalchemy as sa

revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('company_name', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='investor'),
        sa.Column('subscription_status', sa.String(20), nullable=False, server_default='trial'),
        sa.Column('subscription_tier', sa.String(20), nullable=False, server_default='none'),
        sa.Column('stripe_customer_id', sa.String(100), unique=True, nullable=True),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=True),
        sa.Column('stripe_subscription_id_secondary', sa.String(100), nullable=True),
        sa.Column('trial_property_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trial_ai_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False),
        sa.Column('max_deposit', sa.Integer(), nullable=True),
        sa.Column('loan_type_sought', sa.String(50), nullable=True),
        sa.Column('max_loan_wanted', sa.Integer(), nullable=True),
        sa.Column('loan_term_months', sa.Integer(), nullable=True),
        sa.Column('purpose', sa.String(20), nullable=True),
        sa.Column('investment_experience', sa.String(20), nullable=True),
        sa.Column('properties_owned', sa.Integer(), nullable=True),
        sa.Column('portfolio_value_band', sa.String(20), nullable=True),
        sa.Column('outstanding_mortgage_band', sa.String(20), nullable=True),
        sa.Column('hmo_experience', sa.Boolean(), nullable=True),
        sa.Column('development_experience', sa.Boolean(), nullable=True),
        sa.Column('limited_company', sa.Boolean(), nullable=True),
        sa.Column('company_name_ch', sa.String(200), nullable=True),
        sa.Column('companies_house_number', sa.String(20), nullable=True),
        sa.Column('spv', sa.Boolean(), nullable=True),
        sa.Column('personal_guarantee_willing', sa.Boolean(), nullable=True),
        sa.Column('main_residence', sa.Boolean(), nullable=True),
        sa.Column('uk_resident', sa.Boolean(), nullable=True),
        sa.Column('employment_status', sa.String(20), nullable=True),
        sa.Column('annual_income_band', sa.String(20), nullable=True),
        sa.Column('credit_history', sa.String(20), nullable=True),
        sa.Column('target_location', sa.String(200), nullable=True),
        sa.Column('strategy', sa.String(30), nullable=True),
        sa.Column('readiness', sa.String(20), nullable=True),
        sa.Column('broker_consent_given_at', sa.DateTime(), nullable=True),
        sa.Column('profile_deletion_at', sa.DateTime(), nullable=True),
        sa.Column('auction_form_field_prefs', sa.Text(), nullable=True),
        sa.Column('brand_logo_url', sa.String(500), nullable=True),
        sa.Column('brand_primary_colour', sa.String(7), nullable=True),
        sa.Column('brand_accent_colour', sa.String(7), nullable=True),
        sa.Column('custom_subdomain', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('user_profiles')
    op.drop_table('users')
