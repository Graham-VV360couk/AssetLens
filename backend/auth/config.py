"""JWT configuration."""
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'CHANGE-ME-IN-PRODUCTION')
JWT_LIFETIME_SECONDS = int(os.environ.get('JWT_LIFETIME_SECONDS', '1800'))  # 30 min
JWT_REFRESH_LIFETIME_SECONDS = int(os.environ.get('JWT_REFRESH_LIFETIME_SECONDS', '604800'))  # 7 days
