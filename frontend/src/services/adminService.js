import api from './api';

export const getAdminOverview = async () => {
  const res = await api.get('/billing/admin/overview');
  return res.data;
};

export const getAdminTransactions = async (limit = 200) => {
  const res = await api.get(`/billing/admin/transactions?limit=${limit}`);
  return res.data;
};

export const getRevenueByCurrency = async () => {
  const res = await api.get('/billing/admin/reports/revenue-by-currency');
  return res.data;
};

export const getLLMProviders = async () => {
  const res = await api.get('/admin/llm/providers');
  return res.data;
};

export const updateLLMProvider = async (provider, payload) => {
  const res = await api.put(`/admin/llm/providers/${provider}`, payload);
  return res.data;
};

export const rotateLLMProviderKey = async (provider, apiKey) => {
  const res = await api.post(`/admin/llm/providers/${provider}/keys/rotate`, { api_key: apiKey });
  return res.data;
};

export const deleteLLMProviderKey = async (provider, keyIndex) => {
  const res = await api.post(`/admin/llm/providers/${provider}/keys/delete`, { key_index: keyIndex });
  return res.data;
};

export const runLLMHealthCheck = async () => {
  const res = await api.post('/admin/llm/providers/health-check');
  return res.data;
};

export const runLLMProviderTests = async () => {
  const res = await api.post('/admin/llm/providers/live-test');
  return res.data;
};

export const runLLMProviderHealthCheck = async (provider) => {
  const res = await api.post(`/admin/llm/providers/${encodeURIComponent(provider)}/health-check`);
  return res.data;
};

export const runLLMSingleProviderTest = async (provider) => {
  const res = await api.post(`/admin/llm/providers/${encodeURIComponent(provider)}/live-test`);
  return res.data;
};

export const resetPremiumDismissals = async () => {
  const res = await api.post('/admin/usage/dismissals/reset');
  return res.data;
};

export const getDismissalResetInfo = async () => {
  const res = await api.get('/usage/dismissals/reset');
  return res.data;
};

export const getUserAccessProfile = async (email) => {
  const res = await api.get(`/admin/usage/user-access/${encodeURIComponent(email)}`);
  return res.data;
};

export const updateUserAccessProfile = async (email, payload) => {
  const res = await api.put(`/admin/usage/user-access/${encodeURIComponent(email)}`, payload);
  return res.data;
};

export const getUserSendReadiness = async (email) => {
  const res = await api.get(`/admin/usage/user-access/${encodeURIComponent(email)}/send-readiness`);
  return res.data;
};

export const getFeatureTemplates = async () => {
  const res = await api.get('/admin/usage/feature-templates');
  return res.data;
};

export default {
  getAdminOverview,
  getAdminTransactions,
  getRevenueByCurrency,
  getLLMProviders,
  updateLLMProvider,
  rotateLLMProviderKey,
  deleteLLMProviderKey,
  runLLMHealthCheck,
  runLLMProviderTests,
  runLLMProviderHealthCheck,
  runLLMSingleProviderTest,
  resetPremiumDismissals,
  getDismissalResetInfo,
  getUserAccessProfile,
  updateUserAccessProfile,
  getUserSendReadiness,
  getFeatureTemplates,
};
