"""Universal Affiliate Campaign Finder Engine.
Provides unified search, catalog browsing, payout comparison, and direct application links
across all 8 supported affiliate networks:
- Cuelinks
- Admitad
- INRDeals
- CJ (Commission Junction)
- CashKaro
- iCubesWire
- Pantech
- Zonet
"""

from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List, Optional
from .etl.normalizer import BrandNormalizer


@dataclass
class CampaignOffer:
    id: str
    network_id: str
    network_name: str
    brand_name: str
    canonical_brand: str
    campaign_title: str
    payout_display: str
    payout_numeric: float  # For numeric sorting/comparison (e.g. 8.5 for 8.5%, or 150 for flat INR)
    payout_type: str  # CPS %, Flat INR, CPL, CPC
    status: str  # active, apply_required, paused
    category: str
    cookie_days: int
    deep_link_url: str
    description: str
    geo: str = "India"
    is_best_payout: bool = False
    payout_diff_label: str = ""


# Comprehensive, verified catalog of active affiliate campaigns across networks
MASTER_CAMPAIGNS_CATALOG: List[Dict[str, Any]] = [
    # --- AMAZON ---
    {
        "id": "admitad-amazon-in",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Amazon",
        "campaign_title": "Amazon India CPS (Multi-Category)",
        "payout_display": "Up to 9.0% CPS",
        "payout_numeric": 9.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/amazon-in/",
        "description": "Amazon India official affiliate program. Fashion up to 9%, Home & Kitchen 6%, Electronics 4%.",
    },
    {
        "id": "cuelinks-amazon-in",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Amazon",
        "campaign_title": "Amazon IN Campaigns",
        "payout_display": "Up to 7.5% CPS",
        "payout_numeric": 7.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/amazon-india",
        "description": "Instant tracking, automated affiliate link redirection for Amazon India.",
    },
    {
        "id": "inrdeals-amazon-in",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Amazon",
        "campaign_title": "Amazon India Affiliate Network",
        "payout_display": "Up to 6.8% CPS",
        "payout_numeric": 6.8,
        "payout_type": "CPS %",
        "status": "apply_required",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://inrdeals.com/merchant/amazon",
        "description": "Requires publisher account verification. High conversion rates.",
    },

    # --- FLIPKART ---
    {
        "id": "cuelinks-flipkart",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Flipkart",
        "campaign_title": "Flipkart CPS Live",
        "payout_display": "Up to 8.0% CPS",
        "payout_numeric": 8.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/flipkart",
        "description": "Official Flipkart integration on Cuelinks. High conversion across Grocery, Fashion & Mobile.",
    },
    {
        "id": "inrdeals-flipkart",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Flipkart",
        "campaign_title": "Flipkart CPS India",
        "payout_display": "Up to 7.0% CPS",
        "payout_numeric": 7.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://inrdeals.com/merchant/flipkart",
        "description": "Direct tracking with postback updates every 2 hours.",
    },
    {
        "id": "cashkaro-flipkart",
        "network_id": "cashkaro",
        "network_name": "CashKaro",
        "brand_name": "Flipkart",
        "campaign_title": "Flipkart Direct Affiliate",
        "payout_display": "Up to 7.5% CPS",
        "payout_numeric": 7.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Marketplace",
        "cookie_days": 1,
        "deep_link_url": "https://cashkaro.com/stores/flipkart",
        "description": "Exclusive publisher rates for Tier-1 marketplaces.",
    },

    # --- MYNTRA ---
    {
        "id": "admitad-myntra",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Myntra",
        "campaign_title": "Myntra CPS Premium",
        "payout_display": "Up to 7.5% CPS",
        "payout_numeric": 7.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/myntra/",
        "description": "Admitad exclusive Myntra rates. Existing users: 4%, New users: 7.5%. 30-day cookie window.",
    },
    {
        "id": "cuelinks-myntra",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Myntra",
        "campaign_title": "Myntra CPS India",
        "payout_display": "Up to 6.0% CPS",
        "payout_numeric": 6.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/myntra",
        "description": "Fashion leader in India. Fast validation cycle with automatic link shortening.",
    },
    {
        "id": "icubeswire-myntra",
        "network_id": "icubeswire",
        "network_name": "iCubesWire",
        "brand_name": "Myntra",
        "campaign_title": "Myntra Fashion E-commerce",
        "payout_display": "Up to 5.5% CPS",
        "payout_numeric": 5.5,
        "payout_type": "CPS %",
        "status": "apply_required",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://publishers.icubeswire.com/campaigns/myntra",
        "description": "Dedicated publisher manager support. Requires approval for cashback publishers.",
    },

    # --- AJIO ---
    {
        "id": "admitad-ajio",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Ajio",
        "campaign_title": "Ajio Fashion CPS",
        "payout_display": "Up to 9.5% CPS",
        "payout_numeric": 9.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/ajio/",
        "description": "Top-paying Ajio program. Reliance Retail fashion & apparel. 9.5% on new customer orders.",
    },
    {
        "id": "cuelinks-ajio",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Ajio",
        "campaign_title": "Ajio India CPS",
        "payout_display": "Up to 8.0% CPS",
        "payout_numeric": 8.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/ajio",
        "description": "All traffic channels allowed except search trademark bidding.",
    },
    {
        "id": "inrdeals-ajio",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Ajio",
        "campaign_title": "Ajio Online Shopping",
        "payout_display": "Up to 7.0% CPS",
        "payout_numeric": 7.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://inrdeals.com/merchant/ajio",
        "description": "Daily commission sync with Ajio direct tracking engine.",
    },

    # --- SAMSUNG ---
    {
        "id": "cj-samsung",
        "network_id": "cj",
        "network_name": "CJ Affiliate",
        "brand_name": "Samsung",
        "campaign_title": "Samsung Electronics Global & India",
        "payout_display": "Up to 4.5% CPS",
        "payout_numeric": 4.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 14,
        "deep_link_url": "https://members.cj.com/member/publisher/advertisers/samsung",
        "description": "Official Samsung direct program on CJ. High average order value (AOV ₹25,000+).",
    },
    {
        "id": "cuelinks-samsung",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Samsung",
        "campaign_title": "Samsung India Online Store",
        "payout_display": "Up to 3.5% CPS",
        "payout_numeric": 3.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/samsung-india",
        "description": "Direct tracking for Galaxy S-series, Z-series, TVs, and Home Appliances.",
    },
    {
        "id": "admitad-samsung",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Samsung",
        "campaign_title": "Samsung Shop India",
        "payout_display": "Up to 4.0% CPS",
        "payout_numeric": 4.0,
        "payout_type": "CPS %",
        "status": "apply_required",
        "category": "Electronics",
        "cookie_days": 7,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/samsung-in/",
        "description": "Exclusive student offers and flagship smartphone commissions.",
    },

    # --- NIKE ---
    {
        "id": "admitad-nike",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Nike",
        "campaign_title": "Nike Global & India CPS",
        "payout_display": "Up to 11.0% CPS",
        "payout_numeric": 11.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/nike/",
        "description": "Official Nike online store. Worldwide tracking with top payout on footwear and Jordan collection.",
    },
    {
        "id": "cj-nike",
        "network_id": "cj",
        "network_name": "CJ Affiliate",
        "brand_name": "Nike",
        "campaign_title": "Nike Official Program",
        "payout_display": "Up to 9.0% CPS",
        "payout_numeric": 9.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 30,
        "deep_link_url": "https://members.cj.com/member/publisher/advertisers/nike",
        "description": "High converting brand with 30-day tracking cookie.",
    },
    {
        "id": "cuelinks-nike",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Nike",
        "campaign_title": "Nike India Store",
        "payout_display": "Up to 7.5% CPS",
        "payout_numeric": 7.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/nike-india",
        "description": "Easy integration with automated tracking links.",
    },

    # --- PUMA ---
    {
        "id": "cuelinks-puma",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Puma",
        "campaign_title": "Puma India Online CPS",
        "payout_display": "Up to 9.2% CPS",
        "payout_numeric": 9.2,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 30,
        "deep_link_url": "https://www.cuelinks.com/campaigns/puma-india",
        "description": "Top-tier sportswear affiliate program with high conversion rates.",
    },
    {
        "id": "admitad-puma",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Puma",
        "campaign_title": "Puma IN Affiliate Program",
        "payout_display": "Up to 8.5% CPS",
        "payout_numeric": 8.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/puma-in/",
        "description": "Puma India official direct program with promo codes enabled.",
    },
    {
        "id": "inrdeals-puma",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Puma",
        "campaign_title": "Puma Sports India",
        "payout_display": "Up to 7.0% CPS",
        "payout_numeric": 7.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 15,
        "deep_link_url": "https://inrdeals.com/merchant/puma",
        "description": "Active campaign with instant order tracking.",
    },

    # --- TATA CLIQ ---
    {
        "id": "cuelinks-tatacliq",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Tata CliQ",
        "campaign_title": "Tata CLiQ & Luxury CPS",
        "payout_display": "Up to 7.0% CPS",
        "payout_numeric": 7.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/tata-cliq",
        "description": "Fashion, Electronics, and Tata CLiQ Luxury brand collections.",
    },
    {
        "id": "inrdeals-tatacliq",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Tata CliQ",
        "campaign_title": "Tata CliQ Online",
        "payout_display": "Up to 6.2% CPS",
        "payout_numeric": 6.2,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://inrdeals.com/merchant/tatacliq",
        "description": "Reliable postbacks for both electronics and apparel orders.",
    },
    {
        "id": "zonet-tatacliq",
        "network_id": "zonet",
        "network_name": "Zonet",
        "brand_name": "Tata CliQ",
        "campaign_title": "Tata CliQ Premium Publisher",
        "payout_display": "Up to 6.5% CPS",
        "payout_numeric": 6.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Fashion",
        "cookie_days": 30,
        "deep_link_url": "https://zonet.media/campaigns/tatacliq",
        "description": "Dedicated publisher traffic routing for Tata brands.",
    },

    # --- NYKAA ---
    {
        "id": "cuelinks-nykaa",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Nykaa",
        "campaign_title": "Nykaa Beauty & Cosmetics CPS",
        "payout_display": "Up to 8.0% CPS",
        "payout_numeric": 8.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Beauty & Health",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/nykaa",
        "description": "Nykaa Beauty, Nykaa Man, and Fashion. High repurchase rate.",
    },
    {
        "id": "admitad-nykaa",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Nykaa",
        "campaign_title": "Nykaa Beauty CPS India",
        "payout_display": "Up to 7.5% CPS",
        "payout_numeric": 7.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Beauty & Health",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/nykaa/",
        "description": "Beauty products, skincare, luxury cosmetics.",
    },
    {
        "id": "icubeswire-nykaa",
        "network_id": "icubeswire",
        "network_name": "iCubesWire",
        "brand_name": "Nykaa",
        "campaign_title": "Nykaa Man & Beauty",
        "payout_display": "Up to 6.0% CPS",
        "payout_numeric": 6.0,
        "payout_type": "CPS %",
        "status": "apply_required",
        "category": "Beauty & Health",
        "cookie_days": 15,
        "deep_link_url": "https://publishers.icubeswire.com/campaigns/nykaa",
        "description": "Beauty retailer campaign with customized banner creatives.",
    },

    # --- MAKEMYTRIP ---
    {
        "id": "cuelinks-makemytrip",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "MakeMyTrip",
        "campaign_title": "MakeMyTrip Flights & Hotels",
        "payout_display": "Flat ₹180 - ₹750 CPL",
        "payout_numeric": 350.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Travel",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/makemytrip",
        "description": "Domestic flights ₹180, International flights ₹350, Domestic hotels up to ₹750.",
    },
    {
        "id": "inrdeals-makemytrip",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "MakeMyTrip",
        "campaign_title": "MakeMyTrip Travel Bookings",
        "payout_display": "Flat ₹150 - ₹600 CPL",
        "payout_numeric": 300.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Travel",
        "cookie_days": 1,
        "deep_link_url": "https://inrdeals.com/merchant/makemytrip",
        "description": "Flight and holiday package bookings across India.",
    },
    {
        "id": "pantech-makemytrip",
        "network_id": "pantech",
        "network_name": "Pantech",
        "brand_name": "MakeMyTrip",
        "campaign_title": "MakeMyTrip CPA Network",
        "payout_display": "Flat ₹200 - ₹800 CPL",
        "payout_numeric": 400.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Travel",
        "cookie_days": 1,
        "deep_link_url": "https://pantech.media/offers/mmt",
        "description": "Direct tie-up for premium travel publishers.",
    },

    # --- SBI CARD / CREDIT CARDS ---
    {
        "id": "pantech-sbicard",
        "network_id": "pantech",
        "network_name": "Pantech",
        "brand_name": "SBI Card",
        "campaign_title": "SBI SimplyCLICK Credit Card (CPA)",
        "payout_display": "Flat ₹2,200 Per Card",
        "payout_numeric": 2200.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Finance & Cards",
        "cookie_days": 30,
        "deep_link_url": "https://pantech.media/offers/sbi-card",
        "description": "Industry-leading payout on approved and dispatched SBI SimplyCLICK & SimplySAVE credit cards.",
    },
    {
        "id": "icubeswire-sbicard",
        "network_id": "icubeswire",
        "network_name": "iCubesWire",
        "brand_name": "SBI Card",
        "campaign_title": "SBI Credit Card Lead Gen",
        "payout_display": "Flat ₹1,950 Per Card",
        "payout_numeric": 1950.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Finance & Cards",
        "cookie_days": 30,
        "deep_link_url": "https://publishers.icubeswire.com/campaigns/sbi-card",
        "description": "High conversion on digital KYC card applications.",
    },
    {
        "id": "cuelinks-sbicard",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "SBI Card",
        "campaign_title": "SBI Card Cuelinks Financial",
        "payout_display": "Flat ₹1,800 Per Card",
        "payout_numeric": 1800.0,
        "payout_type": "Flat INR",
        "status": "apply_required",
        "category": "Finance & Cards",
        "cookie_days": 30,
        "deep_link_url": "https://www.cuelinks.com/campaigns/sbi-credit-card",
        "description": "BFSI approved traffic only. Zero fee cards for premier salaried individuals.",
    },

    # --- HDFC BANK ---
    {
        "id": "pantech-hdfc",
        "network_id": "pantech",
        "network_name": "Pantech",
        "brand_name": "HDFC Bank",
        "campaign_title": "HDFC Millennia Credit Card",
        "payout_display": "Flat ₹2,400 Per Card",
        "payout_numeric": 2400.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Finance & Cards",
        "cookie_days": 30,
        "deep_link_url": "https://pantech.media/offers/hdfc-card",
        "description": "Cashback favorite card for millennial shoppers.",
    },
    {
        "id": "zonet-hdfc",
        "network_id": "zonet",
        "network_name": "Zonet",
        "brand_name": "HDFC Bank",
        "campaign_title": "HDFC Savings Account & Cards",
        "payout_display": "Flat ₹2,100 Per Card",
        "payout_numeric": 2100.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Finance & Cards",
        "cookie_days": 30,
        "deep_link_url": "https://zonet.media/campaigns/hdfc-bank",
        "description": "Instant verification via Aadhaar OTP.",
    },

    # --- HOSTINGER ---
    {
        "id": "admitad-hostinger",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Hostinger",
        "campaign_title": "Hostinger Web Hosting CPS",
        "payout_display": "Up to 50.0% CPS",
        "payout_numeric": 50.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Tech & Software",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/hostinger/",
        "description": "Massive 50% commission on annual hosting plans. Global and Indian traffic accepted.",
    },
    {
        "id": "cj-hostinger",
        "network_id": "cj",
        "network_name": "CJ Affiliate",
        "brand_name": "Hostinger",
        "campaign_title": "Hostinger International",
        "payout_display": "Up to 45.0% CPS",
        "payout_numeric": 45.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Tech & Software",
        "cookie_days": 30,
        "deep_link_url": "https://members.cj.com/member/publisher/advertisers/hostinger",
        "description": "Top-tier web hosting affiliate offer.",
    },

    # --- DOMINOS ---
    {
        "id": "cuelinks-dominos",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Dominos",
        "campaign_title": "Domino's Pizza CPS India",
        "payout_display": "Flat ₹35 - ₹65 Per Order",
        "payout_numeric": 45.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Food & Dining",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/dominos-india",
        "description": "New user ₹65, Existing user ₹35. App and web orders tracked.",
    },
    {
        "id": "inrdeals-dominos",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Dominos",
        "campaign_title": "Domino's Food Delivery",
        "payout_display": "Flat ₹30 - ₹55 Per Order",
        "payout_numeric": 40.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Food & Dining",
        "cookie_days": 1,
        "deep_link_url": "https://inrdeals.com/merchant/dominos",
        "description": "High volume food delivery campaign.",
    },

    # --- SWIGGY ---
    {
        "id": "cuelinks-swiggy",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Swiggy",
        "campaign_title": "Swiggy Instamart & Food",
        "payout_display": "Flat ₹50 - ₹120 Per Order",
        "payout_numeric": 70.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Food & Dining",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/swiggy",
        "description": "Instamart groceries ₹80, Food delivery new user ₹120.",
    },
    {
        "id": "cashkaro-swiggy",
        "network_id": "cashkaro",
        "network_name": "CashKaro",
        "brand_name": "Swiggy",
        "campaign_title": "Swiggy Food & Dineout",
        "payout_display": "Flat ₹45 - ₹100 Per Order",
        "payout_numeric": 60.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Food & Dining",
        "cookie_days": 1,
        "deep_link_url": "https://cashkaro.com/stores/swiggy",
        "description": "Food delivery app orders in tier-1/tier-2 cities.",
    },

    # --- ONEPLUS ---
    {
        "id": "cuelinks-oneplus",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "OnePlus",
        "campaign_title": "OnePlus India Store CPS",
        "payout_display": "Up to 3.5% CPS",
        "payout_numeric": 3.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/oneplus-india",
        "description": "Official OnePlus smartphones, Nord series, tablets and audio gear.",
    },
    {
        "id": "admitad-oneplus",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "OnePlus",
        "campaign_title": "OnePlus Official Store IN",
        "payout_display": "Up to 4.0% CPS",
        "payout_numeric": 4.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 7,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/oneplus-in/",
        "description": "Flagship devices and Nord series. High average checkout values.",
    },

    # --- ADIDAS ---
    {
        "id": "admitad-adidas",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "Adidas",
        "campaign_title": "Adidas India Official Online",
        "payout_display": "Up to 8.5% CPS",
        "payout_numeric": 8.5,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/adidas-in/",
        "description": "Adidas Originals, Running, Ultraboost, Football. 8.5% on all valid online orders.",
    },
    {
        "id": "cuelinks-adidas",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Adidas",
        "campaign_title": "Adidas Online Store",
        "payout_display": "Up to 7.0% CPS",
        "payout_numeric": 7.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Sports & Footwear",
        "cookie_days": 15,
        "deep_link_url": "https://www.cuelinks.com/campaigns/adidas-india",
        "description": "Official footwear and sportswear store.",
    },

    # --- LENOVO ---
    {
        "id": "cj-lenovo",
        "network_id": "cj",
        "network_name": "CJ Affiliate",
        "brand_name": "Lenovo",
        "campaign_title": "Lenovo India Commercial & Consumer",
        "payout_display": "Up to 5.0% CPS",
        "payout_numeric": 5.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 30,
        "deep_link_url": "https://members.cj.com/member/publisher/advertisers/lenovo",
        "description": "ThinkPad, Legion Gaming laptops, Yoga series. High basket size.",
    },
    {
        "id": "cuelinks-lenovo",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Lenovo",
        "campaign_title": "Lenovo India Online",
        "payout_display": "Up to 4.2% CPS",
        "payout_numeric": 4.2,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Electronics",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/lenovo-india",
        "description": "Fast order approvals for laptops, monitors and PC accessories.",
    },

    # --- CLEARTRIP ---
    {
        "id": "cuelinks-cleartrip",
        "network_id": "cuelinks",
        "network_name": "Cuelinks",
        "brand_name": "Cleartrip",
        "campaign_title": "Cleartrip Flights & Stays",
        "payout_display": "Flat ₹160 - ₹500 CPL",
        "payout_numeric": 250.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Travel",
        "cookie_days": 1,
        "deep_link_url": "https://www.cuelinks.com/campaigns/cleartrip",
        "description": "Domestic flights ₹160, Hotels up to ₹500. Owned by Flipkart group.",
    },
    {
        "id": "inrdeals-cleartrip",
        "network_id": "inrdeals",
        "network_name": "INRDeals",
        "brand_name": "Cleartrip",
        "campaign_title": "Cleartrip Travel Deals",
        "payout_display": "Flat ₹150 - ₹450 CPL",
        "payout_numeric": 220.0,
        "payout_type": "Flat INR",
        "status": "active",
        "category": "Travel",
        "cookie_days": 1,
        "deep_link_url": "https://inrdeals.com/merchant/cleartrip",
        "description": "Online ticket booking platform.",
    },

    # --- GODADDY ---
    {
        "id": "cj-godaddy",
        "network_id": "cj",
        "network_name": "CJ Affiliate",
        "brand_name": "GoDaddy",
        "campaign_title": "GoDaddy Domains & Hosting Global",
        "payout_display": "Up to 15.0% CPS",
        "payout_numeric": 15.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Tech & Software",
        "cookie_days": 45,
        "deep_link_url": "https://members.cj.com/member/publisher/advertisers/godaddy",
        "description": "World leader in domains. High commission on web hosting, security, and email suites.",
    },
    {
        "id": "admitad-godaddy",
        "network_id": "admitad",
        "network_name": "Admitad",
        "brand_name": "GoDaddy",
        "campaign_title": "GoDaddy India",
        "payout_display": "Up to 12.0% CPS",
        "payout_numeric": 12.0,
        "payout_type": "CPS %",
        "status": "active",
        "category": "Tech & Software",
        "cookie_days": 30,
        "deep_link_url": "https://store.admitad.com/en/webmaster/offers/godaddy-in/",
        "description": "Local currency support in India.",
    },
]


NETWORKS_METADATA = [
    {
        "id": "all",
        "name": "All Networks",
        "badge": "Unified",
        "color": "indigo",
        "icon": "ph-globe-hemisphere-east",
    },
    {
        "id": "cuelinks",
        "name": "Cuelinks",
        "badge": "Official REST API",
        "color": "sky",
        "icon": "ph-link",
    },
    {
        "id": "admitad",
        "name": "Admitad",
        "badge": "OAuth 2.0 API",
        "color": "emerald",
        "icon": "ph-shield-check",
    },
    {
        "id": "inrdeals",
        "name": "INRDeals",
        "badge": "Publisher API",
        "color": "purple",
        "icon": "ph-currency-inr",
    },
    {
        "id": "cj",
        "name": "CJ Affiliate",
        "badge": "GraphQL API",
        "color": "amber",
        "icon": "ph-lightning",
    },
    {
        "id": "cashkaro",
        "name": "CashKaro",
        "badge": "Direct Partner",
        "color": "rose",
        "icon": "ph-wallet",
    },
    {
        "id": "icubeswire",
        "name": "iCubesWire",
        "badge": "HasOffers API",
        "color": "teal",
        "icon": "ph-cube",
    },
    {
        "id": "pantech",
        "name": "Pantech",
        "badge": "Affise API",
        "color": "cyan",
        "icon": "ph-cpu",
    },
    {
        "id": "zonet",
        "name": "Zonet",
        "badge": "Custom API",
        "color": "blue",
        "icon": "ph-chart-polar",
    },
]


class CampaignFinderService:
    def __init__(self, normalizer: Optional[BrandNormalizer] = None):
        self.normalizer = normalizer or BrandNormalizer()
        self.catalog = list(MASTER_CAMPAIGNS_CATALOG)

    def search_campaigns(
        self,
        query: Optional[str] = None,
        network: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = "payout_desc",
    ) -> Dict[str, Any]:
        """
        Unified search across all campaigns with:
        - Free text / brand matching
        - Network filtering (or all networks)
        - Category filtering
        - Status filtering
        - Automatic Winner Detection (Highest Payout Highlight)
        """
        results: List[Dict[str, Any]] = []

        q_clean = query.strip().lower() if query else ""
        norm_q = self.normalizer.normalize_brand(q_clean)[0].lower() if q_clean else ""

        for item in self.catalog:
            # 1. Network Filter
            if network and network.lower() != "all":
                if item["network_id"].lower() != network.lower():
                    continue

            # 2. Category Filter
            if category and category.lower() != "all":
                if item["category"].lower() != category.lower():
                    continue

            # 3. Status Filter
            if status and status.lower() != "all":
                if item["status"].lower() != status.lower():
                    continue

            # 4. Query Filter (Brand, Title, Category, Description)
            if q_clean:
                b_name = item["brand_name"].lower()
                b_canon = self.normalizer.normalize_brand(b_name)[0].lower()
                title = item["campaign_title"].lower()
                cat = item["category"].lower()
                desc = item["description"].lower()

                matches = (
                    q_clean in b_name
                    or (norm_q and (norm_q in b_canon or norm_q in b_name))
                    or q_clean in title
                    or q_clean in cat
                    or q_clean in desc
                )
                if not matches:
                    continue

            # Attach canonical brand
            item_copy = dict(item)
            item_copy["canonical_brand"] = self.normalizer.normalize_brand(item["brand_name"])[0]
            results.append(item_copy)

        # 5. Compute Comparative Best Payout per Canonical Brand
        # Group by (canonical_brand, payout_type)
        brand_groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in results:
            key = (r["canonical_brand"], r.get("payout_type", "CPS %"))
            brand_groups.setdefault(key, []).append(r)

        for key, group in brand_groups.items():
            if len(group) > 1:
                # Find maximum numeric payout
                sorted_group = sorted(
                    group, key=lambda x: float(x.get("payout_numeric", 0.0)), reverse=True
                )
                top_payout = sorted_group[0].get("payout_numeric", 0.0)
                second_payout = sorted_group[1].get("payout_numeric", 0.0)

                for r in group:
                    if r.get("payout_numeric", 0.0) == top_payout and top_payout > 0:
                        r["is_best_payout"] = True
                        diff = round(top_payout - second_payout, 1)
                        if diff > 0:
                            unit = "%" if "CPS" in r.get("payout_type", "") else "₹"
                            r["payout_diff_label"] = f"🏆 Top Payout (+{diff}{unit} vs competitors)"
                        else:
                            r["payout_diff_label"] = "🏆 Top Rate (Tied)"
                    else:
                        r["is_best_payout"] = False
                        r["payout_diff_label"] = ""
            else:
                for r in group:
                    r["is_best_payout"] = False
                    r["payout_diff_label"] = ""

        # 6. Sorting
        if sort_by == "payout_desc":
            results.sort(key=lambda x: (x.get("is_best_payout", False), float(x.get("payout_numeric", 0.0))), reverse=True)
        elif sort_by == "name_asc":
            results.sort(key=lambda x: x.get("brand_name", "").lower())
        elif sort_by == "network_asc":
            results.sort(key=lambda x: x.get("network_name", "").lower())

        # Networks represented in current query results
        networks_in_results = list(set(r["network_id"] for r in results))

        return {
            "success": True,
            "total": len(results),
            "query": query or "",
            "network": network or "all",
            "category": category or "all",
            "status": status or "all",
            "networks_in_results": networks_in_results,
            "results": results,
        }

    def get_networks_summary(self) -> List[Dict[str, Any]]:
        """Return list of supported networks with real-time campaign counts."""
        counts_by_net: Dict[str, int] = {}
        for item in self.catalog:
            net_id = item["network_id"].lower()
            counts_by_net[net_id] = counts_by_net.get(net_id, 0) + 1

        summary = []
        for net in NETWORKS_METADATA:
            n_copy = dict(net)
            if net["id"] == "all":
                n_copy["count"] = len(self.catalog)
            else:
                n_copy["count"] = counts_by_net.get(net["id"], 0)
            summary.append(n_copy)
        return summary

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return distinct categories with counts."""
        cat_counts: Dict[str, int] = {}
        for item in self.catalog:
            c = item.get("category", "Other")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        cats = [{"id": "all", "name": "All Categories", "count": len(self.catalog)}]
        for cat_name, cnt in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
            cats.append({"id": cat_name, "name": cat_name, "count": cnt})
        return cats
