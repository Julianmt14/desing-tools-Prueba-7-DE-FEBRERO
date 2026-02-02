import React, { useMemo } from 'react';
import toast from 'react-hot-toast';
import { useDespieceExport } from '../../hooks/useDespieceExport';

const FORMAT_OPTIONS = [
  { value: 'dwg', label: 'DWG' },
  { value: 'dxf', label: 'DXF' },
  { value: 'pdf', label: 'PDF' },
  { value: 'svg', label: 'SVG' },
];

const LOCALE_OPTIONS = [
  { value: 'es-CO', label: 'Español' },
  { value: 'en-US', label: 'Inglés' },
];

const STATUS_LABEL = {
  queued: 'En cola',
  processing: 'Procesando',
  completed: 'Listo',
  failed: 'Error',
};

const STATUS_CLASS = {
  queued: 'bg-amber-500/20 text-amber-200 border border-amber-400/40',
  processing: 'bg-sky-500/15 text-sky-200 border border-sky-400/40',
  completed: 'bg-emerald-500/20 text-emerald-200 border border-emerald-400/40',
  failed: 'bg-rose-500/15 text-rose-200 border border-rose-400/40',
};

const formatDate = (value) => {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleString('es-CO');
};

const DespieceExportPanel = ({ designId, projectName, beamLabel, lastSavedAt }) => {
  const {
    config,
    updateConfig,
    templates,
    isTemplatesLoading,
    previewSvg,
    previewTimestamp,
    requestPreview,
    isPreviewLoading,
    startExport,
    isExporting,
    jobHistory,
    refreshJobStatus,
    canExport,
    error,
  } = useDespieceExport(designId);

  const templateOptions = useMemo(() => {
    if (templates.length) {
      return templates;
    }
    return [{ key: 'beam/default', metadata: { title_block_label: 'Plantilla estándar' }, locale: 'es-CO' }];
  }, [templates]);

  const lastSyncLabel = useMemo(() => formatDate(lastSavedAt), [lastSavedAt]);

  const handleCopyPath = async (value) => {
    if (!value) {
      return;
    }
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else if (typeof document !== 'undefined') {
        const tempInput = document.createElement('textarea');
        tempInput.value = value;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
      } else {
        throw new Error('clipboard-not-supported');
      }
      toast.success('Ruta copiada al portapapeles');
    } catch (copyError) {
      toast.error('No se pudo copiar la ruta');
    }
  };

  return (
    <div className="despiece-export-panel bg-[#0c1326] border border-slate-800 rounded-3xl p-6 space-y-5 shadow-[0_20px_60px_rgba(2,6,23,0.65)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.35em] text-slate-500">Plano vinculado</p>
          <p className="text-lg font-semibold text-white">{beamLabel || 'Viga sin etiqueta'}</p>
          <p className="text-xs text-slate-400">{projectName || 'Proyecto sin título'}</p>
        </div>
        <span
          className={`text-[11px] px-3 py-1 rounded-full font-semibold uppercase tracking-[0.2em] ${
            canExport ? 'bg-emerald-500/20 text-emerald-100' : 'bg-amber-500/15 text-amber-200'
          }`}
        >
          {canExport ? 'Sincronizado' : 'Borrador'}
        </span>
      </div>

      <p className="text-xs text-slate-500">
        {canExport
          ? `Última sincronización: ${lastSyncLabel}`
          : 'Guarda el despiece para habilitar las exportaciones.'}
      </p>

      {error ? (
        <p className="text-xs text-rose-300 bg-rose-950/40 border border-rose-800/40 rounded-2xl px-3 py-2">
          {error}
        </p>
      ) : null}

      <div className="space-y-4">
        <div>
          <label className="label text-[11px] text-slate-500">Plantilla</label>
          <select
            className="input text-sm bg-[#050b16]"
            value={config.template}
            onChange={(event) => updateConfig({ template: event.target.value })}
            disabled={isTemplatesLoading}
          >
            {templateOptions.map((template) => (
              <option key={template.key} value={template.key}>
                {template.metadata?.title_block_label || template.key} · {template.locale}
              </option>
            ))}
          </select>
        </div>

        <div>
          <p className="label text-[11px] text-slate-500 mb-2">Formato</p>
          <div className="grid grid-cols-4 gap-2 text-xs">
            {FORMAT_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => updateConfig({ format: option.value })}
                className={`rounded-xl border px-3 py-2 font-semibold tracking-[0.2em] transition-colors ${
                  config.format === option.value
                    ? 'border-primary bg-primary/10 text-white'
                    : 'border-slate-700 bg-[#050b16] text-slate-400'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label text-[11px] text-slate-500">Idioma</label>
            <select
              className="input text-sm bg-[#050b16]"
              value={config.locale}
              onChange={(event) => updateConfig({ locale: event.target.value })}
            >
              {LOCALE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label text-[11px] text-slate-500">Escala</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="25"
                max="150"
                step="5"
                value={config.scale}
                onChange={(event) => updateConfig({ scale: Number(event.target.value) })}
                className="flex-1 accent-primary"
              />
              <span className="text-sm font-semibold text-slate-100">1:{Math.round(config.scale)}</span>
            </div>
          </div>
        </div>

        <label className="flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={config.includePreview}
            onChange={(event) => updateConfig({ includePreview: event.target.checked })}
            className="h-4 w-4 rounded border-slate-600 bg-[#050b16] text-primary"
          />
          Incluir SVG de referencia al exportar
        </label>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={requestPreview}
          disabled={!canExport || isPreviewLoading}
          className="flex-1 bg-slate-800/70 hover:bg-slate-700 text-white py-3 rounded-2xl text-xs font-bold uppercase tracking-[0.3em] transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPreviewLoading ? 'Generando vista previa…' : 'Vista previa SVG'}
        </button>
        <button
          type="button"
          onClick={startExport}
          disabled={!canExport || isExporting}
          className="flex-1 bg-primary/90 hover:bg-primary text-white py-3 rounded-2xl text-xs font-bold uppercase tracking-[0.3em] transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExporting ? 'Encolando…' : 'Exportar plano'}
        </button>
      </div>

      <div className="bg-[#050b16] border border-slate-800 rounded-2xl p-4 space-y-3">
        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.35em] text-slate-500">
          <span>Vista previa</span>
          <span>{previewTimestamp ? formatDate(previewTimestamp) : 'Sin generar'}</span>
        </div>
        {previewSvg ? (
          <div className="rounded-xl border border-slate-900/60 bg-[#0c1326] overflow-auto max-h-[320px]">
            <div className="preview-svg" dangerouslySetInnerHTML={{ __html: previewSvg }} />
          </div>
        ) : (
          <p className="text-xs text-slate-500">
            Genera la vista previa para validar la plantilla y escala antes de exportar.
          </p>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-400">Historial de exportaciones</h3>
          <span className="text-[11px] text-slate-500">{jobHistory.length} registro(s)</span>
        </div>
        {jobHistory.length === 0 ? (
          <p className="text-xs text-slate-500">
            Las exportaciones recientes aparecerán aquí con sus rutas de descarga.
          </p>
        ) : (
          <div className="space-y-3">
            {jobHistory.map((job) => (
              <div key={job.job_id} className="rounded-2xl border border-slate-800 bg-[#050b16] p-3 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-slate-100 font-semibold text-sm">{job.format?.toUpperCase()} · Esc 1:{job.scale}</p>
                    <p className="text-[11px] text-slate-500">
                      {job.template} · {job.locale}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-[11px] font-semibold ${
                    STATUS_CLASS[job.status] || 'bg-slate-800 text-slate-300 border border-slate-700'
                  }`}
                  >
                    {STATUS_LABEL[job.status] || job.status}
                  </span>
                </div>
                {job.message && job.status === 'failed' ? (
                  <p className="text-xs text-rose-300">{job.message}</p>
                ) : null}
                <div className="flex flex-wrap gap-2 text-xs">
                  {job.download_url ? (
                    <a
                      href={job.download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1 rounded-xl border border-slate-700 text-slate-200 hover:border-primary/60"
                    >
                      Descargar
                    </a>
                  ) : null}
                  {job.file_path ? (
                    <button
                      type="button"
                      onClick={() => handleCopyPath(job.file_path)}
                      className="px-3 py-1 rounded-xl border border-slate-700 text-slate-200 hover:border-primary/60"
                    >
                      Copiar ruta
                    </button>
                  ) : null}
                  {job.preview_path ? (
                    <button
                      type="button"
                      onClick={() => handleCopyPath(job.preview_path)}
                      className="px-3 py-1 rounded-xl border border-slate-700 text-slate-200 hover:border-primary/60"
                    >
                      Copiar preview
                    </button>
                  ) : null}
                  {job.status !== 'completed' && job.status !== 'failed' ? (
                    <button
                      type="button"
                      onClick={() => refreshJobStatus(job.job_id)}
                      className="px-3 py-1 rounded-xl border border-slate-700 text-slate-200 hover:border-primary/60"
                    >
                      Actualizar
                    </button>
                  ) : null}
                </div>
                <p className="text-[11px] text-slate-500">
                  Actualizado {formatDate(job.updated_at || job.created_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .despiece-export-panel input[type='range']::-webkit-slider-thumb {
          appearance: none;
          height: 14px;
          width: 14px;
          border-radius: 999px;
          background: #6366f1;
        }
        .despiece-export-panel input[type='range']::-moz-range-thumb {
          height: 14px;
          width: 14px;
          border-radius: 999px;
          background: #6366f1;
        }
        .despiece-export-panel .preview-svg svg {
          width: 100%;
          height: auto;
        }
        .despiece-export-panel .preview-svg {
          padding: 1rem;
          background: #050b16;
        }
      `}</style>
    </div>
  );
};

export default DespieceExportPanel;
