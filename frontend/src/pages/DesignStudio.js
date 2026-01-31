import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useForm, useFieldArray } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';

const energyOptions = ['DES', 'DMO', 'DMI'];
const lengthOptions = ['6m', '9m', '12m'];
const hookValues = ['90', '135', '180'];
const hookOptions = [
  { label: '90°', value: '90' },
  { label: '135°', value: '135' },
  { label: '180°', value: '180' },
];

const stirrupSchema = z.object({
  zone: z.string().min(1, 'Requerido'),
  spacing_m: z.coerce.number().positive('Ingrese un espaciamiento válido'),
  quantity: z.coerce.number().int().positive('Cantidad inválida'),
});

const elementLevelSchema = z.preprocess(
  (value) => {
    if (typeof value === 'number' && Number.isNaN(value)) {
      return undefined;
    }
    return value;
  },
  z
    .number({ required_error: 'Ingresa el nivel', invalid_type_error: 'Ingresa el nivel' })
    .refine((val) => Number.isFinite(val), 'Ingresa el nivel')
    .transform((val) => Number(val.toFixed(2)))
);

const formSchema = z.object({
  project_name: z.string().min(1, 'Indica el proyecto'),
  beam_label: z.string().min(1, 'Identifica la viga'),
  element_identifier: z.string().min(1, 'Campo obligatorio'),
  element_level: elementLevelSchema,
  element_quantity: z.coerce.number().int().min(1, 'Cantidad mínima 1'),
  top_bars_qty: z.coerce.number().int().min(1, 'Debe ser al menos 1'),
  bottom_bars_qty: z.coerce.number().int().min(1, 'Debe ser al menos 1'),
  top_bar_diameters_text: z.string().min(1, 'Define los diámetros superiores'),
  bottom_bar_diameters_text: z.string().min(1, 'Define los diámetros inferiores'),
  max_rebar_length_m: z.enum(lengthOptions),
  lap_splice_length_min_m: z.coerce.number().positive('Longitud inválida'),
  lap_splice_location: z.string().min(1, 'Describe la ubicación'),
  has_initial_cantilever: z.boolean(),
  has_final_cantilever: z.boolean(),
  hook_type: z.enum(hookOptions.map((opt) => opt.value)),
  cover_cm: z.coerce.number().int().min(1, 'Define el recubrimiento en cm'),
  span_geometries: z
    .array(
      z.object({
        clear_span_between_supports_m: z.coerce
          .number()
          .nonnegative('Define la luz libre'),
        section_base_cm: z.coerce.number().int().positive('Ingresa la base en cm'),
        section_height_cm: z.coerce.number().int().positive('Ingresa la altura en cm'),
      })
    )
    .min(1, 'Configura al menos una luz'),
  axis_supports: z
    .array(
      z.object({
        label: z.string().optional(),
        support_width_cm: z.coerce.number().int().nonnegative('Ancho inválido').default(0),
      })
    )
    .optional(),
  span_count: z.coerce.number().int().positive('Ingresa un número entero positivo'),
  stirrups_config: z.array(stirrupSchema).min(1, 'Agrega al menos una zona'),
  energy_dissipation_class: z.enum(energyOptions),
  concrete_strength: z.string().min(1, 'Selecciona f’c'),
  reinforcement: z.string().min(1, 'Selecciona fy'),
  notes: z.string().optional(),
});

const defaultValues = {
  project_name: 'Centro Cultural La Estación',
  beam_label: 'VIGA-E3-12',
  element_identifier: 'VIGA-E3-12',
  element_level: 3.52,
  element_quantity: 1,
  top_bars_qty: 4,
  bottom_bars_qty: 2,
  top_bar_diameters_text: '#5, #6',
  bottom_bar_diameters_text: '#5',
  max_rebar_length_m: '9m',
  lap_splice_length_min_m: 0.75,
  lap_splice_location: 'Traslapo centrado a 1.50 m del apoyo A',
  has_initial_cantilever: false,
  has_final_cantilever: false,
  span_geometries: [
    { clear_span_between_supports_m: 3.2, section_base_cm: 30, section_height_cm: 45 },
    { clear_span_between_supports_m: 4.0, section_base_cm: 30, section_height_cm: 45 },
    { clear_span_between_supports_m: 3.2, section_base_cm: 30, section_height_cm: 45 },
  ],
  hook_type: '180',
  cover_cm: 4,
  axis_supports: [
    { label: 'EJE 3', support_width_cm: 35 },
    { label: 'EJE 4', support_width_cm: 35 },
    { label: 'EJE 5', support_width_cm: 35 },
    { label: 'EJE 6', support_width_cm: 35 },
  ],
  span_count: 3,
  stirrups_config: [
    { zone: 'Confinada', spacing_m: 0.07, quantity: 18 },
    { zone: 'Central', spacing_m: 0.15, quantity: 12 },
  ],
  energy_dissipation_class: 'DES',
  concrete_strength: '21 MPa (3000 psi)',
  reinforcement: '420 MPa (Grado 60)',
  notes: 'Detalle conforme a NSR-10 Título C.\nConsiderar recubrimientos adicionales por exposición costa.',
};

const DesignStudio = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastDesign, setLastDesign] = useState(null);

  const {
    control,
    handleSubmit,
    register,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues,
    mode: 'onBlur',
  });

  const {
    fields: stirrupFields,
    append: appendStirrup,
    remove: removeStirrup,
  } = useFieldArray({ control, name: 'stirrups_config' });

  const { fields: axisSupportFields, replace: replaceAxisSupports } = useFieldArray({ control, name: 'axis_supports' });
  const { fields: spanGeometryFields, replace: replaceSpanGeometries } = useFieldArray({ control, name: 'span_geometries' });

  const energyClass = watch('energy_dissipation_class');
  const selectedLength = watch('max_rebar_length_m');
  const watchStirrups = watch('stirrups_config');
  const watchSpanCount = watch('span_count');
  const watchAxisSupports = watch('axis_supports');
  const watchSpanGeometries = watch('span_geometries');
  const watchInitialCantilever = watch('has_initial_cantilever');
  const watchFinalCantilever = watch('has_final_cantilever');
  const elementLevelField = register('element_level', { valueAsNumber: true });

  useEffect(() => {
    const spanTotal = Number(watchSpanCount) || 0;
    const requiredAxes = Math.max(spanTotal + 1, 0);
    const currentSupports = watchAxisSupports || [];

    if (currentSupports.length === requiredAxes) {
      return;
    }

    const nextSupports = Array.from({ length: requiredAxes }, (_, index) => {
      const existing = currentSupports[index];
      return existing ?? { label: '', support_width_cm: 0 };
    });
    replaceAxisSupports(nextSupports);
  }, [watchSpanCount, watchAxisSupports, replaceAxisSupports]);

  useEffect(() => {
    const spanTotal = Number(watchSpanCount) || 0;
    const requiredSpans = Math.max(spanTotal, 0);
    const currentSpans = watchSpanGeometries || [];

    if (currentSpans.length === requiredSpans) {
      return;
    }

    const nextSpans = Array.from({ length: requiredSpans }, (_, index) => {
      const existing = currentSpans[index];
      return (
        existing ?? {
          clear_span_between_supports_m: 0,
          section_base_cm: 0,
          section_height_cm: 0,
        }
      );
    });
    replaceSpanGeometries(nextSpans);
  }, [watchSpanCount, watchSpanGeometries, replaceSpanGeometries]);

  useEffect(() => {
    if (!Array.isArray(watchAxisSupports) || watchAxisSupports.length === 0) {
      return;
    }

    if (watchInitialCantilever) {
      const current = Number(watchAxisSupports[0]?.support_width_cm);
      if (current !== 0) {
        setValue('axis_supports.0.support_width_cm', 0, { shouldDirty: true });
      }
    }

    if (watchFinalCantilever) {
      const lastIndex = watchAxisSupports.length - 1;
      if (lastIndex >= 0) {
        const current = Number(watchAxisSupports[lastIndex]?.support_width_cm);
        if (current !== 0) {
          setValue(`axis_supports.${lastIndex}.support_width_cm`, 0, { shouldDirty: true });
        }
      }
    }
  }, [watchAxisSupports, watchInitialCantilever, watchFinalCantilever, setValue]);

  const preview = useMemo(() => {
    const totalLength =
      watchSpanGeometries?.reduce((sum, span) => sum + Number(span.clear_span_between_supports_m || 0), 0) || 0;
    const stirrupCount = watchStirrups?.reduce((sum, zone) => sum + Number(zone.quantity || 0), 0) || 0;
    return {
      totalLength: totalLength.toFixed(2),
      stirrupCount,
    };
  }, [watchSpanGeometries, watchStirrups]);

  const parseDiameterList = (value) => {
    if (!value) return null;
    const tokens = value
      .split(',')
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
    return tokens.length ? tokens : null;
  };

  const formatDimensionValue = (value) => {
    if (value === undefined || value === null) {
      return null;
    }
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return null;
    }
    return Number(numeric.toFixed(2));
  };

  const handleLevelBlur = (event) => {
    const rawValue = event.target.value;
    if (rawValue === '') {
      return;
    }
    const parsed = Number(rawValue);
    if (Number.isNaN(parsed)) {
      return;
    }
    const formatted = Number(parsed.toFixed(2));
    setValue('element_level', formatted, { shouldValidate: true, shouldDirty: true });
  };

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Tu sesión expiró, inicia sesión nuevamente.');
      }

      const {
        axis_supports,
        span_geometries,
        has_initial_cantilever,
        has_final_cantilever,
        stirrups_config,
        top_bar_diameters_text,
        bottom_bar_diameters_text,
        element_level,
        ...rest
      } = values;

      const formattedLevel =
        typeof element_level === 'number' && Number.isFinite(element_level)
          ? Number(element_level.toFixed(2))
          : null;

      const axisNumbering = (axis_supports || [])
        .map((axis) => (axis?.label || '').trim())
        .filter((label) => label.length > 0)
        .join(' · ');

      const supportWidths = (axis_supports || []).map((axis) => {
        const width = Number(axis?.support_width_cm);
        if (!Number.isFinite(width)) {
          return 0;
        }
        return Number(width.toFixed(2));
      });

      const spanGeometryPayload = (span_geometries || []).map((span, index) => ({
        label: `Luz ${index + 1}`,
        clear_span_between_supports_m: formatDimensionValue(span.clear_span_between_supports_m),
        base_cm: formatDimensionValue(span.section_base_cm),
        height_cm: formatDimensionValue(span.section_height_cm),
      }));

      const validSectionChanges = spanGeometryPayload.filter(
        (entry) =>
          entry.base_cm !== null && entry.height_cm !== null && entry.clear_span_between_supports_m !== null
      );

      const hasCantilevers = Boolean(has_initial_cantilever || has_final_cantilever);

      const payload = {
        ...rest,
        element_level: formattedLevel,
        has_cantilevers: hasCantilevers,
        axis_numbering: axisNumbering || null,
        support_widths_cm: supportWidths,
        span_geometries: spanGeometryPayload,
        top_bar_diameters: parseDiameterList(top_bar_diameters_text),
        bottom_bar_diameters: parseDiameterList(bottom_bar_diameters_text),
        section_changes: validSectionChanges.length ? validSectionChanges : null,
        stirrups_config: stirrups_config.map((zone) => ({
          zone: zone.zone,
          spacing_m: Number(zone.spacing_m),
          quantity: Number(zone.quantity),
        })),
      };

      const response = await axios.post('/api/tools/despiece/designs', payload, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setLastDesign(response.data);
      toast.success('Despiece guardado correctamente.');
    } catch (error) {
      const backendMessage = error.response?.data?.detail;
      toast.error(backendMessage || error.message || 'No se pudo guardar el despiece.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderError = (fieldName) =>
    errors[fieldName] ? (
      <p className="text-rose-400 text-xs mt-1">{errors[fieldName]?.message}</p>
    ) : null;

  return (
    <div className="min-h-screen bg-[#050b16] text-slate-100 font-[Inter]">
      <header className="border-b border-slate-800 bg-[#0f172a] px-8 py-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] tracking-[0.45em] uppercase text-slate-500">Despiece de vigas</p>
          <h1 className="text-2xl font-semibold tracking-wide">Panel técnico NSR-10</h1>
        </div>
        <div className="flex gap-3">
          <div className="flex bg-[#050b16] border border-slate-700 rounded-2xl p-1 text-[11px] font-bold uppercase tracking-[0.3em]">
            {energyOptions.map((option) => (
              <button
                type="button"
                key={option}
                onClick={() => setValue('energy_dissipation_class', option, { shouldDirty: true })}
                className={`px-3 py-1 rounded-xl transition-colors ${
                  energyClass === option ? 'bg-primary text-white' : 'text-slate-400'
                }`}
              >
                {option}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-slate-900/40 border border-slate-700 rounded-2xl px-4 py-2">
            <span className="material-symbols-outlined text-lg">bolt</span>
            <span className="text-xs uppercase tracking-[0.25em]">Modo Sísmico</span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 xl:grid-cols-[1.35fr_0.85fr] gap-8 px-8 py-10">
        <section className="bg-[#0c1326] border border-slate-800/70 rounded-3xl p-8 shadow-[0_20px_80px_rgba(2,6,23,0.75)]">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
            <div className="space-y-6 bg-[#050b16]/40 border border-slate-800 rounded-3xl p-6 shadow-[0_14px_45px_rgba(5,11,22,0.6)]">
              <header className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 01</p>
                  <h2 className="text-lg font-semibold">Identificación y materiales</h2>
                </div>
                <span className="text-xs text-slate-400">Proyecto · f’c · fy · DES</span>
              </header>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Proyecto</label>
                  <input
                    className="input"
                    placeholder="Nombre del proyecto"
                    {...register('project_name')}
                  />
                  {renderError('project_name')}
                </div>
                <div>
                  <label className="label">Viga / Identificador</label>
                  <input className="input" {...register('beam_label')} />
                  {renderError('beam_label')}
                </div>
                <div>
                  <label className="label">Nivel (m)</label>
                  <input
                    type="number"
                    step="0.01"
                    lang="en"
                    inputMode="decimal"
                    className="input no-spin"
                    {...elementLevelField}
                    onBlur={(event) => {
                      elementLevelField.onBlur(event);
                      handleLevelBlur(event);
                    }}
                  />
                  {renderError('element_level')}
                </div>
                <div>
                  <label className="label">Cantidad de elementos</label>
                  <input type="number" className="input" min={1} {...register('element_quantity', { valueAsNumber: true })} />
                  {renderError('element_quantity')}
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <label className="label">f’c concreto</label>
                  <select className="input" {...register('concrete_strength')}>
                    <option value="21 MPa (3000 psi)">21 MPa (3000 psi)</option>
                    <option value="24 MPa (3500 psi)">24 MPa (3500 psi)</option>
                    <option value="28 MPa (4000 psi)">28 MPa (4000 psi)</option>
                    <option value="32 MPa (4600 psi)">32 MPa (4600 psi)</option>
                  </select>
                  {renderError('concrete_strength')}
                </div>
                <div>
                  <label className="label">fy refuerzo</label>
                  <select className="input" {...register('reinforcement')}>
                    <option value="420 MPa (Grado 60)">420 MPa (Grado 60)</option>
                    <option value="520 MPa (Grado 75)">520 MPa (Grado 75)</option>
                  </select>
                  {renderError('reinforcement')}
                </div>
                <div>
                  <label className="label">Clase de disipación</label>
                  <select className="input" {...register('energy_dissipation_class')}>
                    {energyOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="space-y-6 bg-[#040916]/60 border border-slate-900/80 rounded-3xl p-6 shadow-[0_16px_60px_rgba(2,6,23,0.55)]">
              <header className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 02</p>
                  <h2 className="text-lg font-semibold">Geometría y apoyos</h2>
                </div>
                <span className="text-xs text-slate-400">Tramos · ejes · secciones</span>
              </header>

              <div>
                <label className="label">Número de luces</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  className="input input-compact input-short"
                  {...register('span_count', { valueAsNumber: true })}
                />
                {renderError('span_count')}
                <p className="text-xs text-slate-400 mt-1 italic">* Incluye tramos en Voladizo inicial o final</p>
              </div>

              <div>
                <label className="label">Voladizos</label>
                <div className="grid sm:grid-cols-2 gap-4">
                  <label className="flex items-center gap-3 bg-slate-900/50 border border-slate-800 rounded-2xl px-4 py-3 text-sm">
                    <input type="checkbox" className="accent-primary" {...register('has_initial_cantilever')} />
                    Voladizo inicial
                  </label>
                  <label className="flex items-center gap-3 bg-slate-900/50 border border-slate-800 rounded-2xl px-4 py-3 text-sm">
                    <input type="checkbox" className="accent-primary" {...register('has_final_cantilever')} />
                    Voladizo final
                  </label>
                </div>
              </div>

              <div>
                <label className="label">Ejes</label>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {axisSupportFields.length === 0 ? (
                    <p className="text-xs text-slate-500 col-span-full">Ajusta el número de luces para definir los ejes.</p>
                  ) : (
                    axisSupportFields.map((field, index) => (
                      <div key={field.id} className="border border-slate-800 rounded-2xl p-3 space-y-2 bg-slate-900/30">
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Eje {index + 1}</p>
                        <div className="flex gap-2 items-end">
                          <div className="flex-1">
                            <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Nombre</p>
                            <input
                              className="input input-compact"
                              placeholder={`EJE ${index + 1}`}
                              {...register(`axis_supports.${index}.label`)}
                            />
                          </div>
                          <div className="w-24">
                            <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Ancho (cm)</p>
                            <input
                              type="number"
                              step={5}
                              min={0}
                              className="input input-compact text-sm"
                              placeholder="0"
                              {...register(`axis_supports.${index}.support_width_cm`, { valueAsNumber: true })}
                            />
                          </div>
                        </div>
                        <p className="text-[10px] text-slate-500">0 cuando exista voladizo.</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800/70 bg-[#050b16]/30 p-5 space-y-4">
                <p className="text-[11px] uppercase tracking-[0.4em] text-slate-500">Luces y secciones</p>
                {spanGeometryFields.length === 0 ? (
                  <p className="text-xs text-slate-500">Ajusta el número de luces para generar las configuraciones.</p>
                ) : (
                  <div className="space-y-4">
                    {spanGeometryFields.map((field, index) => (
                      <div key={field.id} className="border border-slate-800 rounded-2xl p-4 bg-slate-900/30 space-y-4">
                        <div className="grid lg:grid-cols-[160px_minmax(0,1fr)] gap-4 items-start">
                          <div>
                            <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Luz {index + 1}</p>
                            <label className="label">Luz libre (m)</label>
                            <input
                              type="number"
                              step="0.01"
                              lang="en"
                              inputMode="decimal"
                              className="input input-compact input-short"
                              {...register(`span_geometries.${index}.clear_span_between_supports_m`, {
                                valueAsNumber: true,
                              })}
                            />
                            {errors.span_geometries?.[index]?.clear_span_between_supports_m && (
                              <p className="text-rose-400 text-xs mt-1">
                                {errors.span_geometries[index].clear_span_between_supports_m.message}
                              </p>
                            )}
                          </div>
                          <div>
                            <label className="label">Sección</label>
                            <div className="grid sm:grid-cols-2 gap-4">
                              <div>
                                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500 mb-2">Base (cm)</p>
                                <input
                                  type="number"
                                  step={5}
                                  min={5}
                                  className="input"
                                  placeholder="30"
                                  {...register(`span_geometries.${index}.section_base_cm`, {
                                    valueAsNumber: true,
                                  })}
                                />
                                {errors.span_geometries?.[index]?.section_base_cm && (
                                  <p className="text-rose-400 text-xs mt-1">
                                    {errors.span_geometries[index].section_base_cm.message}
                                  </p>
                                )}
                              </div>
                              <div>
                                <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500 mb-2">Altura (cm)</p>
                                <input
                                  type="number"
                                  step={5}
                                  min={5}
                                  className="input"
                                  placeholder="45"
                                  {...register(`span_geometries.${index}.section_height_cm`, {
                                    valueAsNumber: true,
                                  })}
                                />
                                {errors.span_geometries?.[index]?.section_height_cm && (
                                  <p className="text-rose-400 text-xs mt-1">
                                    {errors.span_geometries[index].section_height_cm.message}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-6 bg-[#030a18]/70 border border-slate-900 rounded-3xl p-6 shadow-[0_18px_70px_rgba(2,6,23,0.6)]">
              <header className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 03</p>
                  <h2 className="text-lg font-semibold">Armaduras longitudinales y transversales</h2>
                </div>
                <span className="text-xs text-slate-400">Barras · Φ · L<sub>máx</sub> · traslapos</span>
              </header>

              <div className="bg-[#0b172f] border border-slate-800 rounded-3xl p-5 space-y-4">
                <p className="text-[11px] uppercase tracking-[0.4em] text-slate-500">Parámetros generales</p>
                <div className="grid md:grid-cols-3 gap-5">
                  <div>
                    <label className="label">L. máxima barra</label>
                    <div className="flex gap-2">
                      {lengthOptions.map((length) => (
                        <button
                          type="button"
                          key={length}
                          onClick={() => setValue('max_rebar_length_m', length, { shouldDirty: true })}
                          className={`flex-1 py-2 rounded-lg border text-sm font-semibold transition-colors ${
                            selectedLength === length
                              ? 'bg-primary/90 text-white border-primary'
                              : 'bg-transparent border-slate-700 text-slate-300'
                          }`}
                        >
                          {length}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="label">Gancho</label>
                    <select className="input" {...register('hook_type')}>
                      {hookOptions.map((hook) => (
                        <option key={hook.value} value={hook.value}>
                          {hook.label}
                        </option>
                      ))}
                    </select>
                    {renderError('hook_type')}
                  </div>
                  <div>
                    <label className="label">Recubrimiento (cm)</label>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      className="input"
                      {...register('cover_cm', { valueAsNumber: true })}
                    />
                    {renderError('cover_cm')}
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Barras superiores</label>
                  <input type="number" className="input" min={0} {...register('top_bars_qty', { valueAsNumber: true })} />
                  {renderError('top_bars_qty')}
                </div>
                <div>
                  <label className="label">Barras inferiores</label>
                  <input type="number" className="input" min={0} {...register('bottom_bars_qty', { valueAsNumber: true })} />
                  {renderError('bottom_bars_qty')}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Diámetros superiores (en pares)</label>
                  <input className="input" placeholder="#5, #6" {...register('top_bar_diameters_text')} />
                  <p className="text-xs text-slate-400 mt-1">Separa por comas para definir varios diámetros.</p>
                  {renderError('top_bar_diameters_text')}
                </div>
                <div>
                  <label className="label">Diámetros inferiores</label>
                  <input className="input" placeholder="#5, #6" {...register('bottom_bar_diameters_text')} />
                  <p className="text-xs text-slate-400 mt-1">Incluye cada barra según el detalle longitudinal.</p>
                  {renderError('bottom_bar_diameters_text')}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Longitud mínima de traslapo (m)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    lang="en"
                    inputMode="decimal"
                    className="input"
                    {...register('lap_splice_length_min_m', { valueAsNumber: true })}
                  />
                  {renderError('lap_splice_length_min_m')}
                </div>
                <div>
                  <label className="label">Ubicación del traslapo</label>
                  <input className="input" {...register('lap_splice_location')} />
                  {renderError('lap_splice_location')}
                </div>
              </div>

              <div className="bg-[#0b172f] rounded-3xl border border-slate-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                    Estribos
                  </h2>
                  <button
                    type="button"
                    onClick={() => appendStirrup({ zone: '', spacing_m: '', quantity: '' })}
                    className="text-xs uppercase tracking-[0.3em] text-primary"
                  >
                    + Añadir zona
                  </button>
                </div>
                <div className="space-y-3">
                  {stirrupFields.map((field, index) => (
                    <div key={field.id} className="grid md:grid-cols-3 gap-3 items-end">
                      <div>
                        <label className="label">Zona</label>
                        <input className="input" {...register(`stirrups_config.${index}.zone`)} />
                        {errors.stirrups_config?.[index]?.zone && (
                          <p className="text-rose-400 text-xs mt-1">
                            {errors.stirrups_config[index].zone.message}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="label">Espaciamiento (m)</label>
                        <input
                          type="number"
                          step="0.01"
                          lang="en"
                          inputMode="decimal"
                          className="input"
                          {...register(`stirrups_config.${index}.spacing_m`, { valueAsNumber: true })}
                        />
                      </div>
                      <div className="flex items-end gap-3">
                        <div className="flex-1">
                          <label className="label">Cantidad</label>
                          <input type="number" className="input" {...register(`stirrups_config.${index}.quantity`, { valueAsNumber: true })} />
                        </div>
                        {stirrupFields.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeStirrup(index)}
                            className="text-xs uppercase tracking-[0.3em] text-slate-400"
                          >
                            Quitar
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                  {errors.stirrups_config?.message && (
                    <p className="text-rose-400 text-xs">{errors.stirrups_config.message}</p>
                  )}
                </div>
              </div>
            </div>

            <div>
              <label className="label">Notas</label>
              <textarea className="input h-24" {...register('notes')} placeholder="Condiciones, recubrimientos, observaciones" />
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 bg-primary/90 hover:bg-primary text-white py-3 rounded-2xl text-sm font-bold uppercase tracking-[0.3em] transition disabled:opacity-50"
              >
                {isSubmitting ? 'Guardando…' : 'Guardar despiece'}
              </button>
              <button
                type="button"
                onClick={() => reset(defaultValues)}
                className="px-6 py-3 rounded-2xl border border-slate-700 text-sm font-bold uppercase tracking-[0.3em]"
              >
                Restaurar presets
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-6">
          <div className="bg-[#050b16] border border-slate-800 rounded-3xl p-6 shadow-[0_20px_60px_rgba(2,6,23,0.65)]">
            <p className="text-[11px] uppercase tracking-[0.5em] text-slate-500 mb-5">Vista previa</p>
            <div className="h-44 rounded-2xl border border-primary/30 relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-950">
              <div className="absolute inset-4 border border-dashed border-primary/30 rounded-2xl" />
              <div className="absolute top-4 left-6 bg-primary/20 text-primary text-[11px] px-3 py-1 rounded-full font-mono">
                Luz total: {preview.totalLength} m
              </div>
              <div className="absolute bottom-4 right-6 bg-emerald-500/20 text-emerald-300 text-[11px] px-3 py-1 rounded-full font-mono">
                Estribos: {preview.stirrupCount}
              </div>
              <div className="absolute inset-0 flex items-center justify-center gap-2">
                {watchSpanGeometries?.map((span, index) => (
                  <div
                    key={`${span.label || 'luz'}-${index}`}
                    className="h-12 border border-primary/50 rounded-full px-4 flex flex-col justify-center text-[10px] text-slate-200"
                  >
                    <span className="font-mono text-primary tracking-[0.3em]">L{index + 1}</span>
                    <span>L={span.clear_span_between_supports_m || '--'} m · {span.section_base_cm || '--'}x{span.section_height_cm || '--'} cm</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-[#0c1326] border border-slate-800 rounded-3xl p-6 space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.4em] text-slate-400">Último registro</h2>
            {lastDesign ? (
              <div className="text-sm space-y-1">
                <p className="text-slate-300 font-semibold">{lastDesign.title}</p>
                <p className="text-slate-400">{lastDesign.description}</p>
                {lastDesign.despiece_viga && (
                  <p className="text-slate-400">
                    {lastDesign.despiece_viga.top_bars_qty} sup. / {lastDesign.despiece_viga.bottom_bars_qty} inf. · ganchos {lastDesign.despiece_viga.hook_type}°
                  </p>
                )}
                {lastDesign.despiece_viga && (
                  <p className="text-slate-500 text-xs">
                    Φ sup: {(lastDesign.despiece_viga.top_bar_diameters || []).join(', ') || '—'} · Φ inf: {(lastDesign.despiece_viga.bottom_bar_diameters || []).join(', ') || '—'}
                  </p>
                )}
                <p className="text-slate-500 text-xs">
                  Guardado el {new Date(lastDesign.created_at).toLocaleString('es-CO')}
                </p>
              </div>
            ) : (
              <p className="text-slate-500 text-sm">Aún no has sincronizado este despiece.</p>
            )}
          </div>

          <div className="bg-gradient-to-br from-primary/40 via-indigo-500/20 to-slate-900 rounded-3xl border border-primary/30 p-6 text-sm">
            <p className="uppercase tracking-[0.4em] text-[11px] text-slate-200 mb-3">Checklist normativo</p>
            <ul className="space-y-2">
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                Traslapos ≥ {watch('lap_splice_length_min_m')} m
              </li>
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                Energía {energyClass}
              </li>
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                fc = {watch('concrete_strength')}
              </li>
            </ul>
          </div>
        </aside>
      </main>

      <style jsx>{`
        .label {
          display: block;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.3em;
          color: #94a3b8;
          margin-bottom: 0.5rem;
        }
        .input {
          width: 100%;
          background: #050b16;
          border: 1px solid rgba(148, 163, 184, 0.35);
          border-radius: 1.25rem;
          padding: 0.65rem 1rem;
          font-size: 0.9rem;
          color: #f8fafc;
          transition: box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .input-compact {
          padding: 0.25rem 0.65rem;
          font-size: 0.8rem;
          border-radius: 0.9rem;
          height: 2.1rem;
          line-height: 1.1;
        }
        .input-short {
          max-width: 11rem;
        }
        .input:focus {
          outline: none;
          border-color: rgba(99, 102, 241, 0.8);
          box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
        }
        .input::placeholder {
          color: rgba(148, 163, 184, 0.6);
        }
        .no-spin::-webkit-inner-spin-button,
        .no-spin::-webkit-outer-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        .no-spin {
          -moz-appearance: textfield;
        }
        .material-symbols-outlined {
          font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
        }
      `}</style>
    </div>
  );
};

export default DesignStudio;
