import { useState, useCallback, useMemo, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getUpgradeSuggestion, canAccessFeature, getPlanLimits } from '../utils/subscriptionUtils';
import { getDismissalResetInfo } from '../services/adminService';

/**
 * useSubscription Hook
 * Manages subscription state, limits, and premium prompts
 * 
 * @returns {object} Subscription management object
 */
export const useSubscription = () => {
  const { user } = useAuth();
  const isSuperAdmin = useMemo(
    () => Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser),
    [user]
  );
  const [showPremiumPrompt, setShowPremiumPrompt] = useState(false);
  const [promptType, setPromptType] = useState('credits'); // credits, emails, contacts, workflows
  const [creditWarning, setCreditWarning] = useState(false);
  const [dismissedPrompts, setDismissedPrompts] = useState(() => {
    try {
      const raw = sessionStorage.getItem('dismissedPremiumPrompts');
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch (e) {
      return new Set();
    }
  });

  // On mount, check server-side dismissal reset timestamp and clear session dismissals if needed
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await getDismissalResetInfo();
        const serverReset = res?.reset_at || null;
        if (!serverReset) return;

        const localSeen = sessionStorage.getItem('dismissedPremiumPromptsResetAt') || null;
        if (!localSeen || new Date(serverReset) > new Date(localSeen)) {
          // Clear local dismissals
          sessionStorage.removeItem('dismissedPremiumPrompts');
          sessionStorage.setItem('dismissedPremiumPromptsResetAt', serverReset);
          if (mounted) setDismissedPrompts(new Set());
        }
      } catch (e) {
        // ignore network/errors
      }
    })();
    return () => { mounted = false; };
  }, []);

  // Get user's current plan and limits
  const userPlan = useMemo(() => {
    if (isSuperAdmin) return 'enterprise';
    return user?.subscription?.plan || user?.plan || 'personal';
  }, [isSuperAdmin, user]);
  
  const planLimits = useMemo(() => {
    const limits = {
      personal: {
        name: 'Free',
        aiCredits: 50,
        emailAccounts: 1,
        contacts: 500,
        workflowAutomations: 3,
      },
      plus: {
        name: 'Plus',
        aiCredits: 1500,
        emailAccounts: 3,
        contacts: 2500,
        workflowAutomations: 10,
      },
      professional: {
        name: 'Professional',
        aiCredits: 5000,
        emailAccounts: Infinity,
        contacts: 50000,
        workflowAutomations: 50,
      },
      enterprise: {
        name: 'Enterprise',
        aiCredits: Infinity,
        emailAccounts: Infinity,
        contacts: Infinity,
        workflowAutomations: Infinity,
      },
    };
    return limits[userPlan] || limits.personal;
  }, [userPlan]);

  // Check credit limit
  const checkCreditLimit = useCallback((creditsUsed) => {
    if (isSuperAdmin) return true;
    if (creditsUsed >= planLimits.aiCredits) {
      setPromptType('credits');
      // only show if user hasn't dismissed this prompt type for the session
      if (!dismissedPrompts.has('credits')) {
        setShowPremiumPrompt(true);
      }
      return false;
    }
    // If usage returned below limit, clear any previous dismissal so future overages will re-show prompt
    if (dismissedPrompts.has('credits') && creditsUsed < planLimits.aiCredits) {
      setDismissedPrompts(prev => {
        const next = new Set(prev);
        next.delete('credits');
        try {
          sessionStorage.setItem('dismissedPremiumPrompts', JSON.stringify(Array.from(next)));
        } catch (e) {}
        return next;
      });
    }
    
    // Show warning at 80%
    if (creditsUsed >= planLimits.aiCredits * 0.8) {
      setCreditWarning(true);
      return true;
    }
    
    setCreditWarning(false);
    return true;
  }, [isSuperAdmin, planLimits.aiCredits, dismissedPrompts]);

  // Check email account limit
  const checkEmailAccountLimit = useCallback((accountsUsed) => {
    if (isSuperAdmin) return true;
    if (accountsUsed >= planLimits.emailAccounts) {
      setPromptType('emails');
      setShowPremiumPrompt(true);
      return false;
    }
    return true;
  }, [isSuperAdmin, planLimits.emailAccounts]);

  // Check contact limit
  const checkContactLimit = useCallback((contactsUsed) => {
    if (isSuperAdmin) return true;
    if (contactsUsed >= planLimits.contacts) {
      setPromptType('contacts');
      setShowPremiumPrompt(true);
      return false;
    }
    return true;
  }, [isSuperAdmin, planLimits.contacts]);

  // Check workflow limit
  const checkWorkflowLimit = useCallback((workflowsUsed) => {
    if (isSuperAdmin) return true;
    if (workflowsUsed >= planLimits.workflowAutomations) {
      setPromptType('workflows');
      setShowPremiumPrompt(true);
      return false;
    }
    return true;
  }, [isSuperAdmin, planLimits.workflowAutomations]);

  // Check if feature is accessible
  const hasFeatureAccess = useCallback((featureName) => {
    if (isSuperAdmin) return true;
    const features = {
      personal: ['basicInbox', 'emailSync'],
      plus: ['basicInbox', 'emailSync', 'basicInsights', 'advancedWorkflows', 'campaigns'],
      professional: ['basicInbox', 'emailSync', 'basicInsights', 'advancedWorkflows', 'campaigns', 'teamCollaboration', 'customDomains', 'apiAccess', 'webhooks'],
      enterprise: ['*'], // all features
    };
    
    const planFeatures = features[userPlan] || features.personal;
    return planFeatures.includes('*') || planFeatures.includes(featureName);
  }, [isSuperAdmin, userPlan]);

  // Get upgrade suggestion
  const getUpgradeSuggestionData = useCallback((usage) => {
    return getUpgradeSuggestion(
      usage.aiCreditsUsed || 0,
      planLimits.aiCredits,
      usage.emailAccountsUsed || 0,
      planLimits.emailAccounts
    );
  }, [planLimits]);

  const closePremiumPrompt = useCallback((type = 'credits', persist = false) => {
    setShowPremiumPrompt(false);
    if (persist) {
      setDismissedPrompts(prev => {
        const next = new Set(prev);
        next.add(type);
        try {
          sessionStorage.setItem('dismissedPremiumPrompts', JSON.stringify(Array.from(next)));
        } catch (e) {
          // ignore
        }
        return next;
      });
    }
  }, []);

  // If usage falls back below limit, clear dismissal so it can reappear later
  useEffect(() => {
    try {
      if (planLimits.aiCredits && dismissedPrompts.has('credits')) {
        // read current usage from session if available (no-op here). Keep dismissal until user usage drops below limit.
      }
    } catch (e) {
      // ignore
    }
  }, [planLimits.aiCredits, dismissedPrompts]);

  const isPremiumUser = isSuperAdmin || userPlan !== 'personal';
  const isEnterprise = isSuperAdmin || userPlan === 'enterprise';

  return {
    // State
    userPlan,
    planLimits,
    showPremiumPrompt,
    promptType,
    creditWarning,
    isSuperAdmin,
    isPremiumUser,
    isEnterprise,
    
    // Limit checks
    checkCreditLimit,
    checkEmailAccountLimit,
    checkContactLimit,
    checkWorkflowLimit,
    
    // Feature access
    hasFeatureAccess,
    
    // Suggestions
    getUpgradeSuggestionData,
    
    // UI control
    setShowPremiumPrompt,
    setPromptType,
    closePremiumPrompt,
    setCreditWarning,
  };
};

export default useSubscription;
