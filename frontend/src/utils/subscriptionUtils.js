/**
 * Subscription and Feature Limits Utility
 * Defines feature access based on subscription plans
 */

const PLAN_LIMITS = {
  personal: {
    name: 'Personal',
    price: 0,
    aiCredits: 100,
    emailAccounts: 1,
    contacts: 500,
    workflowAutomations: 3,
    campaignSize: 50,
    features: {
      basicInbox: true,
      emailSync: true,
      basicInsights: false,
      advancedWorkflows: false,
      campaigns: false,
      teamCollaboration: false,
      customDomains: false,
      apiAccess: false,
      webhooks: false,
      prioritySupport: false,
    }
  },
  plus: {
    name: 'Plus',
    price: 29,
    aiCredits: 1000,
    emailAccounts: 3,
    contacts: 2500,
    workflowAutomations: 10,
    campaignSize: 500,
    features: {
      basicInbox: true,
      emailSync: true,
      basicInsights: true,
      advancedWorkflows: true,
      campaigns: true,
      teamCollaboration: false,
      customDomains: false,
      apiAccess: false,
      webhooks: false,
      prioritySupport: false,
    }
  },
  professional: {
    name: 'Professional',
    price: 79,
    aiCredits: 5000,
    emailAccounts: 10,
    contacts: 50000,
    workflowAutomations: 50,
    campaignSize: 5000,
    features: {
      basicInbox: true,
      emailSync: true,
      basicInsights: true,
      advancedWorkflows: true,
      campaigns: true,
      teamCollaboration: true,
      customDomains: true,
      apiAccess: true,
      webhooks: true,
      prioritySupport: false,
    }
  },
  enterprise: {
    name: 'Enterprise',
    price: null,
    aiCredits: Infinity,
    emailAccounts: Infinity,
    contacts: Infinity,
    workflowAutomations: Infinity,
    campaignSize: Infinity,
    features: {
      basicInbox: true,
      emailSync: true,
      basicInsights: true,
      advancedWorkflows: true,
      campaigns: true,
      teamCollaboration: true,
      customDomains: true,
      apiAccess: true,
      webhooks: true,
      prioritySupport: true,
    }
  }
};

/**
 * Get plan limit object for a given plan
 * @param {string} planId - Plan identifier (personal, plus, professional, enterprise)
 * @returns {object} Plan limit object
 */
export const getPlanLimits = (planId = 'personal') => {
  return PLAN_LIMITS[planId?.toLowerCase()] || PLAN_LIMITS.personal;
};

/**
 * Check if user has reached a limit
 * @param {number} currentUsage - Current usage count
 * @param {number} limit - Plan limit
 * @returns {boolean} True if limit reached
 */
export const hasReachedLimit = (currentUsage, limit) => {
  return currentUsage >= limit;
};

/**
 * Check if user is approaching a limit (80%+ usage)
 * @param {number} currentUsage - Current usage count
 * @param {number} limit - Plan limit
 * @returns {boolean} True if approaching limit
 */
export const isApproachingLimit = (currentUsage, limit) => {
  return currentUsage >= limit * 0.8;
};

/**
 * Get percentage of limit used
 * @param {number} currentUsage - Current usage count
 * @param {number} limit - Plan limit
 * @returns {number} Percentage (0-100)
 */
export const getLimitPercentage = (currentUsage, limit) => {
  if (limit === Infinity) return 0;
  return Math.min((currentUsage / limit) * 100, 100);
};

/**
 * Check if user can access a feature
 * @param {string} planId - User's current plan
 * @param {string} featureName - Feature to check
 * @returns {boolean} True if feature is available
 */
export const canAccessFeature = (planId = 'personal', featureName) => {
  const plan = getPlanLimits(planId);
  return plan.features[featureName] || false;
};

/**
 * Get required plan to access a feature
 * @param {string} featureName - Feature to check
 * @returns {string} Minimum required plan
 */
export const getRequiredPlanForFeature = (featureName) => {
  const featurePlanMap = {
    basicInsights: 'plus',
    advancedWorkflows: 'plus',
    campaigns: 'plus',
    teamCollaboration: 'professional',
    customDomains: 'professional',
    apiAccess: 'professional',
    webhooks: 'professional',
    prioritySupport: 'enterprise',
  };
  return featurePlanMap[featureName] || 'professional';
};

/**
 * Get upgrade suggestion based on usage
 * @param {number} aiCreditsUsed - AI credits used
 * @param {number} aiCreditsLimit - AI credits limit
 * @param {number} emailAccountsUsed - Email accounts used
 * @param {number} emailAccountsLimit - Email accounts limit
 * @returns {object} Upgrade suggestion with reason
 */
export const getUpgradeSuggestion = (
  aiCreditsUsed = 0,
  aiCreditsLimit = 100,
  emailAccountsUsed = 0,
  emailAccountsLimit = 1
) => {
  const creditsPercentage = (aiCreditsUsed / aiCreditsLimit) * 100;
  const accountsPercentage = (emailAccountsUsed / emailAccountsLimit) * 100;

  let reason = null;
  let priority = 'low';

  if (creditsPercentage >= 95) {
    reason = 'AI credits';
    priority = 'critical';
  } else if (accountsPercentage >= 95) {
    reason = 'email accounts';
    priority = 'critical';
  } else if (creditsPercentage >= 80) {
    reason = 'AI credits';
    priority = 'high';
  } else if (accountsPercentage >= 80) {
    reason = 'email accounts';
    priority = 'high';
  }

  return {
    shouldUpgrade: priority !== 'low',
    reason,
    priority,
    creditsPercentage: Math.min(creditsPercentage, 100),
    accountsPercentage: Math.min(accountsPercentage, 100),
  };
};

/**
 * Get recommended plan based on usage
 * @param {string} currentPlan - Current plan
 * @param {object} usage - Current usage object
 * @returns {string} Recommended plan
 */
export const getRecommendedPlan = (currentPlan = 'personal', usage = {}) => {
  const {
    aiCreditsUsed = 0,
    emailAccountsUsed = 0,
    workflowsCreated = 0,
  } = usage;

  // If approaching Plus limits, recommend Professional
  if (currentPlan === 'plus') {
    if (aiCreditsUsed > 800 || emailAccountsUsed > 2) {
      return 'professional';
    }
  }

  // If on Personal, recommend Plus
  if (currentPlan === 'personal') {
    if (aiCreditsUsed > 80 || emailAccountsUsed > 0 || workflowsCreated > 0) {
      return 'plus';
    }
  }

  return currentPlan;
};

/**
 * Format limit for display
 * @param {number} limit - Limit value
 * @returns {string} Formatted limit string
 */
export const formatLimit = (limit) => {
  if (limit === Infinity) return 'Unlimited';
  if (limit >= 1000) return `${(limit / 1000).toFixed(1)}k`;
  return limit.toString();
};

export default {
  getPlanLimits,
  hasReachedLimit,
  isApproachingLimit,
  getLimitPercentage,
  canAccessFeature,
  getRequiredPlanForFeature,
  getUpgradeSuggestion,
  getRecommendedPlan,
  formatLimit,
};
