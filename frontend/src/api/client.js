// src/api/client.js
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api';
const ORG_ID   = '0f24e161-d76b-4773-8b0d-19c0116b6754';

export const orgId = ORG_ID;

const api = axios.create({ baseURL: BASE_URL });

export const getDashboard = () =>
  api.get(`/review/dashboard/?organization_id=${ORG_ID}`);

export const getEntries = (filters = {}) => {
  const params = new URLSearchParams({ organization_id: ORG_ID, ...filters });
  return api.get(`/review/entries/?${params}`);
};

export const getEntry = (id) =>
  api.get(`/review/entries/${id}/?organization_id=${ORG_ID}`);

export const approveEntry = (id, note = '') =>
  api.post(`/review/entries/${id}/approve/`, { organization_id: ORG_ID, note });

export const rejectEntry = (id, note = '') =>
  api.post(`/review/entries/${id}/reject/`, { organization_id: ORG_ID, note });

export const flagEntry = (id, note = '') =>
  api.post(`/review/entries/${id}/flag/`, { organization_id: ORG_ID, note });

export const uploadFile = (file, sourceType) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_type', sourceType);
  formData.append('organization_id', ORG_ID);
  return api.post('/ingest/upload/', formData);
};