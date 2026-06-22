/**
 * Payment Processing Service
 * Handles Paystack payment flows
 */

import api from './api';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Initiate premium subscription upgrade
 * @param {string} planId - Plan to upgrade to (plus, professional, enterprise)
 * @param {string} paymentMethod - Payment method (card, mpesa, bank_transfer, etc.)
 * @returns {Promise<object>} Session or checkout data
 */
export const initiateUpgrade = async (
  planId,
  paymentMethod = 'auto',
  options = {}
) => {
  try {
    const {
      countryCode = 'US',
      preferLocalCurrency = false,
    } = options;

    const payload = {
      plan_id: planId,
      country_code: countryCode,
      prefer_local_currency: preferLocalCurrency,
    };
    if (paymentMethod) {
      payload.payment_method = paymentMethod;
    }

    const response = await api.post('/billing/upgrade', payload);

    return response.data;
  } catch (error) {
    console.error('Upgrade initiation error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Get current subscription status
 * @returns {Promise<object>} Subscription data
 */
export const getSubscription = async () => {
  try {
    const response = await api.get('/billing/subscription');
    return response.data;
  } catch (error) {
    console.error('Subscription fetch error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Get current credit usage
 * @returns {Promise<object>} Credit usage data
 */
export const getCreditUsage = async () => {
  try {
    const response = await api.get('/billing/credits');
    return response.data;
  } catch (error) {
    console.error('Credit usage fetch error:', error.response?.data || error.message || error);
    throw error;
  }
};

export const getAvailablePlans = async () => {
  try {
    const response = await api.get('/billing/plans');
    return response.data;
  } catch (error) {
    console.error('Plans fetch error:', error.response?.data || error.message || error);
    throw error;
  }
};

export const getAvailablePaymentMethods = async (countryCode = 'US') => {
  try {
    const response = await api.get(`/billing/payment-methods/${countryCode}`);
    return response.data;
  } catch (error) {
    console.error('Payment methods fetch error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Initialize Paystack payment
 * Opens Paystack checkout modal
 * @param {object} paymentData - Payment data from backend
 * @param {function} onSuccess - Callback on successful payment
 * @param {function} onError - Callback on payment error
 */
export const processPaystackPayment = (paymentData, onSuccess, onError) => {
  if (!window.PaystackPop) {
    console.error('Paystack not loaded');
    onError(new Error('Paystack not loaded'));
    return;
  }

  const handler = window.PaystackPop.setup({
    key: import.meta.env.VITE_PAYSTACK_PUBLIC_KEY,
    email: paymentData.email,
    amount: paymentData.amount * 100, // Amount in kobo
    ref: paymentData.reference,
    plan: paymentData.plan_code,
    onClose: () => {
      onError(new Error('Payment cancelled'));
    },
    onSuccess: (response) => {
      onSuccess(response);
    },
  });

  handler.openIframe();
};

/**
 * Cancel subscription
 * @returns {Promise<object>} Cancellation response
 */
export const cancelSubscription = async () => {
  try {
    const response = await api.post('/billing/cancel');
    return response.data;
  } catch (error) {
    console.error('Cancellation error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Update payment method
 * @param {string} paymentMethod - New payment method
 * @returns {Promise<object>} Updated subscription data
 */
export const updatePaymentMethod = async (paymentMethod) => {
  try {
    const response = await api.put('/billing/payment-method', { payment_method: paymentMethod });
    return response.data;
  } catch (error) {
    console.error('Payment method update error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Get billing history
 * @returns {Promise<array>} Array of billing records
 */
export const getBillingHistory = async () => {
  try {
    const response = await api.get('/billing/history');
    return response.data;
  } catch (error) {
    console.error('Billing history fetch error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Validate coupon/promo code
 * @param {string} code - Coupon code
 * @returns {Promise<object>} Coupon details
 */
export const validateCoupon = async (code) => {
  try {
    const response = await api.post('/billing/coupon/validate', { code });
    return response.data;
  } catch (error) {
    console.error('Coupon validation error:', error.response?.data || error.message || error);
    throw error;
  }
};

/**
 * Apply coupon to account
 * @param {string} code - Coupon code
 * @returns {Promise<object>} Updated subscription with discount
 */
export const applyCoupon = async (code) => {
  try {
    const response = await api.post('/billing/coupon/apply', { code });
    return response.data;
  } catch (error) {
    console.error('Coupon apply error:', error.response?.data || error.message || error);
    throw error;
  }
};

export default {
  initiateUpgrade,
  getSubscription,
  getCreditUsage,
  getAvailablePlans,
  getAvailablePaymentMethods,
  processPaystackPayment,
  cancelSubscription,
  updatePaymentMethod,
  getBillingHistory,
  validateCoupon,
  applyCoupon,
};
