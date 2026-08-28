from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.billing_models import (
    CREDIT_PACK_PRICING_USD,
    Payment,
)
from app.services.billing.credits import CreditService
from app.services.billing.paypal import (
    BybitPayService,
    CoinbaseCommerceService,
    PayPalService,
    StripeService,
)
from app.services.billing.paystack import PaystackService


class PaymentInfrastructureMixin:
    def __init__(self):
        self.paystack = PaystackService()
        self.paypal = PayPalService()
        self.coinbase = CoinbaseCommerceService()
        self.bybit = BybitPayService()
        self.stripe = StripeService()
        self.credit_service = CreditService()
        self._fx_rate_cache: Dict[str, Dict[str, Any]] = {}

    async def _create_payment_row(
        self,
        session: AsyncSession,
        user_id: str,
        provider: str,
        amount_usd: float,
        currency: str,
        reference: Optional[str],
        status: str = "pending",
    ) -> None:
        if not reference:
            return

        existing_res = await session.execute(select(Payment).where(Payment.reference == reference))
        if existing_res.scalar_one_or_none():
            return

        payment = Payment(
            user_id=user_id,
            provider=provider,
            amount=amount_usd,
            currency=currency,
            status=status,
            reference=reference,
        )
        session.add(payment)

    def get_credit_pack_price_usd(self, credits: int) -> Optional[float]:
        return CREDIT_PACK_PRICING_USD.get(int(credits))

    def _is_paystack_configured(self) -> bool:
        if settings.ENABLE_MOCK_MODE:
            return True
        api_key = self.paystack.api_key or ""
        # Server-side Paystack calls require secret key (sk_*)
        return bool(api_key and api_key.startswith("sk_"))

    def _is_paypal_configured(self) -> bool:
        return bool(self.paypal.client_id and self.paypal.client_secret)

    def _is_coinbase_configured(self) -> bool:
        return bool(self.coinbase.api_key)

    def _is_bybit_configured(self) -> bool:
        return self.bybit.is_configured()

    def _is_stripe_configured(self) -> bool:
        return self.stripe.is_configured()

    def _paystack_supported_currencies(self) -> set:
        raw = (settings.PAYSTACK_SUPPORTED_CURRENCIES or "").strip()
        values = {item.strip().upper() for item in raw.split(",") if item.strip()}
        return values or {"NGN"}

    def _conversion_rate_for_currency_fallback(self, currency: str) -> float:
        rates = {
            "USD": 1,
            "NGN": 1500,
            "KES": 150,
            "GHS": 13,
            "ZAR": 19,
            "UGX": 4000,
            "TZS": 2500,
            "RWF": 1300,
        }
        return float(rates.get((currency or "USD").upper(), 1))

    async def _conversion_rate_for_currency(self, currency: str) -> float:
        target = (currency or "USD").upper()
        if target == "USD":
            return 1.0

        if settings.ENABLE_MOCK_MODE or not settings.ENABLE_LIVE_FX_RATES:
            return self._conversion_rate_for_currency_fallback(target)

        now = datetime.utcnow()
        cache_minutes = max(1, int(getattr(settings, "FX_RATE_CACHE_MINUTES", 15) or 15))
        cached = self._fx_rate_cache.get(target)
        if cached and isinstance(cached.get("ts"), datetime):
            if now - cached["ts"] < timedelta(minutes=cache_minutes):
                return float(cached.get("rate", 1.0))

        try:
            api_base = (settings.FX_RATE_API_BASE_URL or "https://api.exchangerate.host").rstrip("/")
            params = {"from": "USD", "to": target, "amount": 1}
            if settings.FX_RATE_API_KEY:
                params["access_key"] = settings.FX_RATE_API_KEY

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{api_base}/convert", params=params)
                resp.raise_for_status()
                data = resp.json() or {}

            rate = None
            info = data.get("info") if isinstance(data, dict) else None
            if isinstance(info, dict):
                rate = info.get("rate")
            if rate is None:
                result = data.get("result") if isinstance(data, dict) else None
                if isinstance(result, (int, float)):
                    rate = result

            if isinstance(rate, (int, float)) and float(rate) > 0:
                self._fx_rate_cache[target] = {"rate": float(rate), "ts": now}
                return float(rate)

        except Exception as e:
            logger.warning(
                f"⚠️ [PaymentService] Live FX lookup failed for USD->{target}; using fallback rate. Error={str(e)}"
            )

        return self._conversion_rate_for_currency_fallback(target)

    def _is_currency_unsupported_error(self, message: str) -> bool:
        text = (message or "").lower()
        return "currency" in text and "supported" in text

    def _paystack_charge_currency(self, detected_local_currency: str = "USD") -> str:
        """
        Determine actual currency to send to Paystack.
        If PAYSTACK_FORCE_CURRENCY is set, it always wins (e.g., KES settlement strategy).
        """
        forced = (settings.PAYSTACK_FORCE_CURRENCY or "").strip().upper()
        if forced:
            return forced
        return (detected_local_currency or "USD").upper()

    async def detect_country_code_from_ip(self, ip_address: Optional[str]) -> str:
        """Resolve ISO country code from IP with safe fallback to US."""
        if settings.ENABLE_MOCK_MODE or not settings.ENABLE_GEOIP_DETECTION:
            return "US"

        ip = (ip_address or "").strip()
        if not ip or ip in {"127.0.0.1", "::1", "localhost"}:
            return "US"

        try:
            base = (settings.GEOIP_API_BASE_URL or "https://ipapi.co").rstrip("/")
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"{base}/{ip}/json/")
                resp.raise_for_status()
                data = resp.json() or {}
            country = (data.get("country_code") or "US").upper()
            return country if len(country) == 2 else "US"
        except Exception as e:
            logger.warning(f"⚠️ [PaymentService] GeoIP lookup failed for ip={ip}: {str(e)}")
            return "US"

    def get_available_payment_methods(self, country_code: str) -> list:
        """
        Get available payment methods based on user's country

        Args:
            country_code: ISO 2-letter country code (e.g., "KE", "NG", "US")

        Returns:
            List of available payment method dictionaries
        """
        # Paystack coverage: Africa (Nigeria, Kenya, Ghana, South Africa, etc.)
        paystack_countries = {
            "NG": "Nigeria",  # Paystack primary market
            "KE": "Kenya",  # M-Pesa support
            "GH": "Ghana",  # Mobile Money
            "ZA": "South Africa",  # Mobile Money
            "UG": "Uganda",
            "TZ": "Tanzania",
            "RW": "Rwanda",
        }

        country_code = country_code.upper() if country_code else "US"

        methods = []

        # Determine which processors to use
        use_paystack = country_code in paystack_countries and self._is_paystack_configured()
        use_paypal = self._is_paypal_configured()

        if use_paystack:
            # Paystack methods by country
            if country_code == "KE":
                methods.extend(
                    [
                        {"id": "mpesa", "name": "M-Pesa", "processor": "paystack", "region": "Kenya"},
                        {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Global"},
                        {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Kenya"},
                    ]
                )
            elif country_code == "NG":
                methods.extend(
                    [
                        {"id": "card", "name": "Visa/Mastercard/Verve", "processor": "paystack", "region": "Nigeria"},
                        {"id": "ussd", "name": "USSD", "processor": "paystack", "region": "Nigeria"},
                        {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Nigeria"},
                        {"id": "qr", "name": "QR Payment", "processor": "paystack", "region": "Nigeria (optional)"},
                    ]
                )
            elif country_code == "GH":
                methods.extend(
                    [
                        {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Ghana"},
                        {
                            "id": "mobile_money",
                            "name": "MTN Mobile Money | AirtelTigo",
                            "processor": "paystack",
                            "region": "Ghana",
                        },
                        {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Ghana"},
                    ]
                )
            elif country_code == "ZA":
                methods.extend(
                    [
                        {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "South Africa"},
                        {
                            "id": "mobile_money",
                            "name": "Vodacom Mobile Money",
                            "processor": "paystack",
                            "region": "South Africa",
                        },
                        {
                            "id": "bank_transfer",
                            "name": "Bank Transfer",
                            "processor": "paystack",
                            "region": "South Africa",
                        },
                    ]
                )
            else:
                # Default Paystack methods for other African countries
                methods.extend(
                    [
                        {"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Africa"},
                        {"id": "mobile_money", "name": "Mobile Money", "processor": "paystack", "region": "Africa"},
                        {"id": "bank_transfer", "name": "Bank Transfer", "processor": "paystack", "region": "Africa"},
                    ]
                )

        # Global card rails and wallets
        if use_paypal:
            methods.extend(
                [
                    {
                        "id": "paypal",
                        "name": "PayPal",
                        "processor": "paypal",
                        "description": "PayPal wallet, cards, bank transfer",
                        "region": "Global",
                    },
                    {
                        "id": "apple_pay",
                        "name": "Apple Pay",
                        "processor": "paypal",
                        "description": "Apple Pay via PayPal checkout",
                        "region": "Global",
                    },
                    {
                        "id": "google_pay",
                        "name": "Google Pay",
                        "processor": "paypal",
                        "description": "Google Pay via PayPal checkout",
                        "region": "Global",
                    },
                ]
            )
        # Add PayPal as fallback/primary for non-Paystack regions
        if use_paypal:
            methods.append(
                {
                    "id": "card_international",
                    "name": "International Cards",
                    "processor": "paypal",
                    "description": "Visa, Mastercard, Amex, Discover",
                    "region": "Global",
                }
            )
            methods.extend(
                [
                    {"id": "sepa_debit", "name": "SEPA Direct Debit", "processor": "paypal", "region": "Europe"},
                    {"id": "ideal", "name": "iDEAL", "processor": "paypal", "region": "Netherlands"},
                    {"id": "sofort", "name": "Sofort", "processor": "paypal", "region": "Germany/Austria"},
                    {"id": "bancontact", "name": "Bancontact", "processor": "paypal", "region": "Belgium"},
                    {"id": "eps", "name": "EPS", "processor": "paypal", "region": "Austria"},
                    {"id": "p24", "name": "Przelewy24", "processor": "paypal", "region": "Poland"},
                    {"id": "blik", "name": "BLIK", "processor": "paypal", "region": "Poland"},
                    {"id": "multibanco", "name": "Multibanco", "processor": "paypal", "region": "Portugal"},
                    {"id": "pix", "name": "PIX", "processor": "paypal", "region": "Brazil"},
                    {"id": "boleto", "name": "Boleto", "processor": "paypal", "region": "Brazil"},
                    {"id": "alipay", "name": "Alipay", "processor": "paypal", "region": "China"},
                    {"id": "wechat_pay", "name": "WeChat Pay", "processor": "paypal", "region": "China"},
                    {"id": "upi", "name": "UPI", "processor": "paypal", "region": "India"},
                    {"id": "net_banking", "name": "NetBanking", "processor": "paypal", "region": "India"},
                    {"id": "paytm", "name": "Paytm Wallet", "processor": "paypal", "region": "India"},
                    {"id": "grabpay", "name": "GrabPay", "processor": "paypal", "region": "Southeast Asia"},
                    {"id": "gcash", "name": "GCash", "processor": "paypal", "region": "Philippines"},
                    {"id": "paynow", "name": "PayNow", "processor": "paypal", "region": "Singapore"},
                    {"id": "fpx", "name": "FPX", "processor": "paypal", "region": "Malaysia"},
                    {"id": "klarna", "name": "Klarna", "processor": "paypal", "region": "Global"},
                    {"id": "afterpay", "name": "Afterpay/Clearpay", "processor": "paypal", "region": "Global"},
                ]
            )

        # Add crypto options globally (powered by Bybit Pay when configured)
        if self._is_bybit_configured() or self._is_coinbase_configured():
            methods.extend(
                [
                    {
                        "id": "crypto",
                        "name": "Crypto (auto)",
                        "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                        "description": "Pay with supported assets via Bybit Pay",
                        "region": "Global",
                    },
                    {
                        "id": "crypto_btc",
                        "name": "Bitcoin (BTC)",
                        "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                        "description": "Bitcoin payment",
                        "region": "Global",
                    },
                    {
                        "id": "crypto_eth",
                        "name": "Ethereum (ETH)",
                        "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                        "description": "Ethereum payment",
                        "region": "Global",
                    },
                    {
                        "id": "crypto_usdc",
                        "name": "USDC",
                        "processor": "bybit" if self._is_bybit_configured() else "coinbase",
                        "description": "USD Coin stablecoin payment",
                        "region": "Global",
                    },
                ]
            )

        # Absolute fallback: if no region-specific option exists but Paystack is configured,
        # still expose card checkout so upgrades can proceed.
        if not methods and self._is_paystack_configured():
            methods.append({"id": "card", "name": "Debit/Credit Card", "processor": "paystack", "region": "Global"})

        return methods

    async def get_currency_for_country(self, country_code: str) -> tuple:
        """
        Get the currency and conversion rate for a country

        Args:
            country_code: ISO 2-letter country code

        Returns:
            Tuple of (currency_code, amount_in_local_currency)
        """
        country_code = country_code.upper() if country_code else "US"

        # Currency mappings and approximate USD conversion rates
        currencies = {
            "NG": ("NGN", 1500),  # Nigerian Naira (1 USD = ~1500 NGN)
            "KE": ("KES", 150),  # Kenyan Shilling (1 USD = ~150 KES)
            "GH": ("GHS", 13),  # Ghanaian Cedi (1 USD = ~13 GHS)
            "ZA": ("ZAR", 19),  # South African Rand (1 USD = ~19 ZAR)
            "UG": ("UGX", 4000),  # Ugandan Shilling
            "TZ": ("TZS", 2500),  # Tanzanian Shilling
            "RW": ("RWF", 1300),  # Rwandan Franc
        }

        if country_code in currencies:
            currency, _ = currencies[country_code]
            rate = await self._conversion_rate_for_currency(currency)
            return currency, rate
        return "USD", 1  # Default to USD

    def _paystack_channels_for_method(self, payment_method: str) -> Optional[List[str]]:
        """
        Map frontend payment method to Paystack channels.
        """
        channel_map = {
            "card": ["card"],
            "mpesa": ["mobile_money"],
            "mobile_money": ["mobile_money"],
            "bank_transfer": ["bank_transfer"],
            "ussd": ["ussd"],
            "qr": ["qr"],
        }
        return channel_map.get(payment_method)
