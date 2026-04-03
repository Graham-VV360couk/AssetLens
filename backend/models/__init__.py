"""
AssetLens Database Models
"""

from .base import Base
from .user import User, UserProfile
from .property import Property, PropertySource, PropertyScore
from .sales_history import SalesHistory
from .rental import Rental
from .hmo import HMORegister
from .auction import Auction
from .scraper_source import ScraperSource
from .scraper_run_log import ScraperRunLog
from .property_ai_insight import PropertyAIInsight
from .property_attribute_profile import PropertyAttributeProfile
from .epc_certificate import EPCCertificate
from .epc_recommendation import EPCRecommendation
from .school import School
from .crime import Crime
from .postcode import Postcode
from .planning_designation import PlanningDesignation
from .transport_stop import TransportStop
from .broadband import BroadbandCoverage
from .alert_preference import UserAlertPreference
from .user_property import UserProperty, PropertyValuation
from .private_listing import PrivateListing, Conversation, Message

__all__ = [
    'Base',
    'User',
    'UserProfile',
    'Property',
    'PropertySource',
    'PropertyScore',
    'SalesHistory',
    'Rental',
    'HMORegister',
    'Auction',
    'ScraperSource',
    'ScraperRunLog',
    'PropertyAIInsight',
    'PropertyAttributeProfile',
    'EPCCertificate',
    'EPCRecommendation',
    'School',
    'Crime',
    'Postcode',
    'PlanningDesignation',
    'TransportStop',
    'BroadbandCoverage',
    'UserAlertPreference',
    'UserProperty',
    'PropertyValuation',
    'PrivateListing',
    'Conversation',
    'Message',
]
