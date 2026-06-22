import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Check, Zap, Star, TrendingUp, AlertCircle, Loader, Info } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { initiateUpgrade, getAvailablePlans, getAvailablePaymentMethods } from '../../services/paymentService';
import { useSubscription } from '../../hooks/useSubscription';
import './BillingUpgrade.css';

/**
 * BillingUpgrade Component
 * Displays subscription plans and handles upgrade flow
 * Can pre-select a plan via query parameter (?plan=plus)
 */
const BillingUpgrade = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const { userPlan } = useSubscription();
  const [selectedPlan, setSelectedPlan] = useState(searchParams.get('plan') || 'plus');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [couponCode, setCouponCode] = useState('');
  const [discount, setDiscount] = useState(0);
  const [showDebugInfo, setShowDebugInfo] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [plans, setPlans] = useState([]);
  const [showMethodsModal, setShowMethodsModal] = useState(false);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [selectedMethod, setSelectedMethod] = useState('card');
  const [pendingPlanId, setPendingPlanId] = useState(null);
  const [countryCode, setCountryCode] = useState('US');

  const normalizeApiBase = () => {
    if (import.meta.env.DEV) {
      return '/api/v1';
    }
    const raw = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    const trimmed = raw.replace(/\/+$/, '');
    return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`;
  };

  // Check backend availability on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const healthUrl = `${normalizeApiBase()}/health`;
        
        const response = await fetch(healthUrl, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          },
        });
        setBackendStatus(response.ok ? 'available' : 'offline');
      } catch (err) {
        console.warn('🔍 Backend health check failed:', err.message);
        setBackendStatus('offline');
      }
    };

    checkBackendHealth();
  }, []);

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const data = await getAvailablePlans();
        const serverPlans = Object.entries(data?.plans || {}).map(([id, plan]) => ({
          id,
          name: plan.name || id,
          price: typeof plan.price === 'number' ? plan.price : null,
          period: plan.billing_cycle === 'monthly' ? '/month' : (plan.billing_cycle === 'annual' ? '/year' : ''),
          description: plan.description || '',
          features: Object.entries(plan.features || {})
            .filter(([, enabled]) => Boolean(enabled))
            .map(([feature]) => feature.replace(/_/g, ' ')),
          cta: id === 'enterprise' ? 'Contact Sales' : `Upgrade to ${(plan.name || id)}`,
          highlighted: id === 'professional',
          disabled: false,
          perks: [],
        }));
        setPlans(serverPlans.length ? serverPlans : fallbackPlans);
      } catch (err) {
        console.warn('Failed to load plans from backend, using fallback plans', err);
        setPlans(fallbackPlans);
      }
    };
    loadPlans();
  }, []);

  useEffect(() => {
    const inferCountryCode = () => {
      try {
        const locale = Intl.DateTimeFormat().resolvedOptions().locale || 'en-US';
        const parts = locale.split('-');
        return (parts[1] || 'US').toUpperCase();
      } catch (e) {
        return 'US';
      }
    };
    setCountryCode(inferCountryCode());
  }, []);

  const fallbackPlans = [
    { id: 'personal', name: 'Free', price: 0, period: '/day', features: ['50 AI credits/day', '1 email account'], cta: 'Current Plan', highlighted: false, disabled: false, perks: [] },
    { id: 'plus', name: 'Plus', price: 12, period: '/month', features: ['1,500 AI credits/month', '3 email accounts'], cta: 'Upgrade to Plus', highlighted: true, disabled: false, perks: [] },
    { id: 'professional', name: 'Professional', price: 29, period: '/month', features: ['5,000 AI credits/month', 'Unlimited accounts'], cta: 'Upgrade to Professional', highlighted: false, disabled: false, perks: [] },
    { id: 'enterprise', name: 'Enterprise', price: null, period: 'Custom', features: ['Enterprise features'], cta: 'Contact Sales', highlighted: false, disabled: false, perks: [] },
  ];

  const handleUpgrade = async (planId) => {
    console.log(`🔄 [Billing] Attempting upgrade to plan: ${planId}`);
    
    if (planId === userPlan) {
      setError('You are already on this plan');
      return;
    }

    if (planId === 'personal') {
      setError('You are already on the Free plan, or cannot downgrade here.');
      return;
    }

    if (planId === 'enterprise') {
      console.log('📧 [Billing] Redirecting to sales email');
      window.location.href = 'mailto:sales@bylix.email?subject=Enterprise%20Plan%20Inquiry';
      return;
    }

    // Instead of immediately starting a provider redirect, show the payment-method chooser
    setError(null);
    try {
      setIsProcessing(true);
      const methodsResp = await getAvailablePaymentMethods(countryCode);
      const methods = (methodsResp && methodsResp.payment_methods) || [];
      // Ensure card / Paystack appears first by default when available
      methods.sort((a, b) => {
        if (a.id === 'card') return -1;
        if (b.id === 'card') return 1;
        return 0;
      });
      setPendingPlanId(planId);
      setPaymentMethods(methods);
      setSelectedMethod(methods.length ? (methods[0].id || 'card') : 'card');
      setShowMethodsModal(true);
    } catch (err) {
      console.error('❌ [Billing] Could not load payment methods, falling back to default flow', err);
      // Fallback: continue with original auto flow
      setIsProcessing(true);
      setShowMethodsModal(false);
      try {
        const response = await initiateUpgrade(planId, 'auto', { countryCode, preferLocalCurrency: false });
        if (response.authorization_url) window.location.href = response.authorization_url;
        else if (response.approval_url) window.location.href = response.approval_url;
        else if (response.checkout_url) window.location.href = response.checkout_url;
        else throw new Error('No redirect URL returned');
      } catch (e) {
        setError(e.message || 'Upgrade failed');
      } finally {
        setIsProcessing(false);
      }
    }
    setIsProcessing(false);

    
  };

  const confirmPaymentMethod = async (planId) => {
    setShowMethodsModal(false);
    setIsProcessing(true);
    setError(null);
    try {
      const response = await initiateUpgrade(planId, selectedMethod, { countryCode, preferLocalCurrency: false });
      if (response.authorization_url) {
        window.location.href = response.authorization_url;
      } else if (response.approval_url) {
        window.location.href = response.approval_url;
      } else if (response.checkout_url) {
        window.location.href = response.checkout_url;
      } else if (response.success === true) {
        if (response.mock_mode) throw new Error('Payment providers not configured for real checkout');
        throw new Error('Payment session created without redirect URL.');
      } else {
        throw new Error('Invalid payment service response');
      }
    } catch (err) {
      console.error('❌ [Billing] Confirm payment method error:', err);
      setError(err?.message || 'Failed to start payment');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyCoupon = async (e) => {
    e.preventDefault();
    if (!couponCode.trim()) return;

    setIsProcessing(true);
    try {
      // Mock coupon validation - replace with actual API call
      if (couponCode === 'SAVE10') {
        setDiscount(10);
      } else if (couponCode === 'SAVE20') {
        setDiscount(20);
      } else {
        setError('Invalid coupon code');
        setDiscount(0);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const currentPlan = plans.find(p => p.id === selectedPlan);

  return (
    <div className="billing-upgrade-container">
      {/* Header */}
      <div className="upgrade-header">
        <button 
          className="back-button"
          onClick={() => navigate('/')}
        >
          <ArrowLeft size={20} />
          Back
        </button>
        <div className="header-content">
          <h1>Choose Your Plan</h1>
          <p>Unlock premium features and boost your productivity</p>
        </div>
      </div>

      {/* Current User Info */}
      {user && (
        <div className="user-info">
          <div className="user-details">
            <h3>{user.full_name || user.email}</h3>
            <p>{user.email}</p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <div>
            <h4>Error Processing Request</h4>
            <p>{error}</p>
            {error.includes('backend') && (
              <details style={{ marginTop: '8px', fontSize: '13px' }}>
                <summary>Backend Implementation Required</summary>
                <pre style={{ backgroundColor: '#f1f5f9', padding: '8px', borderRadius: '4px', overflowX: 'auto', marginTop: '8px', fontSize: '12px' }}>{`POST /api/v1/billing/upgrade

Request:
{
  "plan_id": "plus",
  "payment_method": "auto"
}

Response (one of):
{
  "success": true
}`}</pre>
              </details>
            )}
          </div>
        </div>
      )}

      {/* Backend Status Alert */}
      {backendStatus === 'offline' && (
        <div className="info-banner">
          <Info size={20} />
          <div>
            <h4>⚠️ Backend Service Offline</h4>
            <p>The payment backend is not available. To test:</p>
            <ul style={{ marginTop: '8px', marginLeft: '20px', fontSize: '13px' }}>
              <li>1. Ensure your backend is running at http://localhost:8000</li>
              <li>2. Implement the endpoint: POST /api/v1/billing/upgrade</li>
              <li>3. See console for detailed debugging information</li>
            </ul>
            <a href="#" onClick={(e) => { e.preventDefault(); setShowDebugInfo(!showDebugInfo); }} style={{ fontSize: '12px', color: '#6366f1', marginTop: '8px', display: 'inline-block' }}>
              {showDebugInfo ? 'Hide Debug Info' : 'Show Debug Info'}
            </a>
          </div>
        </div>
      )}

      {/* Debug Information */}
      {showDebugInfo && (
        <div className="debug-panel">
          <h4>🔧 Debug Information</h4>
          <div className="debug-row">
            <span>Backend Status:</span>
            <span>{backendStatus}</span>
          </div>
          <div className="debug-row">
            <span>API Base URL:</span>
            <span>{import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}</span>
          </div>
          <div className="debug-row">
            <span>Paystack Key:</span>
            <span>{import.meta.env.VITE_PAYSTACK_PUBLIC_KEY ? '✓ Configured' : '✗ Not configured'}</span>
          </div>
          <div className="debug-row">
            <span>Auth Token:</span>
            <span>{localStorage.getItem('auth_token') ? '✓ Present' : '✗ Missing'}</span>
          </div>
          <div className="debug-row">
            <span>User Plan:</span>
            <span>{userPlan || 'personal'}</span>
          </div>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '12px' }}>
            Open browser DevTools (F12) Console tab for detailed request/response logs.
          </p>
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Checkout Setup</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-600 mb-1">Country</label>
            <input
              value={countryCode}
              onChange={(e) => setCountryCode((e.target.value || 'US').toUpperCase().slice(0, 2))}
              className="w-full px-3 py-2 border border-slate-300 rounded"
              maxLength={2}
            />
          </div>
          <div className="flex items-end">
            <p className="text-xs text-slate-500">
              Clicking <strong>Upgrade</strong> opens hosted checkout with card as default; users can switch to other available methods there.
            </p>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Default is exact USD charging to match website pricing; provider fallback applies automatically when required.
        </p>
      </div>

      {/* Plans Grid */}
      <div className="plans-grid">
        {plans.map((plan, idx) => (
          <div
            key={plan.id}
            className={`plan-card ${plan.highlighted ? 'highlighted' : ''} ${selectedPlan === plan.id ? 'selected' : ''}`}
          >
            {plan.highlighted && <div className="popular-badge">Most Popular</div>}
            
            <div className="plan-header">
              <h3>{plan.name}</h3>
              <p className="plan-description">{plan.description}</p>
            </div>

            <div className="plan-pricing">
              {plan.price !== null ? (
                <>
                  <span className="price">${plan.price}</span>
                  <span className="period">{plan.period}</span>
                  <div className="text-xs text-slate-500">~ KES {Math.round(Number(plan.price || 0) * 150)}</div>
                </>
              ) : (
                <span className="price-custom">Custom Pricing</span>
              )}
            </div>

            {plan.perks.length > 0 && (
              <div className="plan-perks">
                {plan.perks.map((perk, i) => (
                  <div key={i} className="perk">
                    <Star size={14} />
                    <span>{perk}</span>
                  </div>
                ))}
              </div>
            )}

            <button
              className={`plan-cta ${plan.highlighted ? 'highlighted' : ''}`}
              onClick={() => handleUpgrade(plan.id)}
              disabled={isProcessing || plan.disabled}
              title={plan.disabled ? 'Not available' : `Upgrade to ${plan.name}`}
            >
              {isProcessing && <Loader size={16} className="spinner" />}
              {isProcessing ? 'Processing...' : plan.cta}
            </button>

            <div className="features-divider"></div>

            <ul className="plan-features">
              {plan.features.map((feature, i) => (
                <li key={i}>
                  <Check size={18} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Payment Methods Modal */}
      {showMethodsModal && (
        <div className="modal-backdrop">
          <div className="modal-panel">
            <h3>Select payment method</h3>
            <p className="text-sm text-slate-600">Card is selected by default. You can switch to other available methods.</p>
            <div className="methods-list">
              {paymentMethods.length ? paymentMethods.map((m) => (
                <label key={m.id} className="method-row">
                  <input
                    type="radio"
                    name="payment_method"
                    value={m.id}
                    checked={selectedMethod === m.id}
                    onChange={() => setSelectedMethod(m.id)}
                  />
                  <div className="method-info">
                    <strong>{m.name || m.id}</strong>
                    <div className="method-desc">{m.description || m.processor || ''}</div>
                  </div>
                </label>
              )) : (
                <p>No payment methods available</p>
              )}
            </div>
            <div className="modal-actions">
              <button className="btn btn-default" onClick={() => { setShowMethodsModal(false); setPaymentMethods([]); setPendingPlanId(null); }}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={() => confirmPaymentMethod(pendingPlanId)} disabled={!selectedMethod || isProcessing}>
                {isProcessing ? 'Processing...' : 'Continue to payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FAQ Section */}
      <div className="faq-section">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-grid">
          <div className="faq-item">
            <h4>Can I change my plan anytime?</h4>
            <p>Yes! You can upgrade or downgrade your plan at any time. Changes take effect at the start of your next billing cycle.</p>
          </div>
          <div className="faq-item">
            <h4>What payment methods do you accept?</h4>
            <p>We accept major cards and local payment methods through Paystack and supported regional processors.</p>
          </div>
          <div className="faq-item">
            <h4>Is there a free trial?</h4>
            <p>Start with our free Personal plan. Upgrade anytime to access more features and credits without a trial period.</p>
          </div>
          <div className="faq-item">
            <h4>Do you offer refunds?</h4>
            <p>We offer a 14-day money-back guarantee if you're not satisfied. Contact our support team for assistance.</p>
          </div>
          <div className="faq-item">
            <h4>What are AI Credits used for?</h4>
            <p>AI Credits power our intelligent features including email suggestions, smart replies, and automated categorization.</p>
          </div>
          <div className="faq-item">
            <h4>Can I get a custom plan?</h4>
            <p>Absolutely! Contact our sales team for enterprise solutions tailored to your organization's needs.</p>
          </div>
        </div>
      </div>

      {/* Help Footer */}
      <div className="help-footer">
        <div className="help-item">
          <Zap size={20} />
          <div>
            <h4>Need Help?</h4>
            <p>Contact our support team at support@bylix.email or call +1 (555) 123-4567</p>
          </div>
        </div>
        <div className="help-item">
          <TrendingUp size={20} />
          <div>
            <h4>Special Discounts</h4>
            <p>Annual billing is available with 20% discount. Contact sales for details.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BillingUpgrade;
