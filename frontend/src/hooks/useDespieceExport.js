import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import apiClient from '../utils/apiClient';

const STORAGE_KEY = 'despiece-export-history';
const DEFAULT_CONFIG = {
  format: 'dwg',
  template: 'beam/default',
  locale: 'es-CO',
  scale: 50,
  includePreview: true,
};
const MAX_HISTORY_RECORDS = 8;
const POLL_INTERVAL_MS = 3500;
const MAX_POLL_ATTEMPTS = 15;

const loadHistory = (designId) => {
  if (!designId || typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const snapshot = JSON.parse(raw);
    const entries = snapshot?.[String(designId)];
    if (!Array.isArray(entries)) {
      return [];
    }
    return entries.slice(0, MAX_HISTORY_RECORDS);
  } catch (error) {
    return [];
  }
};

const persistHistory = (designId, history) => {
  if (!designId || typeof window === 'undefined') {
    return;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const snapshot = raw ? JSON.parse(raw) : {};
    snapshot[String(designId)] = history;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  } catch (error) {
    // ignore persistence errors silently
  }
};

export const useDespieceExport = (designId) => {
  const [config, setConfig] = useState(() => ({ ...DEFAULT_CONFIG }));
  const [templates, setTemplates] = useState([]);
  const [isTemplatesLoading, setIsTemplatesLoading] = useState(false);
  const [previewSvg, setPreviewSvg] = useState(null);
  const [previewTimestamp, setPreviewTimestamp] = useState(null);
  const [history, setHistory] = useState([]);
  const [isExporting, setIsExporting] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [lastError, setLastError] = useState(null);
  const pollRefs = useRef({});

  useEffect(() => {
    setIsTemplatesLoading(true);
    apiClient
      .get('/api/v1/designs/drawing-templates')
      .then((response) => {
        setTemplates(response.data || []);
      })
      .catch(() => {
        toast.error('No se pudieron cargar las plantillas de dibujo');
      })
      .finally(() => setIsTemplatesLoading(false));
  }, []);

  useEffect(() => {
    if (!designId) {
      setHistory([]);
      setPreviewSvg(null);
      setPreviewTimestamp(null);
      return;
    }
    const storedHistory = loadHistory(designId);
    setHistory(storedHistory);
  }, [designId]);

  useEffect(() => () => {
    Object.values(pollRefs.current).forEach((timerId) => clearTimeout(timerId));
    pollRefs.current = {};
  }, []);

  useEffect(() => {
    if (!templates.length) {
      return;
    }
    if (!templates.some((tpl) => tpl.key === config.template)) {
      setConfig((prev) => ({ ...prev, template: templates[0].key }));
    }
  }, [templates, config.template]);

  const setHistoryWithPersist = useCallback(
    (updater) => {
      setHistory((prev) => {
        const nextValue = typeof updater === 'function' ? updater(prev) : updater;
        if (designId) {
          persistHistory(designId, nextValue);
        }
        return nextValue;
      });
    },
    [designId]
  );

  const upsertJob = useCallback(
    (job) => {
      if (!job || !job.job_id) {
        return;
      }
      setHistoryWithPersist((prev) => {
        const next = Array.isArray(prev) ? [...prev] : [];
        const existingIndex = next.findIndex((entry) => entry.job_id === job.job_id);
        if (existingIndex >= 0) {
          next[existingIndex] = { ...next[existingIndex], ...job };
        } else {
          next.unshift(job);
        }
        return next.slice(0, MAX_HISTORY_RECORDS);
      });
    },
    [setHistoryWithPersist]
  );

  const updateConfig = useCallback((patch) => {
    setConfig((prev) => {
      const next = { ...prev, ...patch };
      if (patch.scale !== undefined) {
        const numericScale = Number(patch.scale) || DEFAULT_CONFIG.scale;
        next.scale = Math.min(150, Math.max(25, numericScale));
      }
      return next;
    });
  }, []);

  const resetConfig = useCallback(() => {
    setConfig({ ...DEFAULT_CONFIG });
  }, []);

  const clearPreview = useCallback(() => {
    setPreviewSvg(null);
    setPreviewTimestamp(null);
  }, []);

  const refreshJobStatusInternal = useCallback(
    async (jobId, { silent } = {}) => {
      if (!jobId) {
        return null;
      }
      try {
        const response = await apiClient.get(`/api/v1/drawing/exports/${jobId}`);
        if (response?.data) {
          upsertJob(response.data);
        }
        return response?.data || null;
      } catch (error) {
        const message = error.response?.data?.detail || error.message || 'No se pudo consultar el estado';
        if (!silent) {
          toast.error(message);
        }
        return null;
      }
    },
    [upsertJob]
  );

  const schedulePolling = useCallback(
    (jobId, attempt = 0) => {
      if (!jobId || attempt >= MAX_POLL_ATTEMPTS) {
        return;
      }
      const timerId = setTimeout(async () => {
        delete pollRefs.current[jobId];
        const job = await refreshJobStatusInternal(jobId, { silent: true });
        if (!job) {
          schedulePolling(jobId, attempt + 1);
          return;
        }
        if (job.status === 'completed') {
          toast.success('Exportación lista para descargar');
          return;
        }
        if (job.status === 'failed') {
          const message = job.message || 'La exportación falló';
          toast.error(message);
          return;
        }
        schedulePolling(jobId, attempt + 1);
      }, POLL_INTERVAL_MS);
      pollRefs.current[jobId] = timerId;
    },
    [refreshJobStatusInternal]
  );

  const startExport = useCallback(async () => {
    if (!designId) {
      const message = 'Guarda el despiece para habilitar las exportaciones';
      toast.error(message);
      setLastError(message);
      return null;
    }
    setIsExporting(true);
    setLastError(null);
    try {
      const payload = {
        design_id: designId,
        format: config.format,
        template: config.template,
        scale: Number(config.scale) || DEFAULT_CONFIG.scale,
        locale: config.locale,
        include_preview: Boolean(config.includePreview),
      };
      const response = await apiClient.post('/api/v1/drawing/exports', payload);
      const job = response.data;
      if (job) {
        upsertJob(job);
        schedulePolling(job.job_id);
      }
      toast.success('Exportación encolada');
      return job;
    } catch (error) {
      const message = error.response?.data?.detail || error.message || 'No se pudo encolar la exportación';
      toast.error(message);
      setLastError(message);
      return null;
    } finally {
      setIsExporting(false);
    }
  }, [designId, config, upsertJob, schedulePolling]);

  const requestPreview = useCallback(async () => {
    if (!designId) {
      const message = 'Guarda el despiece para solicitar la vista previa';
      toast.error(message);
      setLastError(message);
      return null;
    }
    setIsPreviewLoading(true);
    setLastError(null);
    try {
      const payload = {
        template: config.template,
        scale: Number(config.scale) || DEFAULT_CONFIG.scale,
        locale: config.locale,
        include_preview: true,
        format: 'svg',
      };
      const response = await apiClient.post(`/api/v1/designs/${designId}/export`, payload);
      const svgContent = response.data?.preview || null;
      if (!svgContent) {
        toast.error('El servicio no devolvió el SVG de vista previa');
        return null;
      }
      setPreviewSvg(svgContent);
      setPreviewTimestamp(new Date().toISOString());
      return svgContent;
    } catch (error) {
      const message = error.response?.data?.detail || error.message || 'No se pudo generar la vista previa';
      toast.error(message);
      setLastError(message);
      return null;
    } finally {
      setIsPreviewLoading(false);
    }
  }, [designId, config]);

  const refreshJobStatus = useCallback(
    (jobId) => refreshJobStatusInternal(jobId, { silent: false }),
    [refreshJobStatusInternal]
  );

  const sortedHistory = useMemo(() => {
    return [...history].sort((a, b) => {
      const dateA = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const dateB = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return dateB - dateA;
    });
  }, [history]);

  const canExport = Boolean(designId);

  return {
    config,
    updateConfig,
    resetConfig,
    templates,
    isTemplatesLoading,
    previewSvg,
    previewTimestamp,
    requestPreview,
    clearPreview,
    isPreviewLoading,
    startExport,
    isExporting,
    jobHistory: sortedHistory,
    refreshJobStatus,
    canExport,
    error: lastError,
  };
};

export default useDespieceExport;
